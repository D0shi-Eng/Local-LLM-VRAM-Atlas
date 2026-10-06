"""Evidence sidecar completeness audit.

change detection reported 243 logical evidence references without persisted sidecars
(by prior persist_bundle design, not by deletion). This module audits those
references read-only and determines, per reference, whether a sidecar can be
reconstructed *deterministically* from data Atlas already persists.

Atlas never invents a source field to make a sidecar exist. Where
reconstruction is not provable, the reference is recorded as an explicit
limitation (``evidence_sidecar_unavailable``) in an availability inventory —
never as fabricated evidence.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

EVIDENCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,120}$")

# Intake wrote exactly these nine claims per model.
LEGACY_CLAIMS = (
    ("license-license-id", "license_term"),
    ("openness", "openness_class"),
    ("base-models", "other"),
    ("architecture", "architecture_property"),
    ("total-parameters-b", "other"),
    ("context-length-advertised-max", "other"),
    ("quantization-quant-name", "quantization_property"),
    ("popularity", "popularity_signal"),
    ("resolved-revision", "other"),
)

UNAVAILABLE_REASON = "evidence_sidecar_unavailable"


@dataclass
class SidecarAudit:
    """Read-only inventory of evidence references vs persisted sidecars."""

    total_references: int = 0
    unique_references: int = 0
    persisted: int = 0
    missing: int = 0
    invalid_ids: list[str] = field(default_factory=list)
    orphans: list[str] = field(default_factory=list)
    affected_models: dict[str, list[str]] = field(default_factory=dict)

    def to_payload(self) -> dict:
        return {
            "total_references": self.total_references,
            "unique_references": self.unique_references,
            "persisted_sidecars": self.persisted,
            "references_without_sidecar": self.missing,
            "invalid_id_count": len(self.invalid_ids),
            "invalid_ids": sorted(self.invalid_ids),
            "orphan_sidecar_count": len(self.orphans),
            "orphans": sorted(self.orphans),
            "affected_model_count": len(self.affected_models),
            "affected_models": {
                model_id: sorted(ids) for model_id, ids in sorted(self.affected_models.items())
            },
        }


def evidence_dir(repo_root: Path) -> Path:
    """Canonical evidence sidecar directory."""
    return repo_root / "catalog" / "evidence"


def load_records(repo_root: Path) -> dict[str, dict]:
    """Load canonical model records keyed by model_id."""
    models_dir = repo_root / "catalog" / "models"
    out: dict[str, dict] = {}
    if not models_dir.is_dir():
        return out
    for path in sorted(models_dir.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        model_id = record.get("model_id")
        if isinstance(model_id, str):
            out[model_id] = record
    return out


def referenced_evidence_ids(record: dict) -> list[str]:
    """Evidence ids referenced by one record, in stored order."""
    verification = record.get("verification") or {}
    ids = verification.get("evidence_ids") or []
    return [str(e) for e in ids if isinstance(e, str)]


def persisted_sidecars(repo_root: Path) -> dict[str, dict]:
    """Persisted evidence sidecars keyed by evidence_id."""
    base = evidence_dir(repo_root)
    out: dict[str, dict] = {}
    if not base.is_dir():
        return out
    for path in sorted(base.glob("*.json")):
        if path.name.endswith("-manifest.json"):
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        eid = record.get("evidence_id") or path.stem
        out[str(eid)] = record
    return out


def sidecar_completeness(record: dict, repo_root: Path) -> str:
    """Completeness of one record's evidence backing."""
    ids = referenced_evidence_ids(record)
    if not ids:
        return "none"
    persisted = set(persisted_sidecars(repo_root))
    found = sum(1 for eid in ids if eid in persisted)
    if found == len(ids):
        return "complete"
    if found:
        return "partial"
    return "logical_reference_only"


def audit_sidecars(repo_root: Path) -> SidecarAudit:
    """Read-only inventory of references, sidecars and orphans."""
    audit = SidecarAudit()
    records = load_records(repo_root)
    sidecars = persisted_sidecars(repo_root)
    referenced: set[str] = set()
    for model_id, record in sorted(records.items()):
        ids = referenced_evidence_ids(record)
        audit.total_references += len(ids)
        missing_for_model: list[str] = []
        for eid in ids:
            referenced.add(eid)
            if not EVIDENCE_ID_RE.match(eid):
                audit.invalid_ids.append(eid)
            if eid in sidecars:
                audit.persisted += 1
            else:
                audit.missing += 1
                missing_for_model.append(eid)
        if missing_for_model:
            audit.affected_models[model_id] = missing_for_model
    audit.unique_references = len(referenced)
    audit.orphans = sorted(set(sidecars) - referenced)
    return audit


def _claim_for(evidence_id: str) -> str | None:
    for suffix, claim_type in LEGACY_CLAIMS:
        if evidence_id.endswith(f"-ev-{suffix}"):
            return claim_type
    return None


def backfill_plan(repo_root: Path) -> dict:
    """Dry-run plan: which missing sidecars are provably reconstructible.

    Reconstruction requires, for the exact reference: a persisted source
    record (for provenance), a resolved revision, a retrieval/capture
    timestamp already stored by Atlas, and a documented claim shape. Anything
    else is refused as an explicit limitation rather than invented.
    """
    audit = audit_sidecars(repo_root)
    records = load_records(repo_root)
    sources_dir = repo_root / "catalog" / "sources"
    available_sources: set[str] = set()
    if sources_dir.is_dir():
        for path in sorted(sources_dir.glob("*.json")):
            if path.name == "registry.json":
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                continue
            sid = data.get("source_id")
            if isinstance(sid, str):
                available_sources.add(sid)

    proposed: list[dict] = []
    refused: list[dict] = []
    for model_id, ids in sorted(audit.affected_models.items()):
        record = records.get(model_id, {})
        display = str(record.get("display_name") or "")
        revision = (record.get("quantization") or {}).get("source_revision")
        popularity = record.get("popularity") or {}
        captured_at = popularity.get("captured_at") if isinstance(popularity, dict) else None
        source_id = f"{model_id}-src-hf"
        for eid in ids:
            claim_type = _claim_for(eid)
            if claim_type is None:
                refused.append(
                    {
                        "model_id": model_id,
                        "evidence_id": eid,
                        "reason": "undocumented_claim_shape",
                    }
                )
                continue
            reason = None
            if source_id not in available_sources:
                reason = "no_persisted_source_record_for_provenance"
            elif not isinstance(revision, str) or not revision.strip():
                reason = "resolved_revision_absent"
            elif claim_type == "popularity_signal" and not captured_at:
                reason = "capture_timestamp_absent"
            elif claim_type == "other" and not captured_at:
                reason = "retrieval_timestamp_absent"
            if reason:
                refused.append(
                    {
                        "model_id": model_id,
                        "evidence_id": eid,
                        "claim_type": claim_type,
                        "reason": reason,
                        "status": UNAVAILABLE_REASON,
                    }
                )
                continue
            proposed.append(
                {
                    "evidence_id": eid,
                    "model_id": model_id,
                    "claim_type": claim_type,
                    "source_id": source_id,
                    "source_url": f"https://huggingface.co/{display}",
                    "resolved_revision": revision,
                    "retrieved_at": captured_at,
                }
            )
    return {
        "dry_run": True,
        "plan_kind": "historical_evidence_sidecar_backfill",
        "references_missing": audit.missing,
        "reconstructible_count": len(proposed),
        "unavailable_count": len(refused),
        "proposed": proposed,
        "unavailable": refused,
        "notes": (
            "Only references whose provenance, revision and timestamp are already persisted are "
            "reconstructible. Everything else is recorded as an explicit limitation; no source "
            "field is invented and no historical evidence id is regenerated."
        ),
    }

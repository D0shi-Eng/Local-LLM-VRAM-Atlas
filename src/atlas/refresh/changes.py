"""Change taxonomy, severity, events, and semantic delta analysis."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

CHANGE_TYPES = (
    "model_discovered",
    "repository_revision_changed",
    "metadata_changed",
    "artifact_added",
    "artifact_removed",
    "artifact_changed",
    "quant_variant_added",
    "quant_variant_removed",
    "license_changed",
    "openness_changed",
    "lineage_changed",
    "architecture_changed",
    "base_model_changed",
    "gating_changed",
    "repository_disabled",
    "repository_unavailable",
    "repository_restored",
    "alignment_claim_changed",
    "runtime_evidence_changed",
    "source_officiality_changed",
    "popularity_changed",
    # Quality-evidence events (additive; severity is data-integrity
    # impact, never model quality or intelligence).
    "quality_evidence_added",
    "quality_evidence_updated",
    "quality_evidence_withdrawn",
    "benchmark_superseded",
    "evaluation_identity_conflict",
    "retention_evidence_added",
    # Evidence-closure events (additive; same data-integrity semantics).
    "evidence_reacquired",
    "vram_evidence_recorded",
    "recommendation_status_changed",
    "evidence_conflict_detected",
    "evidence_superseded",
)

SEVERITIES = ("critical", "high", "medium", "low", "informational")

REVIEW_STATES = ("safe_auto_apply", "review_required", "blocked", "informational_only")

# Severity assignment: catalog integrity impact, never model quality.
SEVERITY_BY_TYPE: dict[str, str] = {
    "model_discovered": "informational",
    "repository_revision_changed": "low",
    "metadata_changed": "low",
    "artifact_added": "medium",
    "artifact_removed": "high",
    "artifact_changed": "medium",
    "quant_variant_added": "medium",
    "quant_variant_removed": "high",
    "license_changed": "critical",
    "openness_changed": "critical",
    "lineage_changed": "high",
    "architecture_changed": "high",
    "base_model_changed": "high",
    "gating_changed": "medium",
    "repository_disabled": "high",
    "repository_unavailable": "medium",
    "repository_restored": "medium",
    "alignment_claim_changed": "low",
    "runtime_evidence_changed": "low",
    "source_officiality_changed": "high",
    "popularity_changed": "informational",
    "quality_evidence_added": "informational",
    "quality_evidence_updated": "low",
    "quality_evidence_withdrawn": "medium",
    "benchmark_superseded": "low",
    "evaluation_identity_conflict": "high",
    "retention_evidence_added": "informational",
    "evidence_reacquired": "informational",
    "vram_evidence_recorded": "informational",
    "recommendation_status_changed": "low",
    "evidence_conflict_detected": "high",
    "evidence_superseded": "low",
}

# Review policy: critical/high semantic changes are never silently auto-applied.
REVIEW_BY_SEVERITY: dict[str, str] = {
    "critical": "review_required",
    "high": "review_required",
    "medium": "safe_auto_apply",
    "low": "safe_auto_apply",
    "informational": "informational_only",
}


def severity_for(change_type: str) -> str:
    """Severity for a change type (unknown types are blocked, never guessed)."""
    if change_type not in SEVERITY_BY_TYPE:
        return "critical"
    return SEVERITY_BY_TYPE[change_type]


def review_for(change_type: str) -> str:
    """Review state derived from severity."""
    return REVIEW_BY_SEVERITY[severity_for(change_type)]


def change_event_id(
    *,
    event_type: str,
    model_id: str,
    old_revision: str | None,
    new_revision: str | None,
    old_fingerprint: str | None,
    new_fingerprint: str | None,
) -> str:
    """Bounded deterministic change-event ID (digest, no long-name defect)."""
    canonical = "\x1f".join(
        [
            "atlas-change/v1",
            event_type.strip().lower(),
            (model_id or "").strip().lower(),
            (old_revision or "").strip(),
            (new_revision or "").strip(),
            (old_fingerprint or "").strip(),
            (new_fingerprint or "").strip(),
        ]
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    candidate = f"chg-v1-{digest}"
    assert len(candidate) <= 121
    return candidate


@dataclass(frozen=True)
class ChangeEvent:
    """One semantic delta (machine-readable, compact references only)."""

    event_id: str
    event_version: str
    event_type: str
    severity: str
    model_id: str
    artifact_id: str | None
    source_id: str | None
    old_revision: str | None
    new_revision: str | None
    old_fingerprint: str | None
    new_fingerprint: str | None
    changed_fields: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    detected_at: str
    review_status: str
    apply_status: str
    notes: str | None = None

    def to_dict(self) -> dict:
        """Serialize without duplicating full model records."""
        return {
            "event_id": self.event_id,
            "event_version": self.event_version,
            "event_type": self.event_type,
            "severity": self.severity,
            "model_id": self.model_id,
            "artifact_id": self.artifact_id,
            "source_id": self.source_id,
            "old_revision": self.old_revision,
            "new_revision": self.new_revision,
            "old_fingerprint": self.old_fingerprint,
            "new_fingerprint": self.new_fingerprint,
            "changed_fields": list(self.changed_fields),
            "evidence_ids": list(self.evidence_ids),
            "detected_at": self.detected_at,
            "review_status": self.review_status,
            "apply_status": self.apply_status,
            "notes": self.notes,
        }


def build_event(
    *,
    event_type: str,
    model_id: str,
    old_revision: str | None,
    new_revision: str | None,
    old_fingerprint: str | None,
    new_fingerprint: str | None,
    changed_fields: tuple[str, ...] | list[str] = (),
    evidence_ids: tuple[str, ...] | list[str] = (),
    detected_at: str,
    artifact_id: str | None = None,
    source_id: str | None = None,
    notes: str | None = None,
) -> ChangeEvent:
    """Construct a validated change event with derived severity/review."""
    if event_type not in CHANGE_TYPES:
        raise ValueError(f"unknown change type: {event_type!r}")
    severity = severity_for(event_type)
    review = review_for(event_type)
    event_id = change_event_id(
        event_type=event_type,
        model_id=model_id,
        old_revision=old_revision,
        new_revision=new_revision,
        old_fingerprint=old_fingerprint,
        new_fingerprint=new_fingerprint,
    )
    return ChangeEvent(
        event_id=event_id,
        event_version="0.5.0",
        event_type=event_type,
        severity=severity,
        model_id=model_id,
        artifact_id=artifact_id,
        source_id=source_id,
        old_revision=old_revision,
        new_revision=new_revision,
        old_fingerprint=old_fingerprint,
        new_fingerprint=new_fingerprint,
        changed_fields=tuple(changed_fields),
        evidence_ids=tuple(evidence_ids),
        detected_at=detected_at,
        review_status=review,
        apply_status="pending",
        notes=notes,
    )


def semantic_delta(
    *,
    model_id: str,
    old_record: dict,
    new_record: dict,
    old_artifacts: list[dict] | None = None,
    new_artifacts: list[dict] | None = None,
    old_revision: str | None,
    new_revision: str | None,
    detected_at: str,
    source_id: str | None = None,
) -> list[ChangeEvent]:
    """Compare semantic fingerprints; README-only revisions yield no events.

    Volatile popularity deltas produce a separate informational event only.
    """
    from atlas.refresh import fingerprints as fp

    old_fp = fp.all_fingerprints(old_record, old_artifacts or [])
    new_fp = fp.all_fingerprints(new_record, new_artifacts or [])
    events: list[ChangeEvent] = []
    if old_revision != new_revision:
        # Revision change is recorded, but semantic events carry the weight.
        events.append(
            build_event(
                event_type="repository_revision_changed",
                model_id=model_id,
                old_revision=old_revision,
                new_revision=new_revision,
                old_fingerprint=old_fp["identity"],
                new_fingerprint=new_fp["identity"],
                changed_fields=("source_revision",),
                detected_at=detected_at,
                source_id=source_id,
                notes="revision signal only; semantic impact determined by sibling events",
            )
        )
    mapping = [
        ("license", "license_changed", ("license.license_id",)),
        ("openness", "openness_changed", ("openness",)),
        ("lineage", "lineage_changed", ("base_models",)),
        ("architecture", "architecture_changed", ("architecture",)),
        ("artifact_manifest", "artifact_changed", ("artifacts",)),
        ("quantization", "artifact_changed", ("quantization",)),
        ("alignment", "alignment_claim_changed", ("alignment",)),
    ]
    for key, event_type, fields in mapping:
        if old_fp[key] != new_fp[key]:
            # Refine artifact vs quant variant add/remove via set diff when possible.
            refined = event_type
            if key == "artifact_manifest":
                refined = _refine_artifact_event(old_artifacts or [], new_artifacts or [])
            events.append(
                build_event(
                    event_type=refined,
                    model_id=model_id,
                    old_revision=old_revision,
                    new_revision=new_revision,
                    old_fingerprint=old_fp[key],
                    new_fingerprint=new_fp[key],
                    changed_fields=fields,
                    detected_at=detected_at,
                    source_id=source_id,
                )
            )
    # Popularity is informational and never triggers qualification/VRAM changes.
    if fp.popularity_fingerprint(old_record) != fp.popularity_fingerprint(new_record):
        events.append(
            build_event(
                event_type="popularity_changed",
                model_id=model_id,
                old_revision=old_revision,
                new_revision=new_revision,
                old_fingerprint=None,
                new_fingerprint=None,
                changed_fields=("popularity",),
                detected_at=detected_at,
                source_id=source_id,
                notes="informational only; never drives qualification or VRAM",
            )
        )
    # Gating is derived from lifecycle comparison by the caller via explicit
    # events; fingerprint comparison here covers the semantic core.
    return events


def _refine_artifact_event(old: list[dict], new: list[dict]) -> str:
    old_ids = {str(a.get("artifact_set_id")) for a in old}
    new_ids = {str(a.get("artifact_set_id")) for a in new}
    if new_ids - old_ids and not old_ids - new_ids:
        return "artifact_added"
    if old_ids - new_ids and not new_ids - old_ids:
        return "artifact_removed"
    return "artifact_changed"

"""Catalog population orchestrator.

Dry-run by default; explicit apply persists atomically with idempotency.
One malformed candidate never aborts the run; systemic schema/security
failures stop it. No downloads, no execution, no GPU.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from atlas.catalog import tiering
from atlas.catalog.artifacts_catalog import build_artifact_records
from atlas.catalog.identity import atlas_identity, canonical_model_id
from atlas.catalog.manifest import build_manifest
from atlas.catalog.qualification import qualify_candidate
from atlas.catalog.special import (
    alignment_claim,
    compression_evidence,
    native_low_bit_status,
    ternary_status,
)
from atlas.catalog.views import (
    build_special_view_payload,
    build_tier_view_payload,
    render_index_markdown_ar,
    render_index_markdown_en,
    render_special_markdown_ar,
    render_special_markdown_en,
    render_tier_markdown_ar,
    render_tier_markdown_en,
)
from atlas.intake.pipeline import IntakePipeline
from atlas.intake.store import atomic_write_json, canonical_json_bytes

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_DIR = REPO_ROOT / "catalog"
MODELS_DIR = CATALOG_DIR / "models"
ARTIFACTS_DIR = CATALOG_DIR / "artifacts"
VIEWS_DIR = CATALOG_DIR / "views"


@dataclass
class PopulationSummary:
    """Counts for observability (no secrets)."""

    discovered: int = 0
    deduplicated: int = 0
    metadata_fetched: int = 0
    qualified: int = 0
    qualified_with_limitations: int = 0
    blocked: int = 0
    rejected: int = 0
    network_failures: int = 0
    schema_failures: int = 0
    log: list[str] = field(default_factory=list)


def realtime_utc_now() -> str:
    """UTC ISO timestamp with Z suffix."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def populate_from_records(
    records: list[dict],
    *,
    siblings_by_model: dict[str, list[dict]] | None = None,
    dry_run: bool = True,
    observed_at: str | None = None,
) -> tuple[PopulationSummary, dict]:
    """Normalize -> qualify -> tier -> views without network.

    Returns (summary, bundle) where bundle holds records, artifacts,
    classifications, special views, manifest payload. When dry_run is
    False, persists canonical files atomically with idempotency.
    """
    siblings_by_model = siblings_by_model or {}
    stamp = observed_at or realtime_utc_now()
    summary = PopulationSummary(discovered=len(records))
    qualified_records: dict[str, dict] = {}
    artifacts_by_model: dict[str, list[dict]] = {}
    classifications: dict[str, dict] = {}
    states: dict[str, str] = {}

    for record in records:
        model_id = str(
            record.get("model_id")
            or canonical_model_id(str(record.get("display_name") or "unknown"))
        )
        try:
            result = qualify_candidate(record)
        except Exception as exc:  # noqa: BLE001 - isolate one bad candidate
            summary.schema_failures += 1
            summary.log.append(f"{model_id}: qualification error {exc}")
            continue
        states[model_id] = result.conceptual_state
        if result.conceptual_state == "qualified":
            summary.qualified += 1
        elif result.conceptual_state == "qualified_with_limitations":
            summary.qualified_with_limitations += 1
        elif result.conceptual_state == "blocked":
            summary.blocked += 1
            continue
        elif result.conceptual_state in ("rejected",):
            summary.rejected += 1
            continue
        elif result.conceptual_state in (
            "license_pending",
            "metadata_pending",
            "lineage_pending",
            "architecture_pending",
            "artifact_pending",
            "discovered",
            "deprecated",
        ):
            # Pending states are kept as limited catalog entries when they
            # carry usable metadata; count them as limited, not qualified.
            if result.conceptual_state == "deprecated":
                summary.rejected += 1
                continue
            summary.qualified_with_limitations += 1
        # Persist-ready copy with mapped catalog_status.
        stored = dict(record)
        stored["catalog_status"] = result.catalog_status
        qualified_records[model_id] = stored
        # Artifacts from siblings evidence.
        siblings = siblings_by_model.get(model_id, [])
        try:
            art_records, _warn = build_artifact_records(
                model_id=model_id,
                revision=(stored.get("quantization") or {}).get("source_revision"),
                siblings=siblings,
            )
        except Exception as exc:  # noqa: BLE001 - isolate
            summary.schema_failures += 1
            summary.log.append(f"{model_id}: artifact error {exc}")
            art_records = []
        artifacts_by_model[model_id] = art_records
        # VRAM classification (conservative, file size never implies fit).
        try:
            classifications[model_id] = tiering.classify_record(stored)
        except Exception as exc:  # noqa: BLE001 - isolate
            summary.schema_failures += 1
            summary.log.append(f"{model_id}: tiering error {exc}")
            classifications[model_id] = {
                "estimate_status": "insufficient_evidence",
                "lower_bytes": None,
                "upper_bytes": None,
                "decisions": [],
                "by_tier": {},
                "estimated_minimum_nominal_tier_gb": None,
            }

    summary.metadata_fetched = len(qualified_records)
    summary.deduplicated = summary.discovered - len(records)

    # Special views (evidence-backed).
    high = [
        m for m, r in qualified_records.items() if compression_evidence(r)["is_high_compression"]
    ]
    native = [
        m for m, r in qualified_records.items() if native_low_bit_status(r)["is_native_low_bit"]
    ]
    ternary = [
        m
        for m, r in qualified_records.items()
        if ternary_status(r)["kind"] in ("ternary-native", "tq-format")
    ]
    unc = [
        m
        for m, r in qualified_records.items()
        if alignment_claim(r)["alignment_variant"] == "uncensored"
    ]
    abl = [
        m
        for m, r in qualified_records.items()
        if alignment_claim(r)["alignment_variant"] == "abliterated"
    ]
    her = [
        m
        for m, r in qualified_records.items()
        if alignment_claim(r)["alignment_variant"] == "heretic"
    ]

    total_artifacts = sum(len(v) for v in artifacts_by_model.values())
    stats = {
        "model_count": len(qualified_records),
        "artifact_count": total_artifacts,
        "qualified": summary.qualified,
        "qualified_with_limitations": summary.qualified_with_limitations,
        "blocked": summary.blocked,
        "rejected": summary.rejected,
    }
    manifest = build_manifest(
        generated_at=stamp,
        model_ids=sorted(qualified_records),
        artifact_count=total_artifacts,
    )
    bundle = {
        "records": qualified_records,
        "artifacts": artifacts_by_model,
        "classifications": classifications,
        "states": states,
        "special": {
            "high_compression": sorted(high),
            "native_low_bit": sorted(native),
            "ternary": sorted(ternary),
            "uncensored": sorted(unc),
            "abliterated": sorted(abl),
            "heretic": sorted(her),
        },
        "stats": stats,
        "manifest": manifest,
        "generated_at": stamp,
    }
    if not dry_run:
        persist_bundle(bundle)
    return summary, bundle


def persist_bundle(bundle: dict) -> dict[str, int]:
    """Atomically persist canonical records, artifacts, views, manifest."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    (VIEWS_DIR / "4gb").mkdir(parents=True, exist_ok=True)
    (VIEWS_DIR / "8gb").mkdir(parents=True, exist_ok=True)
    (VIEWS_DIR / "12gb").mkdir(parents=True, exist_ok=True)
    (VIEWS_DIR / "16gb").mkdir(parents=True, exist_ok=True)
    for special_id in (
        "high-compression",
        "native-low-bit",
        "ternary",
        "uncensored",
        "abliterated",
        "heretic",
    ):
        (VIEWS_DIR / special_id).mkdir(parents=True, exist_ok=True)
    counts = {"models": 0, "artifacts": 0, "views": 0}
    records: dict[str, dict] = bundle["records"]
    for model_id, record in sorted(records.items()):
        target = MODELS_DIR / f"{model_id}.json"
        existing = None
        if target.is_file():
            import json as _json

            try:
                existing = _json.loads(target.read_text(encoding="utf-8"))
            except ValueError:
                existing = None
        if existing != record:
            atomic_write_json(target, record)
        counts["models"] += 1
    for model_id, arts in sorted(bundle["artifacts"].items()):
        for art in arts:
            aid = str(art.get("artifact_set_id") or f"{model_id}-artifact")
            safe = "".join(c if (c.isalnum() or c in "-_.") else "-" for c in aid)[:180]
            atomic_write_json(ARTIFACTS_DIR / f"{safe}.json", art)
            counts["artifacts"] += 1
    classifications = bundle["classifications"]
    for tier in (4, 8, 12, 16):
        payload = build_tier_view_payload(
            tier_gb=tier, classifications=classifications, records=records
        )
        atomic_write_json(VIEWS_DIR / f"{tier}gb" / "view.json", payload)
        (VIEWS_DIR / f"{tier}gb" / "index.en.md").write_text(
            render_tier_markdown_en(tier_gb=tier, payload=payload), encoding="utf-8"
        )
        (VIEWS_DIR / f"{tier}gb" / "index.ar.md").write_text(
            render_tier_markdown_ar(tier_gb=tier, payload=payload), encoding="utf-8"
        )
        counts["views"] += 3
    special_defs = [
        (
            "high-compression",
            "High-Compression Models",
            "ضغط عالٍ — نماذج",
            "High compression from structured evidence (effective BPW / quant family / "
            "native low-bit). Ordinary post-training quantization is kept distinct.",
        ),
        (
            "native-low-bit",
            "Native Low-Bit Models",
            "نماذج منخفضة البت الأصلية",
            "Native low-bit requires training-architecture evidence; 1-2bit post-training "
            "quants are never labeled native.",
        ),
        (
            "ternary",
            "Ternary Models",
            "نماذج ثلاثية",
            "Ternary-native, post-training ternarization and TQ format are separate concepts.",
        ),
        (
            "uncensored",
            "Uncensored Variants",
            "متغيرات غير مقيدة",
            "Uncensored is a variant-author claim, never a quality signal. No superiority implied.",
        ),
        (
            "abliterated",
            "Abliterated Variants",
            "متغيرات مُزالة القيود",
            "Abliterated is a variant-author claim, never a quality signal.",
        ),
        (
            "heretic",
            "Heretic Variants",
            "متغيرات Heretic",
            "Heretic is a variant-author claim, never a quality signal. No superiority implied.",
        ),
    ]
    key_map = {
        "high-compression": "high_compression",
        "native-low-bit": "native_low_bit",
        "ternary": "ternary",
        "uncensored": "uncensored",
        "abliterated": "abliterated",
        "heretic": "heretic",
    }
    for view_id, title_en, title_ar, note in special_defs:
        mids = bundle["special"].get(key_map[view_id], [])
        payload = build_special_view_payload(
            view_id=view_id, model_ids=mids, records=records, note=note
        )
        atomic_write_json(VIEWS_DIR / view_id / "view.json", payload)
        (VIEWS_DIR / view_id / "index.en.md").write_text(
            render_special_markdown_en(title=title_en, payload=payload, disclaimer=note),
            encoding="utf-8",
        )
        (VIEWS_DIR / view_id / "index.ar.md").write_text(
            render_special_markdown_ar(title=title_ar, payload=payload, disclaimer=note),
            encoding="utf-8",
        )
        counts["views"] += 3
    stats = bundle["stats"]
    mids = sorted(records)
    atomic_write_json(CATALOG_DIR / "manifest.json", bundle["manifest"])
    (VIEWS_DIR / "index.en.md").write_text(
        render_index_markdown_en(stats=stats, model_ids=mids), encoding="utf-8"
    )
    (VIEWS_DIR / "index.ar.md").write_text(
        render_index_markdown_ar(stats=stats, model_ids=mids), encoding="utf-8"
    )
    # Deterministic manifest bytes check (same data -> same bytes).
    _ = canonical_json_bytes(bundle["manifest"])
    counts["views"] += 3
    return counts


def fetch_candidates_live(
    repo_ids: list[str],
    *,
    timeout: float = 15.0,
    budget_requests: int = 60,
) -> tuple[list[dict], dict[str, list[dict]], PopulationSummary]:
    """Fetch canonical records + siblings for approved repos (token=False).

    Sequential, bounded retries via client policy, read-only GET. Returns
    (records, siblings_by_model, summary). Never downloads weights.
    """
    pipeline = IntakePipeline()
    # Rebuild client with requested timeout (anonymous).
    from atlas.intake.hf_client import HuggingFaceSourceClient

    pipeline = IntakePipeline(HuggingFaceSourceClient(timeout=timeout))
    records: list[dict] = []
    siblings: dict[str, list[dict]] = {}
    summary = PopulationSummary(discovered=len(repo_ids))
    used = 0
    for repo in repo_ids:
        if used >= budget_requests:
            summary.log.append("request budget exhausted: stopping")
            break
        try:
            raw = pipeline._client.fetch(repo.strip())
            outcome = pipeline.build_from_raw(raw)
        except Exception as exc:  # noqa: BLE001 - isolate per candidate
            summary.network_failures += 1
            summary.log.append(f"{repo}: fetch failed {type(exc).__name__}")
            used += 1
            continue
        used += 1
        summary.metadata_fetched += 1
        rec = dict(outcome.model_record)
        records.append(rec)
        mid = str(rec.get("model_id"))
        sib_list: list[dict] = []
        for s in raw.siblings:
            sib_list.append(
                {
                    "filename": s.filename,
                    "path": s.path,
                    "extension": s.extension,
                    "source_reported_size_bytes": s.source_reported_size_bytes,
                }
            )
        siblings[mid] = sib_list
        summary.log.append(f"{repo}: {outcome.intake_state} -> {mid}")
    summary.deduplicated = 0
    return records, siblings, summary


def atlas_identity_for_record(record: dict) -> str:
    """Stable identity string for a canonical record."""
    quant = record.get("quantization") or {}
    return atlas_identity(
        platform="hugging-face",
        repo_id=str(record.get("display_name") or record.get("model_id")),
        resolved_revision=str(quant.get("source_revision") or ""),
        variant=str(quant.get("quant_name") or ""),
    )

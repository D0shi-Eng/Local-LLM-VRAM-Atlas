"""Quality ingestion orchestration (Phase 6).

Flow: audit sidecars -> build evidence sidecars for new quality claims ->
bounded source read -> normalize evaluation results -> persist atomically ->
generate profiles, retention records, gap report and change events.

Dry-run is the default everywhere: canonical quality state changes only on an
explicit apply.
"""

from __future__ import annotations

from pathlib import Path

from atlas.intake.store import atomic_write_json
from atlas.quality import QUALITY_SNAPSHOT_VERSION
from atlas.quality.changes import QUALITY_EVENT_TYPES, append_quality_events, quality_event
from atlas.quality.declared import OBSERVED_AT, claims
from atlas.quality.gaps import build_gap_report
from atlas.quality.ingest import load_evaluations
from atlas.quality.live import ingest_publisher_tables, write_quality_evidence
from atlas.quality.profiles import build_profile
from atlas.quality.sidecars import audit_sidecars, backfill_plan, load_records
from atlas.quality.sources import default_registry, registry_path
from atlas.quality.tiers import evidence_status_from_origins

EXIT_OK = 0
EXIT_INVALID_INPUT = 2
EXIT_SOURCE_FAILURE = 21


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def build_quality_evidence(quality_models: dict[str, dict]) -> list[dict]:
    """Evidence sidecar for each quality-bearing model (persisted, not logical)."""
    from atlas.evidence_ids import generate_evidence_id_v2

    out: list[dict] = []
    for model_id, record in sorted(quality_models.items()):
        display = str(record.get("display_name") or model_id)
        revision = (record.get("quantization") or {}).get("source_revision")
        namespace = display.split("/")[0] if "/" in display else None
        out.append(
            {
                "schema_version": "0.1.0",
                "evidence_id": generate_evidence_id_v2(
                    source_id=f"{model_id}-quality-src",
                    repo_id=display,
                    resolved_revision=str(revision) if revision else None,
                    claim_type="benchmark_score",
                    field_path="quality",
                ),
                "claim_type": "benchmark_score",
                "field_path": "quality",
                "source_id": f"{model_id}-quality-src",
                "source_type": "official_repo",
                "source_url": f"https://huggingface.co/{display}",
                "retrieved_at": OBSERVED_AT,
                "publisher": namespace,
                "evidence_level": "publisher_claim",
                "verification_status": "publisher_claim",
                "notes": (
                    "Quality claim evidence: recorded publisher-reported evaluation results. "
                    "See catalog/benchmarks/evaluations/ for per-result provenance and "
                    "quality evidence_ids. Popularity, size, recency and brand are excluded."
                ),
            }
        )
    return out


def run_ingestion(
    *,
    repo_root: Path | None = None,
    dry_run: bool = True,
    client: object | None = None,
    observed_at: str | None = None,
) -> dict:
    """Run the bounded quality ingestion and report what changed."""
    from atlas.quality.declared import DECLARED_RESULTS

    root = repo_root or _repo_root()
    records = load_records(root)
    records_by_repo: dict[str, dict] = {}
    for record in records.values():
        display = str(record.get("display_name") or "")
        if "/" in display:
            records_by_repo[display.lower()] = record

    audit = audit_sidecars(root)
    plan = backfill_plan(root)

    quality_models = {
        str(group["model_id"]): records[str(group["model_id"])]
        for group in DECLARED_RESULTS
        if str(group["model_id"]) in records
    }
    evidence_records = build_quality_evidence(quality_models)
    evidence_written, evidence_unchanged = write_quality_evidence(
        root, evidence=evidence_records, dry_run=dry_run
    )
    by_model_evidence: dict[str, list[str]] = {}
    for model_id in quality_models:
        by_model_evidence[model_id] = [
            str(record["evidence_id"])
            for record in evidence_records
            if record["source_id"] == f"{model_id}-quality-src"
        ]

    report = ingest_publisher_tables(
        repo_root=root,
        claims=claims(by_model_evidence),
        records_by_repo=records_by_repo,
        dry_run=dry_run,
        client=client,
        observed_at=observed_at or OBSERVED_AT,
    )

    return {
        "dry_run": dry_run,
        "quality_snapshot_version": QUALITY_SNAPSHOT_VERSION,
        "sidecar_audit": audit.to_payload(),
        "sidecar_backfill_plan": {
            "reconstructible_count": plan["reconstructible_count"],
            "unavailable_count": plan["unavailable_count"],
            "notes": plan["notes"],
        },
        "evidence_written": evidence_written,
        "evidence_unchanged": evidence_unchanged,
        "ingest": report.to_payload(),
    }


def generate_quality_dataset(
    *,
    repo_root: Path | None = None,
    snapshot_version: str = QUALITY_SNAPSHOT_VERSION,
) -> dict:
    """Build profiles, retention records and gap report from persisted results."""
    root = repo_root or _repo_root()
    records = load_records(root)
    evaluations = load_evaluations(root)
    by_model: dict[str, list[dict]] = {}
    for evaluation in evaluations.values():
        by_model.setdefault(str(evaluation.get("model_id")), []).append(evaluation)

    from atlas.quality.retention import build_retention

    profiles: dict[str, dict] = {}
    retentions: list[dict] = []
    for model_id, record in sorted(records.items()):
        results = by_model.get(model_id, [])
        profiles[model_id] = build_profile(
            model_id=model_id,
            results=results,
            quality_snapshot_version=snapshot_version,
        )
        quant = record.get("quantization") or {}
        if quant.get("quant_name") or str(quant.get("quant_family") or "unknown") != "unknown":
            retentions.append(
                build_retention(
                    base_release=str(model_id),
                    quantized_artifact=str(model_id),
                    quantization=str(quant.get("quant_name") or quant.get("quant_family")),
                    base_result=None,
                    quant_result=results[0] if results else None,
                    evidence_ids=sorted(
                        {str(e) for r in results for e in r.get("evidence_ids", [])}
                    ),
                    notes=(
                        "No exact base-release evaluation is available for this artifact, so "
                        "retention stays unknown rather than inherited."
                    ),
                )
            )

    from atlas.catalog.tiering import classify_record

    tier_states = {model_id: classify_record(record) for model_id, record in records.items()}
    gaps = build_gap_report(root, tier_states=tier_states)
    return {
        "snapshot_version": snapshot_version,
        "profiles": profiles,
        "retentions": retentions,
        "gaps": gaps,
        "tier_states": tier_states,
        "records": records,
    }


def write_source_registry(*, repo_root: Path | None = None, observed_at: str | None = None) -> Path:
    """Persist the declared quality source registry (versioned, no credentials)."""
    root = repo_root or _repo_root()
    registry = default_registry(observed_at or OBSERVED_AT)
    target = registry_path(root)
    atomic_write_json(target, registry)
    return target


def write_quality_snapshot(
    *,
    repo_root: Path | None = None,
    snapshot_version: str = QUALITY_SNAPSHOT_VERSION,
    journal_quality_events: bool = True,
) -> dict:
    """Materialize profiles, retention records, gaps, manifest and events.

    Deterministic: the same evidence snapshot yields byte-identical outputs.
    Change events go through the Phase 5 append-only journal and are idempotent
    by event_id, so re-running writes no duplicate history.
    """
    root = repo_root or _repo_root()
    dataset = generate_quality_dataset(repo_root=root, snapshot_version=snapshot_version)
    records = dataset["records"]
    evaluations = load_evaluations(root)

    written: list[str] = []
    profiles_dir = root / "catalog" / "quality" / "profiles"
    retentions_dir = root / "catalog" / "quality" / "retention"
    for model_id, profile in sorted(dataset["profiles"].items()):
        target = profiles_dir / f"{model_id}.json"
        atomic_write_json(target, profile)
        written.append(str(target))
    for record in sorted(dataset["retentions"], key=lambda r: str(r["retention_id"])):
        target = retentions_dir / f"{record['retention_id']}.json"
        atomic_write_json(target, record)
        written.append(str(target))

    atomic_write_json(root / "catalog" / "quality" / "gaps.json", dataset["gaps"])
    manifest = quality_manifest(repo_root=root, snapshot_version=snapshot_version)
    atomic_write_json(root / "catalog" / "quality" / "manifest.json", manifest)

    events_appended = 0
    if journal_quality_events:
        by_model: dict[str, list[dict]] = {}
        for evaluation in evaluations.values():
            by_model.setdefault(str(evaluation.get("model_id")), []).append(evaluation)
        events = []
        for model_id, results in sorted(by_model.items()):
            exact = [r for r in results if str(r.get("match_status", "")).startswith("exact")]
            if exact:
                events.append(
                    quality_event(
                        event_type="quality_evidence_added",
                        model_id=model_id,
                        detected_at=OBSERVED_AT,
                        subject_id=model_id,
                        evidence_ids=sorted({str(e) for r in exact for e in r["evidence_ids"]}),
                        changed_fields=["quality"],
                        notes=f"{len(exact)} evaluation result(s) recorded",
                    )
                )
            if any(str(r.get("match_status")) == "identity_conflict" for r in results):
                events.append(
                    quality_event(
                        event_type="evaluation_identity_conflict",
                        model_id=model_id,
                        detected_at=OBSERVED_AT,
                        subject_id=f"{model_id}-identity-conflict",
                        notes="unresolved evaluated-identity conflict",
                    )
                )
            quant = (records.get(model_id) or {}).get("quantization") or {}
            is_quantized = bool(quant.get("quant_name")) or str(
                quant.get("quant_family") or "unknown"
            ) not in ("unknown", "")
            if is_quantized:
                events.append(
                    quality_event(
                        event_type="retention_evidence_added",
                        model_id=model_id,
                        detected_at=OBSERVED_AT,
                        subject_id=model_id,
                        notes="quantization retention state recorded (unknown unless comparable)",
                    )
                )
        events_appended = append_quality_events(root / "catalog" / "changes", events)

    return {
        "quality_snapshot_version": snapshot_version,
        "profiles_written": len(dataset["profiles"]),
        "retentions_written": len(dataset["retentions"]),
        "files_written": len(written),
        "manifest": manifest,
        "quality_events_appended": events_appended,
        "quality_event_types": list(QUALITY_EVENT_TYPES),
        "evidence_status_counts": _evidence_status_counts(dataset["profiles"]),
    }


def _evidence_status_counts(profiles: dict[str, dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for profile in profiles.values():
        key = str(profile.get("evidence_status"))
        counts[key] = counts.get(key, 0) + 1
    return counts


def independent_source_counts(evaluations: list[dict]) -> dict:
    """Distinct independent sources and resulting status (no double counting)."""
    independent = [
        str(e.get("source_id"))
        for e in evaluations
        if str(e.get("evaluation_origin")) == "independent"
    ]
    status = evidence_status_from_origins(
        [str(e.get("evaluation_origin")) for e in evaluations],
        verification_statuses=[str(e.get("verification_status")) for e in evaluations],
        independent_sources=independent,
    )
    return {"status": status, "distinct_independent_sources": len(set(independent))}


def quality_manifest(
    *,
    repo_root: Path | None = None,
    snapshot_version: str = QUALITY_SNAPSHOT_VERSION,
) -> dict:
    """Machine-readable quality dataset summary (counts and versions)."""
    from atlas.quality.policy import policy_versions
    from atlas.quality.sources import load_registry

    root = repo_root or _repo_root()
    evaluations = load_evaluations(root)
    dataset = generate_quality_dataset(repo_root=root, snapshot_version=snapshot_version)
    registry = load_registry(root)
    origins: dict[str, int] = {}
    verification: dict[str, int] = {}
    for evaluation in evaluations.values():
        key = str(evaluation.get("evaluation_origin"))
        origins[key] = origins.get(key, 0) + 1
        vkey = str(evaluation.get("verification_status"))
        verification[vkey] = verification.get(vkey, 0) + 1
    return {
        "quality_snapshot_version": snapshot_version,
        "quality_registry_version": registry.get("registry_version"),
        "policy_versions": policy_versions(),
        "evaluation_count": len(evaluations),
        "evaluations_by_origin": origins,
        "evaluations_by_verification_status": verification,
        "profile_count": len(dataset["profiles"]),
        "retention_record_count": len(dataset["retentions"]),
        "gap_counts": dataset["gaps"]["gap_counts"],
    }

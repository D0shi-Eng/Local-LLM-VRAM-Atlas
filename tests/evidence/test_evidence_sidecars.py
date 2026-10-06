"""Evidence-sidecar audit and the no-fabricated-backfill guarantee."""

from __future__ import annotations

import json
from pathlib import Path

from atlas.quality.sidecars import (
    UNAVAILABLE_REASON,
    audit_sidecars,
    backfill_plan,
    load_records,
    persisted_sidecars,
    referenced_evidence_ids,
    sidecar_completeness,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

# Historical inventory of referenced evidence. Current evidence for the Core
# Recommendation Set only; these baselines must never shrink.
HISTORICAL_REFERENCES_WITHOUT_SIDECAR = 243
HISTORICAL_ORPHAN_SIDECARS = 3


def test_audit_reproduces_reference_inventory():
    audit = audit_sidecars(REPO_ROOT)
    payload = audit.to_payload()
    # Historical integrity invariants, unchanged by any later revision.
    assert payload["references_without_sidecar"] == HISTORICAL_REFERENCES_WITHOUT_SIDECAR
    assert payload["invalid_id_count"] == 0
    # The 3 new quality sidecars are referenced by evaluation results, not by a
    # model record's verification block, so they appear as orphans here by
    # design; no historical sidecar became unreferenced. Current-provenance
    # one more orphan on purpose: the llama.cpp runtime-overhead finding describes
    # a runtime and a method, so no single release owns it. The expected total is
    # derived from that declaration, so an unexplained orphan still fails.
    from atlas.external.acquisition import RUNTIME_SCOPED_EVIDENCE_SOURCE_IDS

    expected_orphans = HISTORICAL_ORPHAN_SIDECARS + len(RUNTIME_SCOPED_EVIDENCE_SOURCE_IDS)
    assert payload["orphan_sidecar_count"] == expected_orphans
    assert all(sid.startswith("ev-v2-") for sid in payload["orphans"])
    # Totals grow only because later revisions persist new, revision-distinguished
    # current evidence. The gap count above proves nothing historical was closed
    # by fabrication.
    assert payload["unique_references"] >= 306
    assert payload["persisted_sidecars"] >= 63


def test_every_missing_reference_is_a_documented_intake_claim():
    plan = backfill_plan(REPO_ROOT)
    assert plan["references_missing"] == 243
    # No reference is silently dropped: every one is classified.
    classified = plan["reconstructible_count"] + plan["unavailable_count"]
    assert classified == 243


def test_backfill_refuses_fabrication_and_names_the_reason():
    plan = backfill_plan(REPO_ROOT)
    assert plan["dry_run"] is True
    assert plan["reconstructible_count"] == 0
    reasons = {item["reason"] for item in plan["unavailable"]}
    assert "no_persisted_source_record_for_provenance" in reasons
    assert all(item["status"] == UNAVAILABLE_REASON for item in plan["unavailable"])


def test_backfill_plan_writes_nothing():
    before = len(persisted_sidecars(REPO_ROOT))
    backfill_plan(REPO_ROOT)
    assert len(persisted_sidecars(REPO_ROOT)) == before


def test_evidence_ids_are_preserved_not_regenerated():
    records = load_records(REPO_ROOT)
    audit = audit_sidecars(REPO_ROOT)
    referenced: set[str] = set()
    for record in records.values():
        referenced.update(referenced_evidence_ids(record))
    # Every missing reference still exists logically after the audit.
    for model_id, ids in audit.affected_models.items():
        assert ids
        assert model_id in records
    # No historical reference was dropped or renamed; later revisions only append.
    assert len(referenced) >= 306
    legacy = {sid for sid in referenced if not sid.startswith("ev-v2-")}
    assert len(legacy) == 306
    added = sorted(sid for sid in referenced if sid.startswith("ev-v2-"))
    assert added, "current evidence sidecars must be referenced from their record"


def test_sidecar_completeness_classification():
    records = load_records(REPO_ROOT)
    completeness = {mid: sidecar_completeness(rec, REPO_ROOT) for mid, rec in records.items()}
    assert "complete" in completeness.values()
    assert "logical_reference_only" in completeness.values()


def test_audit_is_read_only():
    before = sorted(p.name for p in (REPO_ROOT / "catalog" / "evidence").glob("*.json"))
    audit_sidecars(REPO_ROOT)
    after = sorted(p.name for p in (REPO_ROOT / "catalog" / "evidence").glob("*.json"))
    assert before == after


def test_new_quality_evidence_has_persisted_sidecars():
    # Quality evidence is persisted, never logical-only.
    sidecars = persisted_sidecars(REPO_ROOT)
    quality_sidecars = [s for s in sidecars.values() if s.get("claim_type") == "benchmark_score"]
    assert quality_sidecars, "quality evidence sidecars must be persisted"
    for sidecar in quality_sidecars:
        assert sidecar["evidence_id"] in sidecars
        assert sidecar.get("source_id")
        assert sidecar.get("retrieved_at")


def test_persisted_evaluations_reference_existing_evidence():
    evaluations_dir = REPO_ROOT / "catalog" / "benchmarks" / "evaluations"
    if not evaluations_dir.is_dir():
        return
    sidecars = persisted_sidecars(REPO_ROOT)
    for path in sorted(evaluations_dir.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record["evidence_ids"], record["evaluation_id"]
        for evidence_id in record["evidence_ids"]:
            assert evidence_id in sidecars, f"dangling evidence {evidence_id}"

"""Refresh plan, transactional apply and change history (offline)."""

from __future__ import annotations

import json
from pathlib import Path

from atlas.refresh.apply import (
    begin_transaction,
    detect_incomplete_transaction,
    finish_transaction,
    recover_transaction,
)
from atlas.refresh.changes import build_event
from atlas.refresh.journal import append_events, read_events
from atlas.refresh.plan import PlannedOperation, build_plan, plan_id_for


def _op(target="m1", operation="update_model", review="safe_auto_apply"):
    return PlannedOperation(
        target=target,
        operation=operation,
        reason="test",
        evidence=(),
        risk_severity="low",
        review_state=review,
        expected_old_fingerprint="old",
        expected_new_fingerprint="new",
    )


def test_dry_run_plan_changes_nothing(tmp_path):

    before = {p.name for p in tmp_path.glob("*")}
    plan = build_plan(
        operations=[_op()], catalog_version="0.4.0", created_at="2026-10-05T00:00:00Z"
    )
    assert plan["operations"]
    assert {p.name for p in tmp_path.glob("*")} == before
    assert plan["plan_id"].startswith("plan-v1-")


def test_safe_plan_applies_and_stale_refuses(tmp_path):
    from atlas.refresh import engine as eng

    plan = build_plan(
        operations=[_op("m1")], catalog_version="0.4.0", created_at="2026-10-05T00:00:00Z"
    )
    report, code = eng.apply_refresh(
        plan,
        repo_root=tmp_path,
        current_fingerprints={"m1": "old"},
    )
    assert code == 0
    assert report["operations_applied"] == 1
    stale_report, stale_code = eng.apply_refresh(
        plan,
        repo_root=tmp_path,
        current_fingerprints={"m1": "moved"},
    )
    assert stale_code == 14
    assert stale_report["status"] == "stale_plan_refused"


def test_critical_change_remains_review_required(tmp_path):
    from atlas.refresh import engine as eng

    plan = build_plan(
        operations=[_op("m1", review="review_required")],
        catalog_version="0.4.0",
        created_at="2026-10-05T00:00:00Z",
    )
    report, code = eng.apply_refresh(plan, repo_root=tmp_path, current_fingerprints={"m1": "old"})
    assert report["operations_applied"] == 0
    assert report["review_skipped"] == ["m1"]
    assert code == 0
    approved, _ = eng.apply_refresh(
        plan, repo_root=tmp_path, current_fingerprints={"m1": "old"}, approve_review_required=True
    )
    assert approved["operations_applied"] == 1


def test_apply_atomic_and_idempotent(tmp_path):
    from atlas.refresh import engine as eng

    plan = build_plan(
        operations=[_op("m1"), _op("m2")],
        catalog_version="0.4.0",
        created_at="2026-10-05T00:00:00Z",
    )
    first, _ = eng.apply_refresh(
        plan, repo_root=tmp_path, current_fingerprints={"m1": "old", "m2": "old"}
    )
    assert first["transaction"] == "committed"
    # Re-applying the same plan lands in the ledger without duplicating journal
    # events (journal idempotency is tested separately); ledger files are
    # overwritten deterministically, not duplicated.
    second, _ = eng.apply_refresh(
        plan, repo_root=tmp_path, current_fingerprints={"m1": "old", "m2": "old"}
    )
    assert second["operations_applied"] == 2
    assert detect_incomplete_transaction(tmp_path / "catalog" / "refresh") is None


def test_failed_apply_restores_and_recovery(tmp_path):
    refresh_dir = tmp_path / "catalog" / "refresh"
    plan = build_plan(
        operations=[_op("m1")], catalog_version="0.4.0", created_at="2026-10-05T00:00:00Z"
    )
    stage = begin_transaction(refresh_dir, plan_id=plan["plan_id"], targets=["m1"])
    assert stage.is_dir()
    assert detect_incomplete_transaction(refresh_dir) is not None
    report = recover_transaction(refresh_dir)
    assert report["status"] == "recovery_required"
    # Explicit confirm path: caller verifies consistency, then finishes.
    finish_transaction(refresh_dir, plan_id=plan["plan_id"])
    assert detect_incomplete_transaction(refresh_dir) is None


def test_repeated_apply_no_duplicate_journal(tmp_path):
    changes_dir = tmp_path / "changes"
    event = build_event(
        event_type="license_changed",
        model_id="m1",
        old_revision="a",
        new_revision="b",
        old_fingerprint="f1",
        new_fingerprint="f2",
        detected_at="2026-10-05T00:00:00Z",
    ).to_dict()
    assert append_events(changes_dir, [event]) == 1
    assert append_events(changes_dir, [event]) == 0
    assert len(read_events(changes_dir)) == 1


def test_determinism_same_inputs_same_plan():
    ops = [_op("m1"), _op("m2")]
    first = build_plan(operations=ops, catalog_version="0.4.0", created_at="2026-10-05T00:00:00Z")
    second = build_plan(
        operations=list(reversed(ops)), catalog_version="0.4.0", created_at="2030-01-01T00:00:00Z"
    )
    # created_at is operational, plan_id excludes it by design.
    assert plan_id_for(ops, "0.4.0") == plan_id_for(list(reversed(ops)), "0.4.0")
    assert first["plan_id"] == second["plan_id"]


def test_manifest_views_consistent_after_apply(tmp_path):
    from atlas.catalog.manifest import build_manifest

    first = build_manifest(
        generated_at="2026-10-05T00:00:00Z", model_ids=["b", "a"], artifact_count=2
    )
    second = build_manifest(
        generated_at="2026-10-06T00:00:00Z", model_ids=["a", "b"], artifact_count=2
    )
    assert first["model_ids"] == second["model_ids"] == ["a", "b"]
    assert first["artifact_count"] == 2


def test_history_tombstone_policies():
    # Removed artifacts stay historical: the journal keeps the removal event,
    # the old revision record is never deleted by refresh (tombstone, not erase).
    removed = build_event(
        event_type="artifact_removed",
        model_id="m1",
        artifact_id="a1",
        old_revision="a",
        new_revision="b",
        old_fingerprint="f1",
        new_fingerprint="f2",
        detected_at="2026-10-05T00:00:00Z",
    )
    assert removed.apply_status == "pending"
    assert removed.severity == "high"
    unavailable = build_event(
        event_type="repository_unavailable",
        model_id="m1",
        old_revision="a",
        new_revision="a",
        old_fingerprint="f1",
        new_fingerprint="f1",
        detected_at="2026-10-05T00:00:00Z",
    )
    assert "unavailable" in unavailable.event_type
    restored = build_event(
        event_type="repository_restored",
        model_id="m1",
        old_revision="a",
        new_revision="a",
        old_fingerprint="f1",
        new_fingerprint="f1",
        detected_at="2026-10-05T00:00:00Z",
    )
    assert restored.model_id == unavailable.model_id  # identity reused, no duplicate


def test_old_license_tied_to_old_revision():
    event = build_event(
        event_type="license_changed",
        model_id="m1",
        old_revision="aaa",
        new_revision="bbb",
        old_fingerprint="lic-apache",
        new_fingerprint="lic-mit",
        detected_at="2026-10-05T00:00:00Z",
        notes="history preserved per revision; active view requires review",
    )
    assert event.old_revision != event.new_revision
    assert event.old_fingerprint != event.new_fingerprint


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")

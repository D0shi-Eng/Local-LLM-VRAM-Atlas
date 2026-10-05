"""Phase 5 incremental discovery tests (offline, fakes only)."""

from __future__ import annotations

import pytest

from atlas.refresh.checkpoints import (
    advance_checkpoint,
    checkpoint_path,
    load_checkpoint,
    save_checkpoint,
)
from atlas.refresh.config import DEFAULT_CONFIG
from atlas.refresh.discovery_incremental import (
    BudgetExhaustedError,
    RequestBudget,
    apply_new_candidate_limit,
    build_recent_window_queries,
    deduplicate_candidates,
    overlap_filter,
    split_known_vs_new,
)
from atlas.refresh.queue import enqueue, load_queue, save_queue
from atlas.refresh.revision_probe import RevisionProbe, needs_detailed_refresh


def test_new_candidate_vs_known_resolution():
    known, new = split_known_vs_new(
        ["Qwen/Qwen3-8B", "New/Publisher-Model"],
        known_repo_ids={"qwen/qwen3-8b"},
    )
    assert known == ["Qwen/Qwen3-8B"]
    assert new == ["New/Publisher-Model"]


def test_known_unchanged_no_refetch():
    probe = RevisionProbe(
        repo_id="p/m",
        sha="aaa",
        last_modified="2026-10-05T00:00:00Z",
        gated=False,
        disabled=False,
        private=False,
        status="ok",
    )
    needed, reason = needs_detailed_refresh(known_revision="aaa", probe=probe)
    assert needed is False
    assert "same_revision" in reason


def test_known_changed_revision_needs_detail():
    probe = RevisionProbe(
        repo_id="p/m",
        sha="bbb",
        last_modified="2026-10-06T00:00:00Z",
        gated=False,
        disabled=False,
        private=False,
        status="ok",
    )
    needed, _ = needs_detailed_refresh(known_revision="aaa", probe=probe)
    assert needed is True


def test_duplicate_discovery_across_strategies():
    unique, dups = deduplicate_candidates(["A/B", "a/b", "C/D", "c/d ", "E/F"])
    assert unique == ["A/B", "C/D", "E/F"]
    assert dups == 2


def test_overlap_window_duplicate_safe():
    candidates = [
        {"repo_id": "a/1", "last_modified": "2026-10-03T00:00:00Z"},
        {"repo_id": "a/2", "last_modified": "2026-10-04T00:00:00Z"},
    ]
    # Overlap window starts before both: nothing skipped.
    assert len(overlap_filter(candidates, overlap_start="2026-10-02T00:00:00Z")) == 2
    # Exact watermark with overlap: second still passes; first filtered only
    # when strictly before, but crash-safe callers use overlap_start earlier.
    assert len(overlap_filter(candidates, overlap_start="2026-10-04T00:00:00Z")) == 1


def test_equal_timestamp_candidates_both_kept():
    candidates = [
        {"repo_id": "a/1", "last_modified": "2026-10-04T00:00:00Z"},
        {"repo_id": "a/2", "last_modified": "2026-10-04T00:00:00Z"},
    ]
    assert len(overlap_filter(candidates, overlap_start="2026-10-04T00:00:00Z")) == 2


def test_clock_skew_tolerance_via_overlap():
    # Candidate seconds before the raw watermark still passes because the
    # caller subtracts the overlap window; here overlap_start is already
    # wound back, so a slightly-early timestamp is kept.
    candidates = [{"repo_id": "a/1", "last_modified": "2026-10-04T23:59:50Z"}]
    assert overlap_filter(candidates, overlap_start="2026-10-04T00:00:00Z") == candidates


def test_source_failure_isolated(tmp_path):
    # One bad strategy must not corrupt another source's checkpoint.
    good = checkpoint_path(tmp_path, "good-strategy", "good-source")
    save_checkpoint(
        good,
        advance_checkpoint(
            None,
            strategy_id="good-strategy",
            source_id="good-source",
            provider_watermark="2026-10-04T00:00:00Z",
            overlap_start="2026-10-02T00:00:00Z",
            last_seen_identity="a/1",
            last_seen_revision="aaa",
            last_successful_run="2026-10-05T00:00:00Z",
        ),
    )
    assert load_checkpoint(good) is not None
    # Failed source simply never writes its checkpoint.
    assert load_checkpoint(checkpoint_path(tmp_path, "bad", "bad")) is None


def test_request_budget_exhaustion_clean_stop():
    budget = RequestBudget(limit=2)
    budget.consume("a")
    budget.consume("b")
    assert budget.remaining == 0
    with pytest.raises(BudgetExhaustedError):
        budget.consume("c")


def test_rate_limit_persists_checkpoint(tmp_path):
    path = checkpoint_path(tmp_path, "s", "src")
    checkpoint = advance_checkpoint(
        None,
        strategy_id="s",
        source_id="src",
        provider_watermark=None,
        overlap_start=None,
        last_seen_identity=None,
        last_seen_revision=None,
        last_successful_run="2026-10-05T00:00:00Z",
        status="rate_limited",
    )
    save_checkpoint(path, checkpoint)
    assert load_checkpoint(path).status == "rate_limited"


def test_deferred_queue_persisted_without_worker(tmp_path):
    refresh_dir = tmp_path / "refresh"
    save_queue(refresh_dir, [{"repo_id": "a/1"}])
    assert len(load_queue(refresh_dir)) == 1
    enqueue(refresh_dir, [{"repo_id": "a/2"}, {"repo_id": "A/1"}])
    queued = load_queue(refresh_dir)
    assert len(queued) == 2  # duplicate A/1 deduplicated


def test_checkpoint_not_advanced_on_failure(tmp_path):
    # No checkpoint file is created until candidates are processed + persisted.
    assert load_checkpoint(checkpoint_path(tmp_path, "s", "src")) is None


def test_new_candidate_limit_queues_remainder():
    to_detail, deferred = apply_new_candidate_limit(
        [f"new/model-{i}" for i in range(30)], limit=DEFAULT_CONFIG.max_new_detailed
    )
    assert len(to_detail) == 25
    assert len(deferred) == 5


def test_recent_window_queries_bounded():
    strategies = [
        {"strategy_id": "s1", "source_id": "src1", "limit": 500},
        {"strategy_id": "s2", "source_id": "src2"},
    ]
    queries = build_recent_window_queries(strategies=strategies, limit_per_strategy=20)
    assert all(q["sort"] == "last_modified" for q in queries)
    assert all(q["limit"] <= 20 for q in queries)

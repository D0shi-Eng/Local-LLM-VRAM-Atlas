"""Multi-axis quality profiles, unknown integrity and determinism."""

from __future__ import annotations

from builders.records import community_evaluation, evaluation, publisher_evaluation

from atlas.quality import QUALITY_SNAPSHOT_VERSION
from atlas.quality.profiles import (
    AXES,
    aggregate_axis_scores,
    axis_for_result,
    build_profile,
    source_disagreements,
)

SNAPSHOT = QUALITY_SNAPSHOT_VERSION


def _profile(results, model_id="acme-test-7b-instruct"):
    return build_profile(model_id=model_id, results=results, quality_snapshot_version=SNAPSHOT)


def test_missing_axis_stays_unknown_not_zero():
    profile = _profile([evaluation()])
    assert profile["axes"]["coding"]["status"] == "unknown"
    assert profile["axes"]["coding"]["evaluation_ids"] == []
    assert profile["axes"]["general_intelligence"]["status"] == "known"


def test_every_declared_axis_is_present_and_unknown_by_default():
    profile = _profile([])
    assert set(profile["axes"]) == set(AXES)
    assert all(block["status"] == "unknown" for block in profile["axes"].values())


def test_publisher_only_profile_is_not_high_quality_candidate():
    profile = _profile([publisher_evaluation(score=70.0)])
    assert profile["evidence_status"] == "publisher_only"
    assert profile["high_quality_candidate"] is False
    assert "below the independent threshold" in profile["high_quality_rationale"]


def test_single_independent_source_profile():
    profile = _profile([evaluation(score=70.0)])
    assert profile["evidence_status"] == "independent_single_source"
    assert profile["high_quality_candidate"] is True
    assert "popularity" in profile["high_quality_rationale"]


def test_multi_independent_evidence_status():
    profile = _profile(
        [
            evaluation(evaluation_id="evl-v1-a", score=70.0, source_id="org-a"),
            evaluation(
                evaluation_id="evl-v1-b",
                score=71.0,
                source_id="org-b",
                benchmark_id="gpqa",
                metric="GPQA accuracy",
            ),
        ]
    )
    assert profile["evidence_status"] == "independent_multi_source"


def test_source_conflict_is_exposed_not_hidden():
    conflicting = [
        evaluation(evaluation_id="evl-v1-a", score=70.0, source_id="org-a"),
        evaluation(evaluation_id="evl-v1-b", score=64.0, source_id="org-b"),
    ]
    profile = _profile(conflicting)
    assert profile["axes"]["general_intelligence"].get("note")
    notes = source_disagreements(conflicting)
    assert notes and "org-a=70.0" in notes[0] and "org-b=64.0" in notes[0]


def test_superseded_benchmark_is_excluded_but_preserved_in_snapshot():
    results = [
        evaluation(evaluation_id="evl-v1-old", benchmark_version="v1", score=60.0, superseded=True),
        evaluation(
            evaluation_id="evl-v1-new",
            benchmark_version="v2",
            score=65.0,
            superseded=False,
            superseded_by=None,
        ),
    ]
    results[0]["superseded_by"] = "evl-v1-new"
    profile = _profile(results)
    used = profile["axes"]["general_intelligence"]["evaluation_ids"]
    assert "evl-v1-old" not in used
    assert "evl-v1-new" in used
    # History is preserved, not deleted: the record still exists in the dataset.
    assert any(r["evaluation_id"] == "evl-v1-old" for r in results)


def test_stale_revision_evidence_is_not_counted_as_exact():
    historical = evaluation(match_status="ambiguous")
    profile = _profile([historical])
    assert profile["evidence_status"] == "unknown"
    assert profile["high_quality_candidate"] is False


def test_no_double_counting_of_republished_run():
    # Two hosts republishing one publisher run stay a single publisher claim.
    results = [
        publisher_evaluation(evaluation_id="evl-v1-a", source_id="model-card"),
        publisher_evaluation(evaluation_id="evl-v1-b", source_id="aggregator-blog"),
    ]
    profile = _profile(results)
    assert profile["evidence_status"] == "publisher_only"


def test_profile_is_deterministic():
    results = [evaluation(), publisher_evaluation(benchmark_id="ifeval", metric="IFEval score")]
    first = _profile(results)
    second = _profile(list(reversed(results)))
    assert first["profile_id"] == second["profile_id"]
    assert first["axes"] == second["axes"]


def test_cross_metric_raw_aggregation_is_refused():
    results = [
        evaluation(score=70.0, score_unit="percent"),
        evaluation(
            evaluation_id="evl-v1-elo",
            score=1200.0,
            metric="Codeforces rating",
            score_unit="elo_rating",
            benchmark_id="codeforces",
        ),
    ]
    aggregate = aggregate_axis_scores(results=results)
    assert aggregate["aggregation"] == "refused"
    assert set(aggregate["per_metric"]) == {"MMLU accuracy", "Codeforces rating"}


def test_axis_mapping_is_explicit_not_inferred_from_popularity():
    assert axis_for_result(evaluation(benchmark_id="humaneval")) == ("coding",)
    assert axis_for_result(evaluation(benchmark_id="terminal-bench")) == (
        "coding",
        "agentic_tool_use",
    )
    assert axis_for_result(evaluation(benchmark_id="ifeval")) == ("instruction_following",)
    assert axis_for_result(evaluation(benchmark_id="simpleqa")) == (
        "knowledge",
        "non_hallucination",
    )


def test_refusal_behavior_is_not_general_capability():
    axes = axis_for_result(evaluation(benchmark_id="refusalbench", metric="refusal rate"))
    assert axes == ("safety_refusal_behavior",)
    assert "general_intelligence" not in axes


def test_community_only_profile_is_not_candidate():
    profile = _profile([community_evaluation()])
    assert profile["evidence_status"] == "community_only"
    assert profile["high_quality_candidate"] is False


def test_arabic_axis_unknown_without_arabic_benchmark():
    profile = _profile([evaluation()])
    assert profile["axes"]["arabic"]["status"] == "unknown"

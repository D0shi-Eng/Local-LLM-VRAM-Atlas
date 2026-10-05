"""Phase 6: benchmark identity, version handling and comparability rules."""

from __future__ import annotations

from phase6.support import (
    community_evaluation,
    evaluation,
    model_record,
    quant_record,
)

from atlas.quality.comparability import compare, is_comparable, rank_within_benchmark
from atlas.quality.identity import (
    is_base_vs_instruct_mismatch,
    is_base_vs_quant_mismatch,
    match_evaluation_identity,
)
from atlas.quality.ingest import normalize_evaluation
from atlas.quality.tiers import evidence_status_from_origins, stronger_tier


def test_same_benchmark_same_version_is_comparable():
    left = evaluation(evaluation_id="evl-v1-a")
    right = evaluation(evaluation_id="evl-v1-b", score=64.0, source_id="second-org")
    assert is_comparable(left, right) is True
    verdict = compare(left, right)
    assert verdict["comparable"] is True
    assert verdict["material_differences"] == []


def test_same_benchmark_different_version_is_not_comparable():
    left = evaluation(benchmark_version="v1")
    right = evaluation(benchmark_version="v2")
    verdict = compare(left, right)
    assert verdict["comparable"] is False
    assert "benchmark_version" in verdict["material_differences"]


def test_higher_is_better_ranks_descending():
    ranked = rank_within_benchmark(
        [
            evaluation(evaluation_id="evl-v1-low", score=50.0),
            evaluation(evaluation_id="evl-v1-high", score=90.0),
        ]
    )
    assert ranked["evl-v1-high"]["rank"] == 1
    assert ranked["evl-v1-low"]["rank"] == 2
    assert ranked["evl-v1-high"]["population_size"] == 2
    assert ranked["evl-v1-low"]["raw_score"] == 50.0


def test_lower_is_better_ranks_ascending():
    ranked = rank_within_benchmark(
        [
            evaluation(
                evaluation_id="evl-v1-a",
                metric="hallucination rate",
                metric_direction="lower_is_better",
                score=5.0,
            ),
            evaluation(
                evaluation_id="evl-v1-b",
                metric="hallucination rate",
                metric_direction="lower_is_better",
                score=2.0,
            ),
        ]
    )
    assert ranked["evl-v1-b"]["rank"] == 1
    assert ranked["evl-v1-a"]["rank"] == 2


def test_reasoning_mode_difference_blocks_comparison():
    verdict = compare(
        evaluation(reasoning_mode="thinking"), evaluation(reasoning_mode="non-reasoning")
    )
    assert verdict["comparable"] is False
    assert "reasoning_mode" in verdict["material_differences"]


def test_tool_mode_difference_blocks_comparison():
    verdict = compare(evaluation(tool_mode="tools"), evaluation(tool_mode="no_tools"))
    assert verdict["comparable"] is False
    assert "tool_mode" in verdict["material_differences"]


def test_elo_and_accuracy_are_not_merged_into_one_population():
    ranked = rank_within_benchmark(
        [
            evaluation(evaluation_id="evl-v1-elo", score=1200.0, score_unit="elo_rating"),
            evaluation(evaluation_id="evl-v1-acc", score=70.0, score_unit="percent"),
        ]
    )
    assert ranked == {}, "different metrics/units must not share a ranking population"


def test_publisher_and_independent_results_stay_distinct():
    status = evidence_status_from_origins(
        ["publisher", "independent"],
        verification_statuses=["publisher_claim", "independently_verified"],
        independent_sources=["independent-org"],
    )
    # One independent run alongside a publisher claim is still single-source.
    assert status == "independent_single_source"
    assert (
        evidence_status_from_origins(["publisher"], verification_statuses=["publisher_claim"])
        == "publisher_only"
    )


def test_two_publisher_republishers_are_not_independent_runs():
    status = evidence_status_from_origins(
        ["publisher", "publisher"], verification_statuses=["publisher_claim", "publisher_claim"]
    )
    assert status == "publisher_only"


def test_community_result_status_is_preserved():
    status = evidence_status_from_origins(["community"], verification_statuses=["unverified"])
    assert status == "community_only"
    assert community_evaluation()["evaluation_origin"] == "community"


def test_exact_model_identity_resolves():
    decision = match_evaluation_identity(
        record=model_record(),
        evaluated_repo_id="acme/Test-7B-Instruct",
        evaluated_revision="rev-base-1",
        record_revision="rev-base-1",
    )
    assert decision["match_status"] == "exact"
    assert decision["attach_as_exact"] is True


def test_ambiguous_identity_is_not_attached():
    decision = match_evaluation_identity(
        record=model_record(),
        evaluated_repo_id="someone-else/Test-7B-Instruct",
        evaluated_revision="rev-base-1",
    )
    assert decision["match_status"] == "ambiguous"
    assert decision["attach_as_exact"] is False


def test_unresolved_revision_is_not_assumed_equal():
    decision = match_evaluation_identity(
        record=model_record(),
        evaluated_repo_id="acme/Test-7B-Instruct",
        evaluated_revision=None,
        record_revision="rev-base-1",
    )
    assert decision["match_status"] == "exact_repo_revision_unresolved"
    assert decision["attach_as_exact"] is True


def test_revision_mismatch_is_not_exact():
    decision = match_evaluation_identity(
        record=model_record(),
        evaluated_repo_id="acme/Test-7B-Instruct",
        evaluated_revision="rev-old",
        record_revision="rev-base-1",
    )
    assert decision["match_status"] == "ambiguous"
    assert decision["attach_as_exact"] is False


def test_identity_conflict_is_excluded_from_ranking():
    decision = match_evaluation_identity(
        record=model_record(),
        evaluated_repo_id="acme/Test-7B-Instruct",
        evaluated_revision="rev-base-1",
        catalog_identity_conflict=True,
    )
    assert decision["match_status"] == "identity_conflict"


def test_base_vs_instruct_results_are_not_transferred():
    record = model_record(display_name="acme/Test-7B-Base")
    assert (
        is_base_vs_instruct_mismatch(record=record, evaluated_repo_id="acme/Test-7B-Instruct")
        is True
    )


def test_base_score_is_not_attached_to_quantized_artifact():
    assert (
        is_base_vs_quant_mismatch(
            record=quant_record(), evaluated_quantization=None, record_quantization="Q4_K_M"
        )
        is False
    )
    # A base run (no quant label) can never stand in for Q4_K_M evidence.
    record = quant_record(
        quantization={
            "format": "GGUF",
            "quant_family": "q4",
            "quant_name": "Q4_K_M",
            "source_revision": "rev-quant-1",
        }
    )
    normalized = normalize_evaluation(
        record=record,
        evaluated_repo_id="acme/Test-7B-Instruct-GGUF",
        evaluated_revision="rev-quant-1",
        benchmark_name="MMLU",
        benchmark_id="mmlu",
        metric="MMLU accuracy",
        metric_direction="higher_is_better",
        score=70.0,
        score_unit="percent",
        evaluation_origin="independent",
        verification_status="independently_verified",
        source_id="independent-org",
        source_url="https://example.org/results",
        quantization="Q4_K_M",
        evidence_ids=["ev-test-1"],
    )
    assert normalized is not None
    assert normalized["quantization"] == "Q4_K_M"


def test_quality_tier_order_is_strict():
    assert stronger_tier("q1_independent_standardized", "q4_publisher") is True
    assert stronger_tier("q4_publisher", "q1_independent_standardized") is False
    assert stronger_tier("unknown-tier", "q4_publisher") is False


def test_publisher_result_is_not_relabeled_independent_by_normalization():
    record = model_record()
    normalized = normalize_evaluation(
        record=record,
        evaluated_repo_id="acme/Test-7B-Instruct",
        evaluated_revision="rev-base-1",
        benchmark_name="MMLU",
        benchmark_id="mmlu",
        metric="MMLU accuracy",
        metric_direction="higher_is_better",
        score=70.0,
        score_unit="percent",
        evaluation_origin="publisher",
        verification_status="publisher_claim",
        source_id="acme-model-card",
        source_url="https://huggingface.co/acme/Test-7B-Instruct",
        evidence_ids=["ev-test-1"],
    )
    assert normalized["evaluation_origin"] == "publisher"
    assert normalized["verification_status"] == "publisher_claim"


def test_evaluation_without_evidence_ids_is_refused():
    normalized = normalize_evaluation(
        record=model_record(),
        evaluated_repo_id="acme/Test-7B-Instruct",
        evaluated_revision="rev-base-1",
        benchmark_name="MMLU",
        benchmark_id="mmlu",
        metric="MMLU accuracy",
        metric_direction="higher_is_better",
        score=70.0,
        score_unit="percent",
        evaluation_origin="independent",
        verification_status="independently_verified",
        source_id="independent-org",
        source_url="https://example.org/results",
        evidence_ids=[],
    )
    assert normalized is None, "no logical-only quality evidence is permitted"

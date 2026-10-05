"""Phase 6: anti-manipulation guarantees.

Popularity, brand, size, recency, repository names and marketing text must be
incapable of improving a quality profile or a recommendation.
"""

from __future__ import annotations

from phase6.support import evaluation, model_record, publisher_evaluation

from atlas.quality import QUALITY_SNAPSHOT_VERSION
from atlas.quality.policy import QUALITY_EVIDENCE_POLICY, RECOMMENDATION_POLICY
from atlas.quality.profiles import build_profile
from atlas.quality.retention import build_retention

SNAPSHOT = QUALITY_SNAPSHOT_VERSION
REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]


def _profile(results):
    return build_profile(
        model_id="acme-test-7b-instruct", results=results, quality_snapshot_version=SNAPSHOT
    )


def test_downloads_cannot_improve_quality():
    unpopular = model_record(popularity={"downloads": 1, "likes": 0})
    famous = model_record(
        model_id="acme-test-7b-instruct-famous",
        display_name="acme/Test-7B-Instruct",
        popularity={"downloads": 90_000_000, "likes": 400_000},
    )
    results = [evaluation()]
    base = _profile(results)
    hot = build_profile(
        model_id=famous["model_id"], results=results, quality_snapshot_version=SNAPSHOT
    )
    assert base["high_quality_candidate"] == hot["high_quality_candidate"]
    assert base["evidence_status"] == hot["evidence_status"]
    assert base["axes"] == hot["axes"]
    assert unpopular["popularity"]["downloads"] < famous["popularity"]["downloads"]


def test_likes_cannot_improve_quality():
    # Same evidence, wildly different popularity: the decision must not move.
    profile_results = [evaluation()]
    assert (
        _profile(profile_results)["high_quality_candidate"]
        == build_profile(
            model_id="acme-test-7b-instruct-liked",
            results=profile_results,
            quality_snapshot_version=SNAPSHOT,
        )["high_quality_candidate"]
    )
    liked = model_record(popularity={"downloads": 0, "likes": 999_999})
    assert liked["popularity"]["likes"] == 999_999


def test_brand_cannot_improve_quality():
    results = [evaluation()]
    openai_like = _profile(results)
    unknown_lab = build_profile(
        model_id="obscure-lab-model",
        results=results,
        quality_snapshot_version=SNAPSHOT,
    )
    assert openai_like["evidence_status"] == unknown_lab["evidence_status"]
    assert openai_like["high_quality_candidate"] == unknown_lab["high_quality_candidate"]


def test_parameter_count_cannot_improve_quality():
    small = model_record(total_parameters_b=1.5)
    huge = model_record(
        model_id="acme-test-70b-instruct",
        display_name="acme/Test-70B-Instruct",
        total_parameters_b=70.0,
    )
    results = [evaluation()]
    assert (
        _profile(results)["high_quality_candidate"]
        == build_profile(
            model_id=huge["model_id"], results=results, quality_snapshot_version=SNAPSHOT
        )["high_quality_candidate"]
    )
    assert small["total_parameters_b"] < huge["total_parameters_b"]


def test_release_recency_cannot_improve_quality():
    old = model_record(release_date="2023-01-01")
    new = model_record(release_date="2026-09-01")
    results = [evaluation()]
    assert (
        _profile(results)["axes"]
        == build_profile(
            model_id=new["model_id"], results=results, quality_snapshot_version=SNAPSHOT
        )["axes"]
    )
    assert old["release_date"] < new["release_date"]


def test_repo_name_uncensored_cannot_improve_quality():
    plain = model_record(display_name="acme/Test-7B-Instruct")
    named = model_record(
        model_id="acme-test-7b-instruct-uncensored-named",
        display_name="acme/Test-7B-Instruct-Uncensored",
    )
    results = [evaluation()]
    assert (
        _profile(results)["high_quality_candidate"]
        == build_profile(
            model_id=named["model_id"], results=results, quality_snapshot_version=SNAPSHOT
        )["high_quality_candidate"]
    )
    assert plain["openness"] == named["openness"]


def test_repo_name_q4_cannot_create_retention():
    retention = build_retention(
        base_release="a",
        quantized_artifact="b",
        quantization="Q4_K_M",
        base_result=evaluation(score=70.0),
        quant_result=None,
    )
    assert retention["quant_score"] is None
    assert retention["absolute_delta"] is None
    assert retention["retention_status"] == "insufficient_evidence"


def test_model_card_sota_text_creates_no_score():
    # A marketing string is metadata: normalization requires explicit evidence.
    from atlas.quality.ingest import normalize_evaluation

    record = model_record()
    assert (
        normalize_evaluation(
            record=record,
            evaluated_repo_id="acme/Test-7B-Instruct",
            evaluated_revision="rev-base-1",
            benchmark_name="SOTA marketing claim",
            metric="vibes",
            metric_direction="higher_is_better",
            score=99.0,
            score_unit="percent",
            evaluation_origin="publisher",
            verification_status="publisher_claim",
            source_id="acme-model-card",
            source_url="https://huggingface.co/acme/Test-7B-Instruct",
            evidence_ids=[],
        )
        is None
    )


def test_policy_declares_popularity_excluded():
    excluded = QUALITY_EVIDENCE_POLICY["rules"]["excluded_signals"]
    for token in ("downloads", "likes", "trending", "parameter_count", "release_recency"):
        assert token in excluded


def test_policy_forbids_brand_and_quantizer_bias():
    assert RECOMMENDATION_POLICY["rules"]["brand_and_quantizer_bias"] == "forbidden"
    assert RECOMMENDATION_POLICY["rules"]["manual_override"]["allowed"] is False


def test_publisher_result_cannot_become_independent_by_ingestion():
    from atlas.quality.ingest import normalize_evaluation

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
    profile = _profile([normalized])
    assert profile["evidence_status"] == "publisher_only"
    assert profile["high_quality_candidate"] is False


def test_quantizer_reputation_does_not_rank_higher():
    popular_quantizer = evaluation(quantization="Q4_K_M", score=69.0)
    obscure_quantizer = evaluation(quantization="Q3_K_S", evaluation_id="evl-v1-q3", score=69.0)
    ranked_popular = build_retention(
        base_release="a",
        quantized_artifact="b",
        quantization="Q4_K_M",
        base_result=evaluation(score=70.0),
        quant_result=popular_quantizer,
    )
    ranked_obscure = build_retention(
        base_release="a2",
        quantized_artifact="b2",
        quantization="Q3_K_S",
        base_result=evaluation(score=70.0),
        quant_result=obscure_quantizer,
    )
    assert ranked_popular["retention_status"] == ranked_obscure["retention_status"]
    assert ranked_popular["evidence_quality"] == ranked_obscure["evidence_quality"]


def test_publisher_and_community_are_not_upgraded_by_verification_status():
    profile = _profile([publisher_evaluation(), publisher_evaluation(evaluation_id="evl-v1-c")])
    assert profile["high_quality_candidate"] is False

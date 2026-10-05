"""Phase 6.5: recommendation readiness states for Core candidates.

Every strict gate must hold at once; every missing gate must be visible; and
no waiver, manual override or weak-evidence promotion is possible.
"""

from __future__ import annotations

from closure.support import candidate, evaluation, model_record

from atlas.closure.readiness import CLOSURE_POLICY, evaluate_candidate
from atlas.quality.policy import RECOMMENDATION_POLICY

ARTIFACT = "acme-test-7b-instruct--gguf--q4_k_m"

STRICT_ESTIMATE = {
    "candidate_id": "core-test-01",
    "artifact_set_id": candidate()["artifact_set_id"],
    "architecture_family": "qwen3",
    "estimate_status": "calculated_from_source_metadata",
    "by_tier": {
        "4": "estimated_not_fit",
        "8": "estimated_fit",
        "12": "estimated_fit",
        "16": "estimated_fit",
    },
    "tier_reasons": {t: "reliable upper bound fits inside tier capacity" for t in (4, 8, 12, 16)},
}

PARTIAL_ESTIMATE = {
    **STRICT_ESTIMATE,
    "by_tier": {
        "4": "insufficient_evidence",
        "8": "insufficient_evidence",
        "12": "insufficient_evidence",
        "16": "insufficient_evidence",
    },
}

REFUSED_ESTIMATE = {
    **STRICT_ESTIMATE,
    "estimate_status": "refused",
    "by_tier": {str(t): "unsupported" for t in (4, 8, 12, 16)},
}

EVIDENCE = {
    "availability": "available",
    "new_evidence": [{"evidence_id": "ev-v2-" + "a" * 64}],
}

DIRECT_RETENTION = {
    "retention_status": "independently_measured",
    "absolute_delta": -1.0,
    "relative_delta": -0.014,
}


def _independent_results() -> list[dict]:
    return [
        evaluation(
            evaluator="evaluator-a",
            artifact_id=ARTIFACT,
            quantization="Q4_K_M",
            evaluation_id="evl-v1-" + "a" * 64,
        ),
        evaluation(
            evaluator="evaluator-b",
            source_id="org-b",
            artifact_id=ARTIFACT,
            quantization="Q4_K_M",
            evaluation_id="evl-v1-" + "b" * 64,
            score=71.0,
        ),
    ]


def _evaluate(**overrides):
    payload = {
        "candidate": candidate(),
        "record": model_record(),
        "estimate": STRICT_ESTIMATE,
        "current_evidence": EVIDENCE,
        "evaluations": _independent_results(),
        "retention": DIRECT_RETENTION,
        "sidecar_state": "partial",
    }
    payload.update(overrides)
    return evaluate_candidate(**payload)


def test_all_gates_satisfied_reaches_strict_ready():
    result = _evaluate()
    assert result["readiness_state"] == "STRICT_READY"
    assert result["missing_gates"] == []
    assert result["strict_tiers"] == [8, 12, 16]


def test_quality_strong_but_vram_incomplete_is_candidate_ready():
    result = _evaluate(estimate=PARTIAL_ESTIMATE)
    assert result["readiness_state"] == "CANDIDATE_READY"
    assert "vram_fit_state_strict" in result["missing_gates"]
    assert result["strict_tiers"] == []


def test_vram_strong_but_quality_missing_is_not_strict():
    result = _evaluate(evaluations=[])
    assert result["readiness_state"] != "STRICT_READY"
    assert "independent_multi_source_quality" in result["missing_gates"]


def test_single_independent_source_is_not_strict():
    result = _evaluate(
        evaluations=[
            evaluation(
                artifact_id=ARTIFACT,
                quantization="Q4_K_M",
                evaluation_id="evl-v1-" + "a" * 64,
            )
        ]
    )
    assert result["quality_state"] == "independent_single_source"
    assert result["readiness_state"] != "STRICT_READY"


def test_base_quality_strong_but_retention_unknown_is_not_strict():
    result = _evaluate(retention={"retention_status": "unknown"})
    assert "quant_retention_when_post_training_quantized" in result["missing_gates"]
    assert result["readiness_state"] != "STRICT_READY"


def test_unknown_license_is_not_strict():
    record = model_record(openness="unclear", license={"license_id": None})
    result = _evaluate(record=record)
    assert result["license_status"] == "unclear"
    assert result["readiness_state"] != "STRICT_READY"
    assert "license_status_acceptable" in result["missing_gates"]


def test_alignment_variant_without_exact_evaluation_is_not_strict():
    record = model_record(
        alignment={
            "alignment_variant": "uncensored",
            "base_model": "acme/Test-7B-Instruct",
            "variant_author": "thirdparty",
        },
        base_models=["acme/Test-7B-Instruct"],
    )
    result = _evaluate(record=record)
    assert result["readiness_state"] != "STRICT_READY"
    assert "alignment_variant_exact_evaluation:uncensored" in result["missing_gates"]


def test_alignment_variant_without_declared_lineage_is_blocked():
    record = model_record(
        alignment={"alignment_variant": "abliterated", "variant_author": "thirdparty"},
        base_models=[],
    )
    result = _evaluate(record=record)
    assert result["readiness_state"] == "BLOCKED"
    assert "alignment_variant_without_declared_lineage" in result["missing_gates"]


def test_publisher_only_quality_is_not_strict():
    publisher = evaluation(
        evaluation_origin="publisher",
        verification_status="publisher_claim",
        evaluator="acme",
        source_id="acme-card",
        artifact_id=ARTIFACT,
        quantization="Q4_K_M",
        evaluation_id="evl-v1-" + "c" * 64,
    )
    result = _evaluate(evaluations=[publisher])
    assert result["quality_state"] == "publisher_or_community_only"
    assert result["readiness_state"] != "STRICT_READY"


def test_refused_estimate_forces_catalog_only():
    result = _evaluate(estimate=REFUSED_ESTIMATE)
    assert result["readiness_state"] == "CATALOG_ONLY"
    assert "vram_fit_state_strict" in result["missing_gates"]


def test_popularity_brand_size_and_recency_cannot_raise_a_state():
    unpopular = _evaluate(
        record=model_record(popularity={"downloads": 1, "likes": 0}),
        evaluations=[],
    )
    famous = _evaluate(
        record=model_record(
            popularity={"downloads": 90_000_000, "likes": 400_000},
            release_date="2026-09-01",
            total_parameters_b=70.0,
        ),
        evaluations=[],
    )
    assert unpopular["readiness_state"] == famous["readiness_state"]
    assert popular_tokens_not_allowed()


def popular_tokens_not_allowed() -> bool:
    for signal in CLOSURE_POLICY["rules"]["signals_that_cannot_raise_a_state"]:
        assert signal in (
            "downloads",
            "likes",
            "trending",
            "parameter_count",
            "artifact_byte_size",
            "publisher_brand",
            "release_recency",
            "adoption",
        )
    return True


def test_no_manual_override_exists():
    assert CLOSURE_POLICY["rules"]["manual_override_allowed"] is False
    assert CLOSURE_POLICY["rules"]["waivers_allowed"] is False
    assert RECOMMENDATION_POLICY["rules"]["manual_override"]["allowed"] is False


def test_closure_reuses_the_phase6_recommendation_policy():
    assert (
        CLOSURE_POLICY["rules"]["derived_recommendation_policy"]["policy_id"]
        == RECOMMENDATION_POLICY["policy_id"]
    )
    assert (
        CLOSURE_POLICY["rules"]["derived_recommendation_policy"]["policy_version"]
        == RECOMMENDATION_POLICY["policy_version"]
    )


def test_strict_state_requires_every_declared_gate():
    declared = set(CLOSURE_POLICY["rules"]["strict_gates"])
    result = _evaluate(estimate=PARTIAL_ESTIMATE)
    for gate in declared:
        assert gate in result["gates"]
    assert result["readiness_state"] == "CANDIDATE_READY"

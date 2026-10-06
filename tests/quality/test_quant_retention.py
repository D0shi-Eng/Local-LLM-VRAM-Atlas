"""Quantization retention integrity.

Base quality is never inherited by a quantized artifact; retention is only
computed when both sides come from a comparable setup.
"""

from __future__ import annotations

from builders.records import evaluation, publisher_evaluation, quant_record

from atlas.quality.retention import build_retention, parent_reference_only


def test_exact_base_and_quant_same_setup_compares():
    base = evaluation(score=70.0, quantization=None)
    quant = evaluation(score=68.0, quantization="Q4_K_M")
    retention = build_retention(
        base_release="acme-test-7b-instruct",
        quantized_artifact="acme-test-7b-instruct-q4-k-m",
        quantization="Q4_K_M",
        base_result=base,
        quant_result=quant,
        evidence_ids=["ev-test-1"],
    )
    assert retention["evaluation_settings_match"] is True
    assert retention["absolute_delta"] == -2.0
    assert retention["retention_status"] == "independently_measured"


def test_different_benchmark_version_is_rejected():
    base = evaluation(benchmark_version="v1")
    quant = evaluation(benchmark_version="v2", quantization="Q4_K_M")
    retention = build_retention(
        base_release="a",
        quantized_artifact="b",
        quantization="Q4_K_M",
        base_result=base,
        quant_result=quant,
    )
    assert retention["evaluation_settings_match"] is False
    assert retention["absolute_delta"] is None
    assert retention["relative_delta"] is None
    assert retention["retention_status"] == "partially_comparable"


def test_different_reasoning_mode_is_rejected():
    base = evaluation(reasoning_mode="thinking")
    quant = evaluation(reasoning_mode="non-reasoning", quantization="Q4_K_M")
    retention = build_retention(
        base_release="a",
        quantized_artifact="b",
        quantization="Q4_K_M",
        base_result=base,
        quant_result=quant,
    )
    assert retention["evaluation_settings_match"] is False
    assert retention["absolute_delta"] is None


def test_missing_base_score_keeps_retention_unknown():
    quant = evaluation(quantization="Q4_K_M")
    retention = build_retention(
        base_release="a",
        quantized_artifact="b",
        quantization="Q4_K_M",
        base_result=None,
        quant_result=quant,
    )
    assert retention["base_score"] is None
    assert retention["retention_status"] == "insufficient_evidence"
    assert retention["absolute_delta"] is None


def test_missing_quant_score_keeps_retention_unknown():
    base = evaluation()
    retention = build_retention(
        base_release="a",
        quantized_artifact="b",
        quantization="Q4_K_M",
        base_result=base,
        quant_result=None,
    )
    assert retention["quant_score"] is None
    assert retention["retention_status"] == "insufficient_evidence"


def test_no_evidence_at_all_is_unknown_not_zero():
    retention = build_retention(
        base_release="a",
        quantized_artifact="b",
        quantization="Q4_K_M",
        base_result=None,
        quant_result=None,
    )
    assert retention["retention_status"] == "unknown"
    assert retention["relative_delta"] is None


def test_publisher_retention_claim_stays_a_claim():
    retention = build_retention(
        base_release="a",
        quantized_artifact="b",
        quantization="Q4_K_M",
        base_result=publisher_evaluation(score=70.0),
        quant_result=publisher_evaluation(score=68.7, quantization="Q4_K_M"),
        publisher_claim={
            "claim_text": "retains 98% of original performance",
            "claim_source": "quantizer model card",
            "claim_date": "2025-02-01",
        },
        evidence_ids=["ev-test-1"],
    )
    assert retention["retention_status"] == "publisher_measured"
    assert retention["verification_status"] == "publisher_claim"
    assert retention["publisher_claim"]["claim_text"] == "retains 98% of original performance"
    assert retention["evidence_quality"] == "publisher_only"


def test_independent_retention_evidence_is_distinguished():
    base = evaluation(score=70.0)
    quant = evaluation(score=69.0, quantization="Q4_K_M")
    retention = build_retention(
        base_release="a",
        quantized_artifact="b",
        quantization="Q4_K_M",
        base_result=base,
        quant_result=quant,
        evidence_ids=["ev-test-1"],
    )
    assert retention["retention_status"] == "independently_measured"
    assert retention["evidence_quality"] == "independent_single_source"


def test_extreme_quant_has_unknown_retention_without_evidence():
    for quant_label in ("IQ1_S", "IQ2_XXS", "TQ1_0"):
        retention = build_retention(
            base_release="a",
            quantized_artifact="b",
            quantization=quant_label,
            base_result=None,
            quant_result=None,
        )
        assert retention["retention_status"] == "unknown"


def test_extreme_quant_does_not_inherit_base_score():
    retention = build_retention(
        base_release="a",
        quantized_artifact="b",
        quantization="IQ2_XXS",
        base_result=evaluation(score=70.0),
        quant_result=None,
    )
    context = parent_reference_only(base_result=evaluation(score=70.0), quant_result=None)
    assert retention["quant_score"] is None
    assert context["usable_as_quant_quality"] is False
    assert "retention unknown" in context["disclosure"]


def test_native_low_bit_exact_evaluation_is_its_own_evidence():
    native = evaluation(
        model_id="microsoft-bitnet-b1-58-2b-4t",
        quantization=None,
        score=61.0,
        benchmark_id="bitnet-native-benchmark",
    )
    retention = build_retention(
        base_release="microsoft-bitnet-b1-58-2b-4t",
        quantized_artifact="microsoft-bitnet-b1-58-2b-4t",
        quantization=None,
        base_result=native,
        quant_result=native,
        evidence_ids=["ev-test-1"],
    )
    # A native release evaluated in its native form is not a post-training
    # quantization comparison; it is represented as its own evidence.
    assert retention["evaluation_settings_match"] is True
    assert retention["absolute_delta"] == 0.0


def test_relative_delta_not_computed_for_lower_is_better():
    base = evaluation(metric="latency", metric_direction="lower_is_better", score=100.0)
    quant = evaluation(
        metric="latency", metric_direction="lower_is_better", score=110.0, quantization="Q4_K_M"
    )
    retention = build_retention(
        base_release="a",
        quantized_artifact="b",
        quantization="Q4_K_M",
        base_result=base,
        quant_result=quant,
    )
    assert retention["absolute_delta"] == 10.0
    assert retention["relative_delta"] is None


def test_quantized_record_context_is_reference_only():
    context = parent_reference_only(base_result=evaluation(score=70.0), quant_result=None)
    assert context["parent_score"] == 70.0
    assert context["usable_as_quant_quality"] is False
    record = quant_record()
    assert record["quantization"]["quant_name"] == "Q4_K_M"

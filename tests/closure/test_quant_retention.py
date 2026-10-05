"""Phase 6.5: quantization retention integrity.

Comparable base/quant pairs, harness and version and reasoning-mode
mismatches, a missing quantized result, publisher-claim-only evidence,
independent direct retention, extreme compression with no data, and native
low-bit releases that need no artificial base-vs-quant comparison.
"""

from __future__ import annotations

from closure.support import candidate, evaluation, model_record

from atlas.closure.retention_evidence import build_candidate_retention
from atlas.quality.retention import build_retention

QUANT_RESULT = "Q4_K_M"


def _retention(base: dict | None, quant: dict | None):
    return build_retention(
        base_release="acme-test-7b-instruct",
        quantized_artifact="acme-test-7b-instruct--gguf--q4_k_m",
        quantization=QUANT_RESULT,
        base_result=base,
        quant_result=quant,
    )


def test_comparable_base_and_quant_result_yields_retention():
    record = _retention(
        evaluation(score=70.0, evaluation_id="evl-v1-" + "1" * 64),
        evaluation(
            score=68.5,
            quantization=QUANT_RESULT,
            evaluation_id="evl-v1-" + "2" * 64,
            evidence_ids=["ev-current-1"],
        ),
    )
    assert record["evaluation_settings_match"] is True
    assert record["absolute_delta"] == -1.5
    assert record["relative_delta"] is not None
    assert record["retention_status"] == "independently_measured"


def test_different_harness_blocks_retention():
    from atlas.closure.retention_evidence import build_candidate_retention

    base = evaluation(suite_version="harness-1.2", evaluation_id="evl-v1-" + "1" * 64)
    quant = evaluation(
        suite_version="harness-2.0",
        quantization=QUANT_RESULT,
        evaluation_id="evl-v1-" + "2" * 64,
    )
    entry = build_candidate_retention(
        candidate=candidate(),
        record=model_record(),
        records={},
        evaluations_by_model={
            "acme-test-7b-instruct": [base, quant],
        },
        native_low_bit=False,
    )
    assert entry["retention_status"] == "partially_comparable"
    assert entry["absolute_delta"] is None
    assert "harness divergence" in (entry["notes"] or "")


def test_different_benchmark_version_blocks_retention():
    record = _retention(
        evaluation(benchmark_version="v1", evaluation_id="evl-v1-" + "1" * 64),
        evaluation(
            benchmark_version="v2",
            quantization=QUANT_RESULT,
            evaluation_id="evl-v1-" + "2" * 64,
        ),
    )
    assert record["evaluation_settings_match"] is False


def test_different_reasoning_mode_blocks_retention():
    record = _retention(
        evaluation(reasoning_mode="non-reasoning", evaluation_id="evl-v1-" + "1" * 64),
        evaluation(
            reasoning_mode="reasoning",
            quantization=QUANT_RESULT,
            evaluation_id="evl-v1-" + "2" * 64,
        ),
    )
    assert record["evaluation_settings_match"] is False


def test_missing_quant_result_keeps_retention_unknown():
    record = _retention(evaluation(score=70.0), None)
    assert record["quant_score"] is None
    assert record["absolute_delta"] is None
    assert record["retention_status"] == "insufficient_evidence"


def test_publisher_claim_only_is_not_independent_retention():
    record = _retention(
        evaluation(
            evaluation_origin="publisher",
            verification_status="publisher_claim",
            evaluator="acme",
            evaluation_id="evl-v1-" + "1" * 64,
        ),
        evaluation(
            evaluation_origin="publisher",
            verification_status="publisher_claim",
            evaluator="acme",
            quantization=QUANT_RESULT,
            evaluation_id="evl-v1-" + "2" * 64,
        ),
    )
    assert record["retention_status"] == "publisher_measured"
    assert record["evidence_quality"] == "publisher_only"


def test_independent_direct_retention_is_recorded():
    record = _retention(
        evaluation(evaluation_id="evl-v1-" + "1" * 64),
        evaluation(
            quantization=QUANT_RESULT,
            evaluator="evaluator-b",
            evaluation_id="evl-v1-" + "2" * 64,
        ),
    )
    assert record["retention_status"] == "independently_measured"
    assert record["absolute_delta"] == 0.0


def test_extreme_compression_with_no_data_never_gets_a_percentage():
    entry = build_candidate_retention(
        candidate=candidate(quantization_label="IQ2_XXS", artifact_variant="IQ2_XXS"),
        record=model_record(
            quantization={"format": "GGUF", "quant_family": "iq2", "quant_name": "IQ2_XXS"}
        ),
        records={},
        evaluations_by_model={"acme-test-7b-instruct": []},
        native_low_bit=False,
    )
    assert entry["retention_status"] == "unknown"
    assert entry["absolute_delta"] is None
    assert entry["relative_delta"] is None
    assert "no heuristic percentage" in entry["guessing_policy"]


def test_native_low_bit_needs_no_base_vs_quant_retention():
    entry = build_candidate_retention(
        candidate=candidate(
            candidate_id="core-native",
            artifact_variant="MXFP_4",
            quantization_label="MXFP_4",
        ),
        record=model_record(architecture="GptOssForCausalLM"),
        records={},
        evaluations_by_model={"acme-test-7b-instruct": []},
        native_low_bit=True,
    )
    assert entry["post_training_quantized"] is False
    assert entry["retention_status"] == "unknown"
    assert entry["absolute_delta"] is None


def test_native_precision_needs_no_retention_record():
    entry = build_candidate_retention(
        candidate=candidate(
            candidate_id="core-native-precision",
            artifact_variant=None,
            quantization_label="bf16",
        ),
        record=model_record(quantization={"format": "safetensors", "quant_family": "unknown"}),
        records={},
        evaluations_by_model={"acme-test-7b-instruct": []},
        native_low_bit=False,
    )
    assert entry["post_training_quantized"] is False
    assert entry["absolute_delta"] is None

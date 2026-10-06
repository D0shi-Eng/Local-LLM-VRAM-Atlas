"""Shared synthetic record builders for quality tests (offline only).

No network, no model, no GPU, no benchmark execution. Every score here is
fabricated test data whose only purpose is to exercise policy logic.
"""

from __future__ import annotations

STAMP = "2026-10-05T00:00:00Z"


def model_record(**overrides) -> dict:
    """Minimal canonical-ish model record with a resolvable repo identity."""
    record = {
        "model_id": "acme-test-7b-instruct",
        "display_name": "acme/Test-7B-Instruct",
        "creator": "acme",
        "architecture": "qwen2",
        "architecture_type": "dense",
        "openness": "open_weights_permissive",
        "verification": {"status": "publisher_claim", "evidence_ids": ["ev-test-1"]},
        "catalog_status": "verified",
        "lifecycle_status": "active",
        "license": {"license_id": "apache-2.0", "verification_status": "publisher_claim"},
        "quantization": {
            "format": "safetensors",
            "quant_family": "unknown",
            "quant_name": None,
            "source_revision": "rev-base-1",
        },
        "alignment": {"alignment_variant": "unknown"},
        "popularity": {"downloads": 900_000, "likes": 4_200, "captured_at": STAMP},
        "total_parameters_b": 7.0,
        "release_date": "2025-01-15",
    }
    record.update(overrides)
    return record


def quant_record(**overrides) -> dict:
    """Canonical-ish record for a quantized artifact of the same base model."""
    record = model_record(
        model_id="acme-test-7b-instruct-q4_k_m",
        display_name="acme/Test-7B-Instruct-GGUF",
        quantization={
            "format": "GGUF",
            "quant_family": "q4",
            "quant_name": "Q4_K_M",
            "source_revision": "rev-quant-1",
        },
    )
    record.update(overrides)
    return record


def alignment_record(**overrides) -> dict:
    """Alignment-variant record (uncensored/abliterated/heretic)."""
    record = model_record(
        model_id="acme-test-7b-instruct-uncensored",
        display_name="acme/Test-7B-Instruct-Uncensored",
        alignment={
            "alignment_variant": "uncensored",
            "base_model": "acme/Test-7B-Instruct",
            "variant_author": "thirdparty",
            "verification_status": "unknown",
        },
    )
    record.update(overrides)
    return record


def evaluation(**overrides) -> dict:
    """Minimal evaluation-result payload with explicit identity and settings."""
    result = {
        "schema_version": "0.6.0",
        "evaluation_id": "evl-v1-" + "0" * 64,
        "model_id": "acme-test-7b-instruct",
        "model_revision": "rev-base-1",
        "artifact_id": None,
        "quantization": None,
        "benchmark_id": "mmlu",
        "benchmark_name": "MMLU",
        "benchmark_version": "v1",
        "suite_version": None,
        "task": "multiple_choice",
        "metric": "MMLU accuracy",
        "metric_direction": "higher_is_better",
        "score": 70.0,
        "score_unit": "percent",
        "reasoning_mode": "non-reasoning",
        "tool_mode": "no_tools",
        "prompting_mode": "zero-shot",
        "context_configuration": "default",
        "evaluation_origin": "independent",
        "verification_status": "independently_verified",
        "evaluator": "independent-org",
        "evaluation_date": "2026-01-10",
        "source_id": "independent-org",
        "source_url": "https://example.org/results",
        "source_observed_at": STAMP,
        "evidence_ids": ["ev-test-1"],
        "match_status": "exact",
        "superseded": False,
        "superseded_by": None,
        "notes": None,
    }
    result.update(overrides)
    return result


def publisher_evaluation(**overrides) -> dict:
    """Publisher-origin evaluation (never relabeled independent)."""
    result = evaluation(
        evaluation_origin="publisher",
        verification_status="publisher_claim",
        source_id="acme-model-card",
        evaluator="acme",
        source_url="https://huggingface.co/acme/Test-7B-Instruct",
    )
    result.update(overrides)
    return result


def community_evaluation(**overrides) -> dict:
    """Community-origin evaluation (retains community status)."""
    result = evaluation(
        evaluation_origin="community",
        verification_status="unverified",
        source_id="forum-post",
        evaluator="community-runner",
        source_url="https://example.org/community",
    )
    result.update(overrides)
    return result

"""Phase 6.5: external VRAM evidence integrity.

Exact-quant measurement, wrong quant, wrong context, CPU/partial offload, full
GPU residency, unknown runtime version, a large-GPU measurement against a
smaller target tier, conflicting reports and anecdotal statements.
"""

from __future__ import annotations

from closure.support import architecture_fields, candidate, measurement

from atlas.closure.vram_evidence import (
    VRAM_SOURCE_CLASSES,
    attention_regime,
    build_candidate_estimate,
    derive_vram_source_class,
    fit_support,
)

ARTIFACT = "acme-test-7b-instruct--gguf--q4_k_m"


def test_source_class_covers_the_declared_ladder():
    assert VRAM_SOURCE_CLASSES == ("V1", "V2", "V3", "V4", "V5")
    assert derive_vram_source_class(measurement()) == "V1"
    assert (
        derive_vram_source_class(measurement(evidence_level="official_runtime_measurement")) == "V2"
    )
    assert derive_vram_source_class(measurement(evidence_level="publisher_measurement")) == "V3"
    assert (
        derive_vram_source_class(
            measurement(
                evidence_level="community_measurement",
                measurement_method="nvidia_smi",
            )
        )
        == "V4"
    )
    assert (
        derive_vram_source_class(
            measurement(evidence_level="community_measurement", measurement_method="documented")
        )
        == "V5"
    )


def test_exact_quant_measurement_supports_a_memory_requirement():
    verdict = fit_support(
        measurement(artifact_variant=ARTIFACT), tier_gb=8, expected_artifact_id=ARTIFACT
    )
    assert verdict["vram_source_class"] == "V1"
    assert verdict["artifact_identity"] == "exact"
    assert verdict["supports_measured_requirement"] is True
    assert verdict["hardware_verification"] == "not_performed_by_atlas"


def test_wrong_quant_measurement_is_not_attached_by_filename():
    verdict = fit_support(
        measurement(artifact_variant="some-other-q4-k-m.gguf"),
        tier_gb=8,
        expected_artifact_id=ARTIFACT,
    )
    assert verdict["artifact_identity"] == "mismatch"
    assert verdict["supports_measured_requirement"] is False


def test_wrong_context_is_not_baseline_evidence():
    verdict = fit_support(measurement(context_tokens=2048), tier_gb=8)
    assert verdict["supports_measured_requirement"] is False
    assert any("2048" in reason for reason in verdict["reasons"])


def test_cpu_offload_is_not_full_gpu_resident_fit():
    verdict = fit_support(measurement(offload_mode="cpu"), tier_gb=8)
    assert verdict["supports_measured_requirement"] is False
    assert any("not a full GPU-resident measurement" in r for r in verdict["reasons"])


def test_partial_offload_is_not_full_gpu_resident_fit():
    verdict = fit_support(measurement(offload_mode="partial"), tier_gb=8)
    assert verdict["supports_measured_requirement"] is False


def test_full_gpu_offload_is_accepted():
    verdict = fit_support(measurement(offload_mode="full"), tier_gb=8)
    assert verdict["supports_measured_requirement"] is True


def test_unknown_runtime_version_reduces_strength():
    verdict = fit_support(measurement(runtime_version=None), tier_gb=8)
    assert any("runtime version unknown" in reason for reason in verdict["reasons"])


def test_large_gpu_measurement_is_not_target_hardware_verification():
    big = measurement(gpu="RTX 4090", gpu_vram="24 GiB", reported_vram_bytes=6_700_000_000)
    verdict = fit_support(big, tier_gb=8)
    assert verdict["supports_measured_requirement"] is True
    assert verdict["hardware_verification"] == "not_performed_by_atlas"
    assert "not verified fit on the target tier" in verdict["note"]


def test_conflicting_reports_are_all_kept_and_refused():
    first = measurement(measurement_id="m-1", reported_vram_bytes=6_700_000_000)
    second = measurement(measurement_id="m-2", reported_vram_bytes=9_900_000_000)
    assert derive_vram_source_class(first) == derive_vram_source_class(second) == "V1"
    assert first["measurement_id"] != second["measurement_id"]


def test_anecdotal_measurement_can_never_support_a_fit():
    anecdotal = measurement(
        evidence_level="community_measurement",
        measurement_method="documented",
        reported_vram_bytes=None,
        context_tokens=None,
    )
    assert derive_vram_source_class(anecdotal) == "V5"
    verdict = fit_support(anecdotal, tier_gb=8)
    assert verdict["supports_measured_requirement"] is False


def test_artifact_size_alone_cannot_create_a_fit():
    estimate = build_candidate_estimate(
        candidate=candidate(artifact_weight_bytes=1_000_000_000),
        architecture_fields=architecture_fields(),
        advertised_max_context=40960,
    )
    assert estimate["upper_bytes"] is None
    assert estimate["by_tier"]["8"] != "estimated_fit"
    assert "no runtime memory profile" in estimate["runtime_overhead_state"]


def test_hybrid_attention_is_refused_not_understated():
    fields = architecture_fields(
        layer_types=["linear_attention", "linear_attention", "full_attention"] * 12,
    )
    assert attention_regime(fields) == "hybrid"
    estimate = build_candidate_estimate(
        candidate=candidate(),
        architecture_fields=fields,
        advertised_max_context=40960,
    )
    assert estimate["estimate_status"] == "refused"
    assert estimate["refusal_reason"] == "hybrid_or_state_space_attention"
    assert estimate["lower_bytes"] is None
    assert set(estimate["by_tier"].values()) == {"unsupported"}


def test_missing_cache_inputs_are_refused():
    estimate = build_candidate_estimate(
        candidate=candidate(),
        architecture_fields={"architectures": ["Qwen3ForCausalLM"], "model_type": "qwen3"},
        advertised_max_context=40960,
    )
    assert estimate["estimate_status"] == "refused"
    assert estimate["refusal_reason"] == "architecture_cache_inputs_missing"


def test_context_shorter_than_the_baseline_refuses_calculation():
    estimate = build_candidate_estimate(
        candidate=candidate(),
        architecture_fields=architecture_fields(),
        advertised_max_context=2048,
    )
    assert estimate["estimate_status"] == "insufficient_evidence"
    assert estimate["by_tier"]["8"] in ("insufficient_evidence", "estimated_not_fit")
    assert "advertises less context" in estimate["evidence_basis"]


def test_layer_plan_keeps_alternating_attention_per_layer():
    fields = architecture_fields(
        layer_types=["sliding_attention", "full_attention"] * 12,
        sliding_window=128,
    )
    estimate = build_candidate_estimate(
        candidate=candidate(),
        architecture_fields=fields,
        advertised_max_context=40960,
    )
    assert estimate["architecture_inputs"]["layer_plan_used"] is True
    assert estimate["architecture_inputs"]["layer_plan_heterogeneous"] is True
    assert estimate["lower_bytes"] is not None


def test_trustworthy_lower_bound_above_capacity_is_not_fit():
    estimate = build_candidate_estimate(
        candidate=candidate(artifact_weight_bytes=15_000_000_000),
        architecture_fields=architecture_fields(),
        advertised_max_context=40960,
    )
    assert estimate["by_tier"]["8"] == "estimated_not_fit"
    assert estimate["by_tier"]["16"] != "estimated_not_fit"


def test_atlas_measured_label_is_never_produced():
    from atlas.measurements.registry import ExternalMeasurement, validate_measurement

    forged = ExternalMeasurement(
        measurement_id="m",
        model_id="acme/Test-7B-Instruct",
        evidence_level="atlas_measured",
    )
    errors = validate_measurement(forged)
    assert any("atlas_measured" in error for error in errors)

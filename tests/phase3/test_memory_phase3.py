"""Phase 3: static memory — layered sums, GQA/MQA, MoE, refusals, tiers."""

import pytest

from atlas.archinfo.layer_plan import LayerPlan, LayerPlanEntry
from atlas.memory.calc_profile import ATLAS_TEXT_8K_BASELINE_V1, CalculationProfile
from atlas.memory.estimator import EstimateInputs, estimate_peak_vram
from atlas.memory.kv_cache import (
    InsufficientCacheEvidenceError,
    UnsupportedArchitectureError,
    estimate_kv_cache_bytes,
    estimate_kv_cache_layer_plan,
)
from atlas.vram.classifier import classify_all_tiers, classify_tier
from atlas.vram.tiers import tier_capacity_bytes


def _inputs(**overrides):
    params = {
        "architecture_family": "llama",
        "total_parameters": 8_000_000_000,
        "effective_bits_per_weight": 4.0,
        "num_layers": 32,
        "num_kv_heads": 8,
        "head_dim": 128,
        "kv_bytes_per_element": 2.0,
    }
    params.update(overrides)
    return EstimateInputs(**params)


def test_weights_do_not_scale_with_context():
    small_profile = CalculationProfile(
        profile_id="test-1k",
        profile_version="1",
        context_tokens=1024,
        sequence_count=1,
        kv_dtype="fp16",
    )
    large_profile = CalculationProfile(
        profile_id="test-2k",
        profile_version="1",
        context_tokens=2048,
        sequence_count=1,
        kv_dtype="fp16",
    )
    small = estimate_peak_vram(_inputs(), small_profile, None)
    large = estimate_peak_vram(_inputs(), large_profile, None)
    assert small.components.device_weight_bytes == large.components.device_weight_bytes
    assert large.components.kv_or_state_cache_bytes == 2 * small.components.kv_or_state_cache_bytes


def test_standard_kv_scales_with_context():
    base = estimate_kv_cache_bytes(
        architecture_family="llama",
        num_layers=4,
        num_kv_heads=8,
        head_dim=128,
        context_tokens=1024,
        bytes_per_element=2.0,
    )
    doubled = estimate_kv_cache_bytes(
        architecture_family="llama",
        num_layers=4,
        num_kv_heads=8,
        head_dim=128,
        context_tokens=2048,
        bytes_per_element=2.0,
    )
    assert doubled == 2 * base


def test_gqa_uses_kv_heads():
    full = estimate_kv_cache_bytes(
        architecture_family="llama",
        num_layers=2,
        num_kv_heads=8,
        head_dim=64,
        context_tokens=512,
        bytes_per_element=2.0,
        num_attention_heads=32,
    )
    quarter = estimate_kv_cache_bytes(
        architecture_family="llama",
        num_layers=2,
        num_kv_heads=2,
        head_dim=64,
        context_tokens=512,
        bytes_per_element=2.0,
        num_attention_heads=32,
    )
    assert full == 4 * quarter


def test_mqa_single_kv_head_cache():
    value = estimate_kv_cache_bytes(
        architecture_family="llama",
        num_layers=2,
        num_kv_heads=1,
        head_dim=64,
        context_tokens=512,
        bytes_per_element=2.0,
        num_attention_heads=32,
    )
    # 2 * 1 seq * 512 tok * 2 layers * 1 kv-head * 64 dim * 2 bytes.
    assert value == 2 * 512 * 2 * 1 * 64 * 2


def test_heterogeneous_layers_sum_independently():
    plan = LayerPlan(
        entries=(
            LayerPlanEntry(
                layer_index=0,
                layer_type="attention",
                attention_present=True,
                num_key_value_heads=8,
                head_dim=128,
            ),
            LayerPlanEntry(
                layer_index=1,
                layer_type="attention",
                attention_present=False,
            ),
            LayerPlanEntry(
                layer_index=2,
                layer_type="attention_sliding",
                attention_present=True,
                num_key_value_heads=4,
                head_dim=128,
                sliding_window=256,
            ),
        ),
        layer_count=3,
        heterogeneous=True,
        source="config_metadata",
        evidence_class="calculated_from_source_metadata",
    )
    total = estimate_kv_cache_layer_plan(
        plan,
        architecture_family="llama",
        context_tokens=1024,
        bytes_per_element=2.0,
    )
    # Layer 0: 2*1024*8*128*2 ; layer 1: 0 ; layer 2: 2*256*4*128*2.
    assert total == 2 * 1024 * 8 * 128 * 2 + 2 * 256 * 4 * 128 * 2
    estimate = estimate_peak_vram(_inputs(), ATLAS_TEXT_8K_BASELINE_V1, None, layer_plan=plan)
    assert "standard-kv-layer-plan-v1" in estimate.formula_refs


def test_unknown_field_never_zero():
    with pytest.raises(InsufficientCacheEvidenceError):
        estimate_kv_cache_bytes(
            architecture_family="llama",
            num_layers=4,
            num_kv_heads=None,
            head_dim=128,
            context_tokens=1024,
            bytes_per_element=2.0,
        )


def test_moe_active_params_not_residency():
    from atlas.memory.weights import MoEActiveParameterMisuseError

    # Direct weight math refuses active-parameter substitution explicitly.
    with pytest.raises(MoEActiveParameterMisuseError):
        from atlas.memory.weights import estimate_resident_weight_bytes

        estimate_resident_weight_bytes(
            total_parameters=None,
            bits_per_weight=4.0,
            architecture_type="moe",
            active_parameters=3_000_000_000,
            total_known=False,
        )
    # The estimator converts the refusal into an honest insufficient verdict.
    estimate = estimate_peak_vram(
        EstimateInputs(
            architecture_family="moe",
            total_parameters=None,
            active_parameters=3_000_000_000,
            total_known=False,
            effective_bits_per_weight=4.0,
            num_layers=32,
            num_kv_heads=8,
            head_dim=128,
            kv_bytes_per_element=2.0,
        ),
        ATLAS_TEXT_8K_BASELINE_V1,
        None,
    )
    assert estimate.estimate_status == "insufficient_evidence"


def test_unsupported_architectures_refuse():
    for family in ("mla", "mamba_ssm", "hybrid"):
        with pytest.raises(UnsupportedArchitectureError):
            estimate_kv_cache_bytes(
                architecture_family=family,
                num_layers=4,
                num_kv_heads=8,
                head_dim=128,
                context_tokens=1024,
                bytes_per_element=2.0,
            )
        estimate = estimate_peak_vram(
            _inputs(architecture_family=family), ATLAS_TEXT_8K_BASELINE_V1, None
        )
        assert estimate.estimate_status == "unsupported_architecture_for_estimation"


def test_lower_bound_only_blocks_fit_claim():
    # Lower bound below the tier but no reliable upper bound: no fit verdict.
    decision = classify_tier(6_000_000_000, None, tier_capacity_bytes(8), 8)
    assert decision.classification == "insufficient_evidence"
    # Lower bound above the tier: not-fit is provable from the lower bound alone.
    exceeded = classify_tier(20_000_000_000, None, tier_capacity_bytes(16), 16)
    assert exceeded.classification == "estimated_not_fit"


def test_context_constraint_refuses_raised_context():
    estimate = estimate_peak_vram(
        _inputs(advertised_max_context=4096),
        ATLAS_TEXT_8K_BASELINE_V1,
        None,
    )
    assert estimate.estimate_status == "insufficient_evidence"
    assert "advertis" in estimate.evidence_basis


def test_formula_version_present():
    estimate = estimate_peak_vram(_inputs(), ATLAS_TEXT_8K_BASELINE_V1, None)
    assert "standard-kv-v1" in estimate.formula_refs
    assert estimate.calculation_profile_id == "atlas-text-8k-baseline-v1"
    assert estimate.estimated_vram_lower_bytes is not None
    assert estimate.estimated_vram_upper_bytes is None


def test_all_tiers_conservative_without_upper():
    result = classify_all_tiers(lower_bound_bytes=6_000_000_000, upper_bound_bytes=None)
    assert all(
        d.classification in ("insufficient_evidence", "estimated_not_fit") for d in result.decisions
    )
    assert not any(d.classification == "estimated_fit" for d in result.decisions)

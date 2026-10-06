"""اختبارات KV/state cache: القياسي وGQA والتوسع والرفض."""

import pytest

from atlas.memory.calc_profile import ATLAS_TEXT_8K_BASELINE_V1
from atlas.memory.estimator import EstimateInputs, estimate_peak_vram
from atlas.memory.kv_cache import (
    InsufficientCacheEvidenceError,
    UnsupportedArchitectureError,
    estimate_kv_cache_bytes,
)


def _standard_kwargs(**overrides):
    """Transformer مصطنع: نتائج محسوبة يدويًا للتحقق."""
    params = {
        "architecture_family": "standard_transformer",
        "num_layers": 32,
        "num_kv_heads": 8,
        "head_dim": 128,
        "context_tokens": 8192,
        "bytes_per_element": 2.0,
        "sequence_count": 1,
    }
    params.update(overrides)
    return params


def test_standard_kv_hand_calculated():
    """المعادلة اليدوية: 2×1×8192×32×8×128×2 = 1073741824."""
    assert estimate_kv_cache_bytes(**_standard_kwargs()) == 1073741824


def test_gqa_uses_kv_heads_not_attention_heads():
    """GQA يستخدم num_key_value_heads لا num_attention_heads."""
    small = estimate_kv_cache_bytes(
        **_standard_kwargs(architecture_family="transformer_gqa", num_kv_heads=4)
    )
    large = estimate_kv_cache_bytes(
        **_standard_kwargs(architecture_family="transformer_gqa", num_kv_heads=32)
    )
    assert large == 8 * small


def test_context_scaling_doubles_kv():
    """مضاعفة السياق تضاعف مكون KV (الأوزان لا تتضاعف)."""
    base = estimate_kv_cache_bytes(**_standard_kwargs())
    doubled = estimate_kv_cache_bytes(**_standard_kwargs(context_tokens=16384))
    assert doubled == 2 * base


def test_quantized_kv_uses_block_overhead():
    """KV المكمم يحمل عامل الكتلة لا التعبئة المثالية وحدها."""
    ideal = estimate_kv_cache_bytes(
        **_standard_kwargs(bytes_per_element=1.0, kv_block_size=64, kv_scale_bytes_per_block=2)
    )
    assert ideal is not None and ideal > 0
    # bytes_per_element=1.0 مع كتلة 64 ومقياس 2 بايت يختلف عن التعبئة المثالية.
    naive = 2 * 1 * 8192 * 32 * 8 * 128 * 1.0
    assert ideal != int(naive)


def test_unknown_kv_heads_refuses():
    """حذف kv heads يجعل النتيجة insufficient_evidence لا صفرًا."""
    estimate = estimate_peak_vram(
        EstimateInputs(
            architecture_family="standard_transformer",
            weight_bytes_verified=4_000_000_000,
            num_layers=32,
            num_kv_heads=None,
            head_dim=128,
            kv_bytes_per_element=2.0,
        ),
        ATLAS_TEXT_8K_BASELINE_V1,
        None,
    )
    assert estimate.estimate_status == "insufficient_evidence"
    assert estimate.components.kv_or_state_cache_bytes is None


def test_mla_is_unsupported():
    """MLA لا تحصل على تقدير مزيف."""
    with pytest.raises(UnsupportedArchitectureError):
        estimate_kv_cache_bytes(**_standard_kwargs(architecture_family="mla"))


def test_mamba_is_unsupported():
    """Mamba/SSM ترفض صيغة KV التقليدية."""
    with pytest.raises(UnsupportedArchitectureError):
        estimate_kv_cache_bytes(**_standard_kwargs(architecture_family="mamba_ssm"))


def test_hybrid_is_unsupported():
    """الهجين لا يُختزل لأقرب Transformer."""
    with pytest.raises(UnsupportedArchitectureError):
        estimate_kv_cache_bytes(**_standard_kwargs(architecture_family="hybrid"))
    estimate = estimate_peak_vram(
        EstimateInputs(
            architecture_family="hybrid",
            weight_bytes_verified=4_000_000_000,
            num_layers=32,
            num_kv_heads=8,
            head_dim=128,
            kv_bytes_per_element=2.0,
        ),
        ATLAS_TEXT_8K_BASELINE_V1,
        None,
    )
    assert estimate.estimate_status == "unsupported_architecture_for_estimation"


def test_missing_kv_field_raises_insufficient():
    """الحقل الحرج الغائب يُرفع كأدلة ناقصة."""
    with pytest.raises(InsufficientCacheEvidenceError):
        estimate_kv_cache_bytes(**_standard_kwargs(num_kv_heads=None))

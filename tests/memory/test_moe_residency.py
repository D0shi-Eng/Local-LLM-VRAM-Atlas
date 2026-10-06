"""اختبارات إقامة MoE: النشط للحوسبة لا للإقامة."""

import pytest

from atlas.memory.calc_profile import ATLAS_TEXT_8K_BASELINE_V1
from atlas.memory.estimator import EstimateInputs, estimate_peak_vram
from atlas.memory.weights import (
    InsufficientWeightEvidenceError,
    MoEActiveParameterMisuseError,
    estimate_resident_weight_bytes,
)


def test_active_params_never_used_for_residency():
    """تمرير النشط دون الكلي في MoE يُرفض صراحة لا يُحسب به."""
    with pytest.raises(MoEActiveParameterMisuseError):
        estimate_resident_weight_bytes(
            total_parameters=None,
            bits_per_weight=4.5,
            architecture_type="moe",
            active_parameters=3_000_000_000,
            total_known=False,
        )


def test_resident_params_use_total():
    """الإقامة تستخدم العدد الكلي الكامل لخبراء MoE."""
    assert (
        estimate_resident_weight_bytes(
            total_parameters=20_000_000_000,
            bits_per_weight=4.0,
            architecture_type="moe",
            active_parameters=3_000_000_000,
            total_known=True,
        )
        == 10_000_000_000
    )


def test_missing_weight_evidence_refuses():
    """غياب عدد المقيمين يعني رفضًا لا صفرًا."""
    with pytest.raises(InsufficientWeightEvidenceError):
        estimate_resident_weight_bytes(
            total_parameters=None, bits_per_weight=4.0, architecture_type="dense"
        )


def test_moe_estimator_does_not_shrink_with_active():
    """المقدر يرفض الحساب دون مقيمين حتى مع وجود active_params."""
    estimate = estimate_peak_vram(
        EstimateInputs(
            architecture_family="moe",
            active_parameters=3_000_000_000,
            total_known=False,
            num_layers=24,
            num_kv_heads=8,
            head_dim=128,
            kv_bytes_per_element=2.0,
        ),
        ATLAS_TEXT_8K_BASELINE_V1,
        None,
    )
    assert estimate.estimate_status == "insufficient_evidence"
    assert estimate.components.device_weight_bytes is None

"""حساب البت الفعال لكل وزن من artifact حقيقي مع حراسة المدخلات."""

from __future__ import annotations


def effective_bits_per_weight(
    weight_storage_bytes: int | None,
    weight_parameter_count: int | float | None,
) -> float | None:
    """حساب bpw الفعال: (بايت التخزين × 8) / عدد معاملات الوزن.

    تعيد None بدل الرقم الكاذب عندما تكون المدخلات ناقصة أو مضللة.
    """
    if (
        weight_storage_bytes is None
        or weight_parameter_count is None
        or isinstance(weight_storage_bytes, bool)
        or isinstance(weight_parameter_count, bool)
        or not isinstance(weight_storage_bytes, int)
        or not isinstance(weight_parameter_count, (int, float))
        or weight_storage_bytes <= 0
        or weight_parameter_count <= 0
    ):
        return None
    return (float(weight_storage_bytes) * 8.0) / float(weight_parameter_count)


def weight_bytes_from_bpw(
    weight_parameter_count: int | float | None,
    bits_per_weight: float | None,
) -> int | None:
    """تقدير بايت الأوزان من عدد المعاملات وbpw موثق فقط."""
    if (
        weight_parameter_count is None
        or bits_per_weight is None
        or isinstance(weight_parameter_count, bool)
        or isinstance(bits_per_weight, bool)
        or not isinstance(weight_parameter_count, (int, float))
        or not isinstance(bits_per_weight, (int, float))
        or weight_parameter_count <= 0
        or bits_per_weight <= 0
    ):
        return None
    return int(round(float(weight_parameter_count) * float(bits_per_weight) / 8.0))

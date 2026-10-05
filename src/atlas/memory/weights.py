"""إقامة الأوزان: المعاملات المقيمة الكلية لا النشطة في MoE."""

from __future__ import annotations


class MoEActiveParameterMisuseError(ValueError):
    """رفع صريح عند تمرير معاملات MoE النشطة كمقيمة في الذاكرة."""


class InsufficientWeightEvidenceError(ValueError):
    """رفع صريح عند غياب دليل الوزن بدل التخمين من الاسم."""


def estimate_resident_weight_bytes(
    *,
    total_parameters: int | float | None,
    bits_per_weight: float | None,
    architecture_type: str | None = None,
    active_parameters: int | float | None = None,
    total_known: bool = True,
) -> int:
    """تقدير بايت الأوزان المقيمة على الجهاز من العدد الكلي وbpw موثق."""
    arch = (architecture_type or "dense").lower()
    if arch == "moe" and active_parameters is not None and not total_known:
        raise MoEActiveParameterMisuseError("active parameters never measure MoE resident weights")
    if (
        total_parameters is None
        or isinstance(total_parameters, bool)
        or not isinstance(total_parameters, (int, float))
        or total_parameters <= 0
    ):
        raise InsufficientWeightEvidenceError(
            f"missing resident parameter count: {total_parameters!r}"
        )
    if (
        bits_per_weight is None
        or isinstance(bits_per_weight, bool)
        or not isinstance(bits_per_weight, (int, float))
        or bits_per_weight <= 0
    ):
        raise InsufficientWeightEvidenceError(f"missing bits-per-weight: {bits_per_weight!r}")
    return int(round(float(total_parameters) * float(bits_per_weight) / 8.0))


def device_weight_bytes_for_offload(
    *,
    primary_weight_bytes: int | None,
    offload_mode: str = "full",
) -> int | None:
    """اشتقاق وزن الجهاز من artifact محدد حسب وضع الإزاحة.

    الإزاحة الكاملة فقط تعيد بايت الأوزان الرئيسية؛ أي وضع جزئي دون خريطة
    طبقات فعلية يعيد None لأن نسبة الطبقات ليست قاعدة عامة.
    """
    if (
        primary_weight_bytes is None
        or isinstance(primary_weight_bytes, bool)
        or not isinstance(primary_weight_bytes, int)
        or primary_weight_bytes <= 0
    ):
        return None
    if offload_mode == "full":
        return primary_weight_bytes
    return None

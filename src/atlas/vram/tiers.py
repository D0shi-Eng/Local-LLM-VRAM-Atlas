"""الفئات الرسمية: التسمية للمستخدم والبايت للحساب دون خلط."""

from __future__ import annotations

from atlas.memory.units import tier_nominal_bytes

# الفئات الرسمية للمشروع.
SUPPORTED_TIERS_GB: tuple[int, ...] = (4, 8, 12, 16)

# سياسة السعة الموثقة: الاسم التجاري لا قيمة رياضية غامضة.
CAPACITY_POLICY_ID = "atlas-tier-nominal-v1"
CAPACITY_POLICY_NOTE = (
    "nominal capacity equals tier GiB in bytes; usable capacity is lower and "
    "enters later via a calibrated system_headroom_profile, never a hidden constant"
)


def is_supported_tier(tier_gb: int | None) -> bool:
    """التحقق من انتماء الفئة الرسمية دون تخمين."""
    return tier_gb in SUPPORTED_TIERS_GB


def tier_capacity_bytes(tier_gb: int) -> int:
    """سعة الفئة بالبايت وفق السياسة الاسمية الموثقة."""
    if not is_supported_tier(tier_gb):
        raise ValueError(f"unsupported VRAM tier: {tier_gb!r}")
    return tier_nominal_bytes(int(tier_gb))

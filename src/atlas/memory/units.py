"""الوحدات المعيارية: البايت قانوني والجيبيبايت للعرض فقط."""

from __future__ import annotations

# القاسم الثنائي الوحيد المعتمد؛ GB العشرية لا تستخدم للحساب أبدًا.
BYTES_PER_GIB = 1024**3
BYTES_PER_GB = 1000**3


def bytes_to_gib(size_bytes: int) -> float:
    """تحويل البايت إلى غيبيبايت ثنائية دون تقريب مبكر."""
    if not isinstance(size_bytes, int) or isinstance(size_bytes, bool):
        raise TypeError("size_bytes must be an int")
    if size_bytes < 0:
        raise ValueError("size_bytes must be non-negative")
    return size_bytes / BYTES_PER_GIB


def gib_to_bytes(value_gib: int | float) -> int:
    """تحويل الغيبيبايت إلى بايت صحيح للحساب الآمن."""
    if isinstance(value_gib, bool) or not isinstance(value_gib, (int, float)):
        raise TypeError("value_gib must be a number")
    if value_gib < 0:
        raise ValueError("value_gib must be non-negative")
    return int(round(float(value_gib) * BYTES_PER_GIB))


def tier_nominal_bytes(tier_gb: int) -> int:
    """سعة الفئة الاسمية بالبايت وفق سياسة atlas-tier-nominal-v1."""
    if tier_gb not in (4, 8, 12, 16):
        raise ValueError(f"unknown VRAM tier: {tier_gb!r}")
    return int(tier_gb) * BYTES_PER_GIB


def format_gib(size_bytes: int, digits: int = 2) -> str:
    """تنسيق العرض فقط مع بقاء القيمة الدقيقة بالبايت داخليًا."""
    return f"{bytes_to_gib(size_bytes):.{digits}f} GiB"

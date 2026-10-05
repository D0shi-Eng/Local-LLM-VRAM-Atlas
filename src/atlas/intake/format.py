"""مساعدات الحجم الموحدة: البايت قيمة معيارية والعرض مشتق فقط."""

from __future__ import annotations

# ثابت التحويل الثنائي الوحيد المعتمد في المشروع.
_GIB_DIVISOR = 1024**3


def bytes_to_gib(size_bytes: int) -> float:
    """تحويل البايت إلى غيبيبايت ثنائية بقيمة معلومة الدقة."""
    if not isinstance(size_bytes, int) or isinstance(size_bytes, bool):
        raise TypeError("size_bytes must be an int")
    if size_bytes < 0:
        raise ValueError("size_bytes must be non-negative")
    return size_bytes / _GIB_DIVISOR


def round_gib(value_gib: float, digits: int = 3) -> float:
    """تقريب قيمة العرض فقط دون المساس بالقيمة المعيارية بالبايت."""
    return round(float(value_gib), digits)

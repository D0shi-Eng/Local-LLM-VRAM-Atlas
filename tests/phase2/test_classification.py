"""اختبارات التصنيف والوحدات وعزل حجم الملف."""

from atlas.memory.units import bytes_to_gib, gib_to_bytes, tier_nominal_bytes
from atlas.vram.classifier import classify_tier
from atlas.vram.tiers import SUPPORTED_TIERS_GB, is_supported_tier, tier_capacity_bytes


def _cap(tier: int) -> int:
    """سعة الفئة بالبايت وفق السياسة الموثقة."""
    return tier_capacity_bytes(tier)


def test_range_classification_fit():
    """upper<=tier يعني estimated_fit."""
    decision = classify_tier(4_000_000_000, 5_000_000_000, _cap(16), 16)
    assert decision.classification == "estimated_fit"


def test_range_classification_indeterminate():
    """الفئة داخل النطاق تعني indeterminate_fit."""
    decision = classify_tier(4_000_000_000, 10_000_000_000, _cap(8), 8)
    assert decision.classification == "indeterminate_fit"


def test_range_classification_not_fit():
    """lower>tier مع حد أدنى موثوق يعني estimated_not_fit."""
    decision = classify_tier(6_000_000_000, 8_000_000_000, _cap(4), 4)
    assert decision.classification == "estimated_not_fit"


def test_unknown_overhead_means_insufficient_evidence():
    """غياب upper الموثوق يمنع Fit: النتيجة أدلة ناقصة لا تخمين."""
    decision = classify_tier(13_000_000_000, None, _cap(16), 16)
    assert decision.classification == "insufficient_evidence"
    # لكن حدًا أدنى يتجاوز السعة يثبت عدم الملاءمة دون حاجة للعلوي.
    exceeded = classify_tier(20_000_000_000, None, _cap(16), 16)
    assert exceeded.classification == "estimated_not_fit"


def test_gb_gib_not_interchangeable():
    """GB عشرية وGiB ثنائية لا تُستخدمان بالتبادل."""
    assert bytes_to_gib(1024**3) == 1.0
    assert gib_to_bytes(1.0) == 1024**3
    assert tier_nominal_bytes(4) == 4 * 1024**3
    assert tier_nominal_bytes(4) != 4_000_000_000


def test_official_tiers_only():
    """الفئات الرسمية 4/8/12/16 فقط."""
    assert SUPPORTED_TIERS_GB == (4, 8, 12, 16)
    for tier in SUPPORTED_TIERS_GB:
        assert is_supported_tier(tier) is True
    assert is_supported_tier(24) is False


def test_artifact_bytes_alone_never_fit():
    """حجم artifact وحده لا ينتج Fit: التصنيف يتطلب نطاقًا مكتملًا."""
    decision = classify_tier(6_000_000_000, None, _cap(8), 8)
    assert decision.classification == "insufficient_evidence"

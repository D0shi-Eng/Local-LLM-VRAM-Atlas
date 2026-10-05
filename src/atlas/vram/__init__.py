"""حزمة تصنيف VRAM: الفئات الرسمية والحالات القائمة على النطاق."""

from atlas.vram.classifier import (
    ClassificationResult,
    TierSetResult,
    classify_all_tiers,
    classify_tier,
)
from atlas.vram.tiers import (
    CAPACITY_POLICY_ID,
    SUPPORTED_TIERS_GB,
    is_supported_tier,
    tier_capacity_bytes,
)

__all__ = [
    "CAPACITY_POLICY_ID",
    "SUPPORTED_TIERS_GB",
    "ClassificationResult",
    "TierSetResult",
    "classify_all_tiers",
    "classify_tier",
    "is_supported_tier",
    "tier_capacity_bytes",
]

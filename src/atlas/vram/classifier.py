"""التصنيف القائم على النطاق: الحالات الصريحة دون حدسية الضيق."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ClassificationResult:
    """نتيجة تصنيف فئة واحدة مع السبب المسجل."""

    tier_gb: int
    tier_capacity_bytes: int
    classification: str
    reason: str


@dataclass(frozen=True)
class TierSetResult:
    """نتيجة الفئات الأربع مع الحد الأدنى الاسمي دون توصية."""

    estimate_status: str
    lower_bytes: int | None
    upper_bytes: int | None
    decisions: tuple[ClassificationResult, ...]
    estimated_minimum_nominal_tier_gb: int | None
    recommendation_headroom_status: str = "not_calibrated"
    warnings: tuple[str, ...] = field(default_factory=tuple)


# حالات التصنيف المسموحة؛ verified_fit تتطلب قياسًا خارج نطاق المرحلة.
CLASSIFICATION_STATES = (
    "estimated_fit",
    "indeterminate_fit",
    "estimated_not_fit",
    "insufficient_evidence",
    "unsupported",
)


def classify_tier(
    lower_bound_bytes: int | None,
    upper_bound_bytes: int | None,
    tier_capacity_bytes_value: int,
    tier_gb: int,
    *,
    lower_trustworthy: bool = True,
    upper_available: bool = True,
) -> ClassificationResult:
    """تصنيف النطاق مقابل سعة الفئة وفق القواعد المفاهيمية الموثقة."""
    if lower_bound_bytes is None:
        return ClassificationResult(
            tier_gb=tier_gb,
            tier_capacity_bytes=tier_capacity_bytes_value,
            classification="insufficient_evidence",
            reason="no trustworthy lower bound; unknown overhead blocks the decision",
        )
    if not isinstance(lower_bound_bytes, int) or lower_bound_bytes < 0:
        return ClassificationResult(
            tier_gb=tier_gb,
            tier_capacity_bytes=tier_capacity_bytes_value,
            classification="insufficient_evidence",
            reason="invalid lower bound value",
        )
    if upper_bound_bytes is None or not upper_available:
        # دون حد علوي موثوق لا يعلن fit أبدًا، ولا indeterminate دون نطاق:
        # النطاق يتطلب حدين، وغياب العلوي الموثوق يعني أدلة ناقصة.
        if lower_bound_bytes > tier_capacity_bytes_value and lower_trustworthy:
            return ClassificationResult(
                tier_gb=tier_gb,
                tier_capacity_bytes=tier_capacity_bytes_value,
                classification="estimated_not_fit",
                reason="trustworthy lower bound alone exceeds tier capacity",
            )
        return ClassificationResult(
            tier_gb=tier_gb,
            tier_capacity_bytes=tier_capacity_bytes_value,
            classification="insufficient_evidence",
            reason="reliable upper bound unavailable; runtime overhead unknown",
        )
    if upper_bound_bytes <= tier_capacity_bytes_value:
        return ClassificationResult(
            tier_gb=tier_gb,
            tier_capacity_bytes=tier_capacity_bytes_value,
            classification="estimated_fit",
            reason="reliable upper bound fits inside tier capacity",
        )
    if lower_bound_bytes <= tier_capacity_bytes_value < upper_bound_bytes:
        return ClassificationResult(
            tier_gb=tier_gb,
            tier_capacity_bytes=tier_capacity_bytes_value,
            classification="indeterminate_fit",
            reason="tier capacity falls inside the uncertainty range",
        )
    if lower_bound_bytes > tier_capacity_bytes_value and lower_trustworthy:
        return ClassificationResult(
            tier_gb=tier_gb,
            tier_capacity_bytes=tier_capacity_bytes_value,
            classification="estimated_not_fit",
            reason="trustworthy lower bound exceeds tier capacity",
        )
    return ClassificationResult(
        tier_gb=tier_gb,
        tier_capacity_bytes=tier_capacity_bytes_value,
        classification="insufficient_evidence",
        reason="lower bound is not trustworthy enough for a not-fit verdict",
    )


def classify_all_tiers(
    *,
    lower_bound_bytes: int | None,
    upper_bound_bytes: int | None,
    tier_capacities: dict[int, int] | None = None,
    estimate_status: str = "estimated",
) -> TierSetResult:
    """تصنيف الفئات الأربع مع الحد الأدنى الاسمي دون Recommended VRAM."""
    if tier_capacities is None:
        from atlas.vram.tiers import SUPPORTED_TIERS_GB, tier_capacity_bytes

        tier_capacities = {tier: tier_capacity_bytes(tier) for tier in SUPPORTED_TIERS_GB}
    if estimate_status == "unsupported_architecture_for_estimation":
        decisions = tuple(
            ClassificationResult(
                tier_gb=tier,
                tier_capacity_bytes=capacity,
                classification="unsupported",
                reason="architecture unsupported for estimation",
            )
            for tier, capacity in sorted(tier_capacities.items())
        )
        return TierSetResult(
            estimate_status=estimate_status,
            lower_bytes=lower_bound_bytes,
            upper_bytes=upper_bound_bytes,
            decisions=decisions,
            estimated_minimum_nominal_tier_gb=None,
            warnings=("unsupported architecture: no tier verdict is produced",),
        )
    decisions = tuple(
        classify_tier(lower_bound_bytes, upper_bound_bytes, capacity, tier)
        for tier, capacity in sorted(tier_capacities.items())
    )
    minimum: int | None = None
    for decision in decisions:
        if decision.classification == "estimated_fit":
            minimum = decision.tier_gb
            break
    warnings = (
        ("nominal_minimum_only: Recommended VRAM stays deferred until headroom calibration",)
        if minimum is not None
        else ("no_estimated_fit: evidence does not support any nominal tier",)
    )
    return TierSetResult(
        estimate_status=estimate_status,
        lower_bytes=lower_bound_bytes,
        upper_bytes=upper_bound_bytes,
        decisions=decisions,
        estimated_minimum_nominal_tier_gb=minimum,
        warnings=warnings,
    )

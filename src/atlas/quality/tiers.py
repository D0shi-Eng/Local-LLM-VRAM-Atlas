"""Quality evidence hierarchy (Phase 6, V1).

Quality claims require evidence. Popularity is deliberately outside this
hierarchy: downloads/likes/trending never enter a quality tier, a quality band
or a recommendation order.

The tiers are ordered strongest-first. They describe *where a number came
from*, never how good the number is.
"""

from __future__ import annotations

# Ordered strongest-first. Popularity signals are intentionally absent.
QUALITY_SOURCE_TIERS = (
    "q1_independent_standardized",
    "q2_independent_academic",
    "q3_verified_community_with_logs",
    "q4_publisher",
    "q5_community_anecdotal",
)

QUALITY_TIER_RANK = {tier: index for index, tier in enumerate(QUALITY_SOURCE_TIERS)}

# Metadata/popularity signals: displayable, never quality evidence.
NON_QUALITY_SIGNALS = (
    "downloads",
    "likes",
    "trending",
    "repository_stars",
    "publisher_fame",
    "release_recency",
    "parameter_count",
    "quant_file_count",
    "marketing_claims",
)

EVIDENCE_STATUS_VALUES = (
    "independent_multi_source",
    "independent_single_source",
    "verified_single_source",
    "publisher_only",
    "community_only",
    "insufficient",
    "unknown",
)

# Which independent evidence statuses are mutually independent runs.
_INDEPENDENT_STATUSES = frozenset(
    {"independent_multi_source", "independent_single_source", "verified_single_source"}
)


def is_quality_tier(value: object) -> bool:
    """Membership test for the documented tier ladder."""
    return isinstance(value, str) and value in QUALITY_TIER_RANK


def tier_rank(value: object) -> int | None:
    """Rank within the ladder; None when the tier is unknown."""
    return QUALITY_TIER_RANK.get(value) if isinstance(value, str) else None


def stronger_tier(first: object, second: object) -> bool:
    """Strict ordering between two documented tiers."""
    left = tier_rank(first)
    right = tier_rank(second)
    if left is None or right is None:
        return False
    return left < right


def is_quality_evidence_status(value: object) -> bool:
    """Membership test for quality evidence classification."""
    return isinstance(value, str) and value in EVIDENCE_STATUS_VALUES


def is_independent_status(value: object) -> bool:
    """Independent-origin statuses only; publisher/community never qualify."""
    return isinstance(value, str) and value in _INDEPENDENT_STATUSES


def evidence_status_from_origins(
    origins: list[str],
    *,
    verification_statuses: list[str],
    independent_sources: list[str] | None = None,
) -> str:
    """Classify a model's quality evidence from resolved origins.

    Independence is counted by *original evaluator runs*, not by URLs: two
    websites republishing one publisher run stay publisher-only. When source
    identifiers are supplied, distinct independent sources are counted; without
    them the origin label alone is used conservatively (one run).
    """
    origin_set = {o for o in origins if isinstance(o, str) and o}
    publisher_present = "publisher" in origin_set
    community_present = "community" in origin_set
    if independent_sources is None:
        independent_runs = 1 if "independent" in origin_set else 0
    else:
        independent_runs = len({s for s in independent_sources if isinstance(s, str) and s.strip()})
    verified = any(
        v in ("independently_verified", "atlas_verified", "verified")
        for v in verification_statuses
        if isinstance(v, str)
    )
    if independent_runs >= 2:
        return "independent_multi_source"
    if independent_runs == 1:
        return "independent_single_source"
    if publisher_present and verified:
        return "verified_single_source"
    if publisher_present:
        return "publisher_only"
    if community_present:
        return "community_only"
    if not origins:
        return "unknown"
    return "insufficient"

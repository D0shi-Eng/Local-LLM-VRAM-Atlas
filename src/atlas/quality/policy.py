"""Versioned quality/recommendation policies (Phase 6).

Policies are declared data, never template logic. Every threshold lives here
with a documented rationale; no S/A/B/C bands are invented from intuition and
no "93% confidence" probabilities are produced.
"""

from __future__ import annotations

from atlas.quality import RECOMMENDATION_POLICY_ID

QUALITY_EVIDENCE_POLICY = {
    "schema_version": "0.6.0",
    "policy_id": "atlas-quality-evidence",
    "policy_version": "0.6.0",
    "policy_kind": "quality_evidence",
    "rules": {
        "quality_source_tiers": [
            "q1_independent_standardized",
            "q2_independent_academic",
            "q3_verified_community_with_logs",
            "q4_publisher",
            "q5_community_anecdotal",
        ],
        "independent_threshold_for_high_quality_candidate": [
            "independent_multi_source",
            "independent_single_source",
            "verified_single_source",
        ],
        "excluded_signals": [
            "downloads",
            "likes",
            "trending",
            "repository_stars",
            "publisher_fame",
            "release_recency",
            "parameter_count",
            "quant_file_count",
            "marketing_claims",
        ],
        "missing_axis_value": "unknown",
        "cross_metric_raw_aggregation": "forbidden",
        "base_score_attached_to_quant": "forbidden",
        "parent_score_attached_to_alignment_variant": "forbidden",
    },
    "source_assumptions": [
        "Only published evaluation results are ingested; Atlas never runs a benchmark.",
        "An independent run is identified by its original evaluator, not by a URL.",
        "A second website republishing one publisher run does not add independence.",
        "Publisher and community results stay readable but never reach the independent threshold.",
        "Popularity, size, recency and brand are metadata only and never enter quality.",
    ],
    "rationale": (
        "Quality must be traceable to an evaluator and a benchmark version. Independence is "
        "counted by original evaluation runs. Missing evidence is reported as unknown so a "
        "gap is never confused with a failure."
    ),
    "superseded_by": None,
    "created_at": None,
}

QUALITY_BAND_POLICY = {
    "schema_version": "0.6.0",
    "policy_id": "atlas-quality-band",
    "policy_version": "0.6.0",
    "policy_kind": "quality_band",
    "rules": {
        "bands_defined": False,
        "reason": (
            "No letter or numeric quality band is emitted in Phase 6: defensible bands require "
            "a populated cross-source benchmark population, which the current catalog does not "
            "have. Same-benchmark ranking is still available per benchmark+version+mode."
        ),
        "allowed_quality_bands": [],
        "same_benchmark_ranking_allowed": True,
    },
    "source_assumptions": [
        "Percentiles are Atlas-computed inside one exact comparable population and documented.",
        "No percentile is attributed to a source unless that source publishes it.",
    ],
    "rationale": (
        "Refusing to invent bands is preferable to shipping intuition-based grades that cannot be "
        "audited or reproduced."
    ),
    "superseded_by": None,
    "created_at": None,
}

FRESHNESS_POLICY = {
    "schema_version": "0.6.0",
    "policy_id": "atlas-quality-freshness",
    "policy_version": "0.6.0",
    "policy_kind": "freshness",
    "rules": {
        "wall_clock_staleness_days": None,
        "reason": (
            "No arbitrary N-day expiry is applied. Freshness is expressed through supersession "
            "(a newer benchmark version or corrected result) and revision drift, not elapsed days."
        ),
        "stale_states": ["superseded", "historical_revision_evidence"],
        "preserves_history": True,
    },
    "source_assumptions": [
        "Old evidence is retained and may be marked superseded; it is never deleted.",
        "A benchmark version change marks prior results superseded rather than rewriting them.",
    ],
    "rationale": (
        "Benchmark supersession and harness change are real invalidation signals; "
        "elapsed time alone "
        "is not evidence of invalidity."
    ),
    "superseded_by": None,
    "created_at": None,
}

RECOMMENDATION_POLICY = {
    "schema_version": "0.6.0",
    "policy_id": RECOMMENDATION_POLICY_ID,
    "policy_version": "0.6.0",
    "policy_kind": "recommendation_eligibility",
    "rules": {
        "required_domains": [
            "quality",
            "vram_fit",
            "runtime",
            "license",
            "variant_identity",
            "evidence_quality",
        ],
        "strict_fit_states": ["estimated_fit"],
        "candidate_fit_states": ["indeterminate_fit"],
        "never_strict_fit_states": ["insufficient_evidence", "unsupported", "estimated_not_fit"],
        "quality_status_for_strict": ["known"],
        "runtime_status_for_strict": ["documented"],
        "license_status_for_strict": ["permissive", "restricted"],
        "variant_identity_for_strict": ["exact"],
        "evidence_quality_for_strict": ["complete"],
        "quant_retention_disclosure_required": True,
        "alignment_variant_requires_exact_evidence": True,
        "confidence_states": [
            "high_evidence",
            "moderate_evidence",
            "limited_evidence",
            "insufficient",
        ],
        "confidence_is_categorical_not_probabilistic": True,
        "supported_tiers_gb": [4, 8, 12, 16],
        "supported_use_cases": [
            "general",
            "coding",
            "reasoning",
            "agentic_tool_use",
            "multilingual",
        ],
        "ranking_requires_uniform_eligibility": True,
        "manual_override": {
            "allowed": False,
            "reason": (
                "Recommendation order derives from policy and evidence only; "
                "no preferred names exist."
            ),
        },
        "brand_and_quantizer_bias": "forbidden",
    },
    "source_assumptions": [
        "VRAM fit states keep Phase 2-5 semantics; no tier verdict is weakened in Phase 6.",
        "Atlas performs no measurement, so every VRAM state is an estimate or is insufficient.",
        "A quantized artifact with unknown retention is disclosed as base-known, "
        "retention-unknown.",
        "An uncensored/abliterated/heretic variant never inherits the parent's quality score.",
    ],
    "rationale": (
        "A strict recommendation needs independent evidence in every domain at once. Partial "
        "evidence is reported as candidate or insufficient, never upgraded by popularity, size, "
        "brand or quantizer reputation."
    ),
    "superseded_by": None,
    "created_at": None,
}

ALL_POLICIES = (
    QUALITY_EVIDENCE_POLICY,
    QUALITY_BAND_POLICY,
    FRESHNESS_POLICY,
    RECOMMENDATION_POLICY,
)


def policy_by_id(policy_id: str) -> dict | None:
    """Look up a declared policy by identifier."""
    for policy in ALL_POLICIES:
        if policy["policy_id"] == policy_id:
            return policy
    return None


def policy_versions() -> dict[str, str]:
    """Current policy versions for the release-candidate manifest."""
    return {policy["policy_id"]: policy["policy_version"] for policy in ALL_POLICIES}

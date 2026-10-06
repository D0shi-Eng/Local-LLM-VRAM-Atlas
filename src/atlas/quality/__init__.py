"""Quality package.

Evidence-aware quality intelligence: benchmark identity/version handling,
evaluation-result normalization, quantization retention, multi-axis quality
profiles and versioned recommendation readiness.

Invariants enforced here:
- quality never derives from downloads, likes, stars, size or recency;
- missing evidence stays unknown, never zero;
- a base-model score is never attached to a quantized artifact;
- different benchmark versions are never merged;
- publisher results are never relabeled independent.
"""

from __future__ import annotations

QUALITY_SNAPSHOT_VERSION = "0.6.0"
QUALITY_POLICY_ID = "atlas-quality-policy"
RECOMMENDATION_POLICY_ID = "atlas-recommendation-policy"
QUALITY_SCHEMA_VERSION = "0.6.0"

__all__ = [
    "QUALITY_SNAPSHOT_VERSION",
    "QUALITY_POLICY_ID",
    "RECOMMENDATION_POLICY_ID",
    "QUALITY_SCHEMA_VERSION",
]

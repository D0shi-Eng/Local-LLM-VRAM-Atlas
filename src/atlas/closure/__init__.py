"""Phase 6.5 evidence closure (local, metadata-only, zero-weight).

This package closes high-value evidence gaps for a bounded Core
Recommendation Set. It never re-implements Phase 0-6 subsystems: memory
formulas, the VRAM classifier, architecture resolution, the quality evidence
model, the recommendation policy and the Phase 5 change journal are all
imported and reused.

Invariants enforced here:

- historical evidence sidecars are never fabricated (Phase 6 left 243 logical
  references without sidecars; they stay ``evidence_sidecar_unavailable``);
- current evidence is new, revision-distinguished evidence with new V2 ids;
- a Core candidate always names an exact artifact set, never a bare model
  name;
- no popularity, size, parameter count, brand or recency signal may raise a
  readiness state;
- VRAM fit states keep Phase 2 classifier semantics; no tier verdict is
  weakened to create a non-zero count.
"""

CLOSURE_SCHEMA_VERSION = "0.1.0"
CLOSURE_SNAPSHOT_VERSION = "0.1.0"
CORE_SET_VERSION = "0.1.0"
CLOSURE_POLICY_ID = "atlas-closure-readiness"
CLOSURE_POLICY_VERSION = "0.1.0"

REFERENCE_DATE = "2026-10-05"

__all__ = (
    "CLOSURE_POLICY_ID",
    "CLOSURE_POLICY_VERSION",
    "CLOSURE_SCHEMA_VERSION",
    "CLOSURE_SNAPSHOT_VERSION",
    "CORE_SET_VERSION",
    "REFERENCE_DATE",
)

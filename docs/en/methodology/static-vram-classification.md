# Static VRAM Classification Methodology (Phase 3)

> Arabic counterpart: `docs/ar/methodology/static-vram-classification.md`

## Conservative range semantics (unchanged from Phase 2)

For 4/8/12/16 GB tiers against nominal capacity (`atlas-tier-nominal-v1`):
a reliable upper bound at or under capacity yields `estimated_fit`; capacity
inside a fully bounded range yields `indeterminate_fit`; a trustworthy lower
bound above capacity yields `estimated_not_fit`. Without a reliable upper
bound, no fit is ever claimed — the verdict is `insufficient_evidence`
(the lower-bound-only case), except that a lower bound already exceeding
capacity proves `estimated_not_fit` alone. Artifact size alone never
produces a fit claim, and `likely_fit` does not exist in the vocabulary.

## Verified fit stays unavailable

`verified_fit` cannot come from Atlas calculation; only sufficiently
documented external measurement (see external-measurement methodology) can
ground it. Calculated and measured stay terminologically separate.

## No recommendations, no ranking

Recommended VRAM remains deferred until a headroom calibration policy
exists (`not_calibrated`). There are no best-model lists, no top-model
claims, no Atlas Score, and no rankings of any kind in this phase.

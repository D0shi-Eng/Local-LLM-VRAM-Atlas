# VRAM Tier Presentation

> Conservative. File size ≠ VRAM. Qualified ≠ recommended.

## Language

Tier pages are titled e.g. "8GB VRAM Atlas", never "All models that work on
8GB", unless every entry genuinely meets that standard. Sections separate
`estimated_fit`, `indeterminate_fit`, `estimated_not_fit`,
`insufficient_evidence`, `unsupported` (plus `verified_fit` only when
external measurement evidence with full conditions exists; Atlas never
measures during intake).

## Method

Only the range classifier (`src/atlas/vram/classifier.py`) with ranged
static estimates (`src/atlas/memory/estimator.py`, 8K baseline). No
`artifact_size < tier_size → fits` shortcut exists; regression tests guard
it. MoE active parameters are never used as resident weights.

## External measurements

Stored, never performed. Each preserves origin, revision, artifact, runtime
+ version, GPU, context, batch, KV format, offload, stage, reported VRAM,
source, observed_at. Vague "uses 7GB" claims stay weak or unused for tier
promotion. `atlas_measured` is structurally forbidden at intake.

## Related

- `static-vram-classification.md`, `vram-methodology.md`
- `external-measurement-evidence.md`, `static-memory-modeling.md`

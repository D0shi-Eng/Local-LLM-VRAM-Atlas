# Static Memory Modeling Methodology (Phase 3)

> Arabic counterpart: `docs/ar/methodology/static-memory-modeling.md`

## What the static model covers

The static model builds on Phase 2 with: artifact weight-storage evidence,
architecture-derived cache calculations (global or layer-plan path), known
auxiliary component sizes, and documented runtime-independent mathematics.
Every calculation exposes `formula_id`, `formula_version`, inputs, input
evidence, result, units, and unsupported components. Same inputs always
produce the same result; formulas are never edited in place — semantics
changes create new versions.

## Storage versus residency

`remote_artifact_bytes`, `weight_storage_bytes`,
`estimated_device_weight_bytes`, `host_resident_bytes`,
`device_resident_bytes`, and `runtime_allocated_bytes` are distinct concepts,
never synonyms. Source-reported artifact storage feeds a lower-bound model
only; it is never labeled measured VRAM. MoE active parameters never
substitute resident weights.

## Cache profiles and context

Every cache calculation names an explicit profile: context tokens, sequence
count, cache dtype/format, architecture revision, and formula version. The
8K baseline (`atlas-text-8k-baseline-v1`) is retained unchanged. Advertised,
configured, and calculation contexts are separate: a calculation targeting
more context than the model advertises refuses instead of raising context
synthetically. Weights never scale with context; standard KV scales linearly.

## No fabricated overhead

Runtime overhead is never invented (`+500MB`, `+10%`, and friends are
forbidden). Without a documented runtime profile the upper bound stays
unknown and tier classification stays conservative. Multimodal components
(vision, projector, audio) are represented separately, never merged into
language-model math.

# Lineage Methodology

> Arabic counterpart: `docs/ar/methodology/lineage-methodology.md`

## Relations

Lineage supports: `base_model`, `fine_tune_of`, `quantized_from`,
`derived_from`, `format_variant_of`, `official_variant_of`. Each edge
records its source; `model_card_metadata` edges stay `publisher_declared`
and are never auto-upgraded to `atlas_verified`.

## Evidence bar

`base_model` metadata in a model card is enough to record a lineage edge
with publisher-declared status — it is not enough to verify it. Name
similarity alone (`SomeModel-27B-Q4` looking like a 27B Q4 quant) is an
`inferred_candidate_signal` at best, never a verified fact, and never a
parameter count, license, or base-model claim.

## Identity classes

`same_repository_same_revision`, `same_repository_new_revision`, `mirror`,
`format_variant`, `quantized_variant`, `fine_tune`, `official_sibling`,
`third_party_derivative`, `same_family`, `unrelated_same_name`. Models from
one family are explicitly not duplicates.

## Chain direction

```text
Original Model → Fine-tuned Model → Quantized Variant → Specific Artifact
```

each edge carrying its own source, so future stages can attach license,
behavior, and hardware statements to the right artifact.

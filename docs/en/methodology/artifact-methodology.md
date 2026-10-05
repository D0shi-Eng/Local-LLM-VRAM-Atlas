# Artifact Methodology

> Arabic counterpart: `docs/ar/methodology/artifact-methodology.md`

## From filenames to artifact sets

A quantized model variant is an **artifact set** (`src/atlas/artifact/`): one
or more files that together form a single loadable variant, described by
`artifact_set_id`, `model_id`, `revision`, `variant`, `format`, file list,
shard accounting, source-reported byte totals, companion components, and a
verification status. The schema is `schemas/artifact.schema.json` (`0.2.0`).

## Shards group, variants never merge

Files matching the shard pattern (`model-00001-of-00005`, supporting both
0-based and 1-based indexing) with the same stem, container, and quant token
group into one `sharded` set. The grouper verifies completeness: missing
indices, repeated indices, and disagreeing totals each produce an explicit
warning. Files such as `model-Q4_K_M.gguf`, `model-Q5_K_M.gguf`, and
`model-Q8_0.gguf` are **separate variants**, never shards of each other, even
when their stems look alike.

## Companions stay out of the weights

Vision projectors (`mmproj`), tokenizers, configs, safetensors index files,
and documentation are classified as auxiliary (`companion.py`) and recorded in
`companion_components`. They never inflate `primary_weight_bytes`. Multimodal
memory enters future estimates as its own component, not as language-model
weight.

## Repository totals are forbidden

A repository may hold dozens of quantizations plus configs and cards, so the
repository's total storage is never used as a model size. Every byte total is
artifact-specific and sums only source-reported file sizes; a missing size
yields `null` plus a warning, never a silent partial sum.

## Detection honesty

Quantization detected from a filename alone is `filename_inferred`.
Structured tensor inventories yield `verified_metadata`. Disagreements are
stored as conflicts with both sides preserved.

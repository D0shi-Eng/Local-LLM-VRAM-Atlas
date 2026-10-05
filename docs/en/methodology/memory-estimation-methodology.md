# Memory Estimation Methodology

> Arabic counterpart: `docs/ar/methodology/memory-estimation-methodology.md`

## Components, never a single multiplier

Peak VRAM is a sum of named components (`src/atlas/memory/components.py`):
device-resident weights, KV/state cache, static and dynamic runtime memory,
compute workspace, graph and output buffers, multimodal components,
speculative-decoding memory, and other known bytes. There is no global
`weights × 1.2` rule; every constant is named, versioned in the formula
registry (`formulas.py`), and sourced. Unknown components stay `null` and are
listed in `unknown_components` — unknown never becomes zero.

## Ranged estimates

Every estimate reports `estimated_vram_lower_bytes` and
`estimated_vram_upper_bytes` with an `estimate_status` and an evidence basis
(schema `memory-estimate.schema.json`, `0.2.0`). The lower bound covers only
documented components; the upper bound additionally requires measured runtime
overhead. When no trustworthy upper bound exists, the result says so instead
of inventing one.

## Weight residency rules

Device weight bytes come from verified artifact bytes under full offload, or
from resident parameter counts times a documented bits-per-weight. For MoE,
residency always uses **total** resident tensors: `active_parameters`
describes compute and routing, never residency, and passing active parameters
as a residency substitute is a tested defect. Partial offload without a real
layer-placement map yields `unknown`, never `file_size × layer_fraction`.

## No estimate without a calculation profile

Every estimate names an explicit profile (context tokens, sequence count, KV
dtype and quantization, runtime, backend, offload mode, multimodal mode).
The engineering baseline is `atlas-text-8k-baseline-v1` (single sequence,
8K context, full offload, text only, applicable only when the model
advertises ≥ 8K). Missing or underspecified profiles refuse with
`insufficient_evidence`.

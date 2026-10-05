# VRAM Methodology

> Arabic counterpart: `docs/ar/methodology/vram-methodology.md`

## Core rule

File size is not VRAM usage. A weight file smaller than a GPU's memory proves
nothing by itself: the backend allocates its own buffers, the KV cache grows with
context, and the offload strategy changes the total. The record therefore keeps
these concepts in separate fields: `weight_file_size_gib`, `measured_vram_gib`,
`estimated_vram_gib`, `minimum_vram_gib`, `recommended_vram_gib`,
`runtime_overhead_gib`, plus KV-cache, context, batch, offload, and backend data.
No tooling may decide "fits" from `file_size_gib <= gpu_vram`.

## Tiers

The official Atlas tiers are 4GB, 8GB, 12GB, and 16GB. The tier is a label; the
record always keeps the real measured or estimated figure alongside it
(e.g. `vram_tier_gb: 8` with `recommended_vram_gib: 7.2`). A tier never replaces
a measurement.

## Measurement baseline (text LLMs)

Where applicable, the reference conditions are: batch size 1, text generation,
full GPU offload, 8K context baseline, and a stated runtime/backend, KV-cache
configuration, and GPU device. These conditions do not fit every architecture;
whenever context, KV format, or backend changes, VRAM can change, so no VRAM
figure stands without its conditions.

## Minimum versus recommended

- **Minimum:** the lowest VRAM at which operation was shown or estimated under
  documented conditions.
- **Recommended:** the level with a realistic margin for runtime, KV cache, and
  context, without unrealistic pressure. A 15.9 GiB footprint is not "recommended"
  for a 16GB card just because the weights are under 16GB.

## Evidence kinds

`measured` (with a recorded measurement source and conditions), `estimated`
(under a documented method), `publisher_claim`, `community_report`, `unknown`.
Community reports can motivate a measurement; they never are one.

## Units

Memory and file sizes distinguish GB (decimal) from GiB (binary) and always state
the unit. Timestamps use ISO 8601 with timezone. Parameter counts distinguish
total from active parameters, particularly for MoE, and no model is classified
on total parameters alone. Advertised maximum context, tested context, and the
context used for a VRAM measurement are three separate fields.

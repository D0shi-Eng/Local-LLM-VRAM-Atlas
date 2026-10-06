# KV / State Cache Methodology

> Arabic counterpart: `docs/ar/methodology/kv-cache-methodology.md`

## The standard formula and its strict gate

For standard attention only, with equal K/V precision:

```
KV bytes = 2 × sequences × context_tokens × layers × kv_heads × head_dim × bytes_per_element
```

(`formula_id: standard-kv-v1`). The gate is strict: grouped-query and
multi-query attention must use `num_key_value_heads`, never
`num_attention_heads` — substituting query heads is a tested defect that can
multiply the estimate severalfold. Context scaling touches the cache
component only; weights never scale with context.

## Quantized cache needs block truth

A quantized KV cache is not `bits / 8` of the standard result. Block-based
formats add scales, metadata, and grouping overhead, so the estimate uses the
runtime's documented block definition (`formula_id: quantized-kv-block-v1`).
Ideal bit-packing is never presented as storage truth.

## Sliding window, MLA, SSM, hybrid

Sliding-window layers cache at most the window, but the window formula
(`sliding-window-kv-v1`) applies only when window size, layer pattern, and
runtime behavior are all known — otherwise the result is unknown. Multi-head
Latent Attention (MLA) needs an architecture-specific latent-cache model;
Mamba/SSM needs a recurrent state model (state dimensions plus convolution
state); hybrid models need summed component-specific models. The cache model defines
none of these, so all three refuse with
`unsupported_architecture_for_estimation`. The architecture support matrix
(`memory/architecture.py`) records per-family weight, cache, overhead, and
classification support with explicit limitations.

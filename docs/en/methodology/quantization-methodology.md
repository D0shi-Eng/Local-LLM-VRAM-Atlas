# Quantization Methodology

> Arabic counterpart: `docs/ar/methodology/quantization-methodology.md`

## Representation, not a single string

Quantization is recorded as a structured object — `format`, `quant_family`,
`quant_name`, `bits_per_weight`, `native_quantization`, `quantizer`,
`quantizer_repo`, `file_size_bytes`, `file_size_gib`, `split_files`,
`source_revision`, `checksum` — never collapsed into one bare label.

## Families

Recognized family labels include `fp32`, `fp16`, `bf16`, `fp8`, `q8`, `q6`, `q5`,
`q4`, `iq4`, `q3`, `iq3`, `q2`, `iq2`, `iq1`, `tq`, `ternary`, `mxfp4`, `nvfp4`,
`awq`, `gptq`, `exl2`, `mlx`, and `other`. These are labels, not a ranking: members
of different families are never treated as directly comparable or equivalent
without evidence, and no quant is described as better than another without proof.

## Compression categories

The descriptive buckets `native_precision`, `light_quantization`,
`balanced_quantization`, `aggressive_quantization`, `ultra_compressed`,
`extreme_compression`, and `native_low_bit` are a preliminary taxonomy, not an
absolute quality verdict. The real quant type always stays in
`quant_family`/`quant_name`, separate from the bucket.

## Provenance

Natively low-bit models (trained at the stated bit depth) are distinguished from
post-training quantization by `native_quantization`, because capability retention
questions differ between the two. Every quantized or modified variant must trace
its lineage: variant, quantized model, modified/fine-tuned model, base model,
original model family. Lineage is never dropped.

# Quantization Methodology — Phase 2 Extension

> Arabic counterpart: `docs/ar/methodology/quantization-methodology-phase-02.md`
> Base document: `docs/en/methodology/quantization-methodology.md`

## Registry, not scattered if-statements

Phase 2 records every known quantization as a versioned registry entry
(`src/atlas/quant/registry.py`, registry version `0.2.0`, observed `2026-10-05`).
Each entry carries its family, container format, runtime family, nominal and
effective bits-per-weight, block layout where documented, aliases, source
project and revision, and verification status. The GGML type enumeration was
re-checked against `ggml/include/ggml.h` at implementation time
(`GGML_TYPE_COUNT=43`, including `Q1_0`, `Q2_0`, `TQ1_0`/`TQ2_0`, `MXFP4`,
`NVFP4`); per-type bit rates come from the Hugging Face GGUF documentation
table, and anything without a documented block definition keeps
`effective_bits_per_weight: null`.

##/bits-per-weight honesty

`Q4` never means `4.000` bits automatically. K-quants carry scale, minimum,
and super-block overhead (`Q4_K` documents `4.5`); IQ-quants depend on an
importance matrix (`IQ2_XXS` documents `2.06`); named K-variants such as
`Q4_K_M` mix precisions per tensor type and therefore carry no single bpw —
their `mixed_precision` flag is `true` and any file-level rate must come from a
real tensor inventory (`effective_bpw = weight_storage_bytes * 8 /
weight_parameter_count`), never from repository totals.

## Separations that must never collapse

- **Container ≠ quantization**: `GGUF` is a container; `Q4_K_M` is a scheme inside it.
- **`MXFP4` ≠ `NVFP4`**: different recipes, different hardware/runtime support.
- **`AWQ` / `GPTQ` / `EXL2` ≠ `Q4`**: independent families identified from
  structured config (`quant_method`, `bits`, `group_size`), never from the
  repository name. EXL2 additionally records `target_bpw`/`effective_bpw`.
- **`FP4` is not a unifying name**: it erases the MXFP4/NVFP4 distinction.
- **Filename inference stays `filename_inferred`**: a structured conflict
  (filename says `Q4`, metadata says `Q5`) is recorded as a conflict, and the
  filename never wins silently and is never promoted to verified.

## Native low-bit and ternary

`native_low_bit` (and the `ternary` family) applies only when the
architecture, training, or checkpoint was natively published at that depth.
Post-training ternarization and the `TQ` storage format are different things
and are recorded separately.

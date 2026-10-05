# Benchmark Methodology

> Arabic counterpart: `docs/ar/methodology/benchmark-methodology.md`

## A result is a configuration, not just a score

A benchmark record stores the score together with everything that produced it:
`benchmark_name`, `benchmark_version`, `benchmark_owner`, model and model revision,
exact quantization, runtime and runtime version, hardware (vendor, model, VRAM,
driver, backend, OS, CPU, system RAM), prompting, reasoning mode, context, score,
`score_unit`, source, evaluation date, and whether the run was independent and
reproducible. Figures from different setups are never compared as equals.

## Origin separation

```text
benchmark_origin: publisher / independent / atlas / community
```

A publisher benchmark is not an independent benchmark. Origins are never averaged
into one number without a published method. A base-model score never stands in for
a quantized variant, and results are never compared across reasoning modes,
quantizations, or hardware without disclosure.

## Independent sources

Independent benchmarks (such as Artificial Analysis and comparable sources, where
suitable) may inform the catalog, but no single leaderboard is an absolute judge.
Each result records its benchmark version and configuration, reasoning mode, and
the exact base model or quant tested.

## Popularity is not quality

Hugging Face downloads, likes, and trending status may be stored as popularity
signals and nothing else. They are never quality benchmarks and never evidence
of intelligence. The schema keeps them in a separate `popularity` object so the
two can never be confused.

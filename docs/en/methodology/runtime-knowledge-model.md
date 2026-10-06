# Runtime Knowledge Model Methodology

> Arabic counterpart: `docs/ar/methodology/runtime-knowledge-model.md`

## Knowledge, not execution

The runtime knowledge base describes runtimes without installing or running them.
Each capability record carries runtime, version/revision, backend, platform,
artifact format, quantization family, architecture family, hardware
requirement, support status, official source, observation date, and notes.

## Support states

`official`, `documented`, `experimental`, `deprecated`, `unsupported`,
`unknown`. An old blog post never becomes current official support, and
support on one backend never implies support on another. Covered runtimes:
llama.cpp, ExLlamaV2/EXL2, Transformers quantization integrations,
TensorRT-LLM, MLX-LM — only where official documentation supports the claim.

## Compatibility is not measurement

A documented supported format is compatibility evidence, never VRAM
measurement evidence. No performance numbers (tokens/sec, latency) are
collected; the foundation is memory and architecture. Runtime memory
profiles (`src/atlas/memory/runtime_profiles.py`) describe loading behavior
with no invented overhead and remain distinct from compatibility claims.

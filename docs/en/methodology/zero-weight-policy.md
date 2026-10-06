# Zero-Weight Policy (permanent architectural rule)

> Arabic counterpart: `docs/ar/methodology/zero-weight-policy.md`

## The rule

Local LLM VRAM Atlas is a zero-weight repository. It stores metadata,
manifests, source references, identifiers, revisions, file names, remote
artifact sizes, remote hashes/OIDs when exposed, licenses, architecture and
quantization facts, runtime compatibility knowledge, mathematics, external
measurement evidence, and documentation. It never stores GGUF, Safetensors,
EXL2, AWQ, GPTQ, MLX, checkpoint, ONNX, or PyTorch weight payloads — no
shards, no partial downloads, no byte-range header inspection.

## Consequences

The future public repository must link users to original providers instead
of rehosting weights. No model cache is ever populated (not even redirected
to another drive). Remote payloads are metadata only: 2 MiB per document,
25 MiB total per run unless the owner explicitly approves otherwise.
Regression tests prove the architecture and memory subsystems never call
weight downloaders or loaders. Any weight download is an automatic
FAIL unless fully remediated.

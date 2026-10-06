# Runtime Support Methodology

> Arabic counterpart: `docs/ar/methodology/runtime-support-methodology.md`

## No VRAM number without a runtime

The same artifact consumes different VRAM under llama.cpp, ExLlamaV2,
TensorRT-LLM, Transformers, MLX, Ollama, or LM Studio. A "model VRAM" figure
without runtime, version, backend, context, and offload mode is an incomplete
statement, so every estimate binds to a `RuntimeMemoryProfile`
(`memory/runtime_profiles.py`): weight-loading behavior, KV cache type and
quantization, workspace and graph behavior, and any *measured* static/dynamic
overhead with its source. Unmeasured overhead stays `unknown`; there is no
`500 MB` or `1 GB` fallback constant.

## Engines, UIs, and hardware

UI products are not engines: LM Studio may use different backends and Ollama
pins a specific engine build, so the record stores engine/backend whenever
known. Format support never implies universal hardware support — NVFP4/MXFP4
support depends on model, runtime version, kernel, and GPU generation, and is
recorded with `observed_at` plus source revision because matrices drift.
Likewise, an AWQ/GPTQ checkpoint existing never implies every runtime runs
it: artifact format, model-architecture support, and GPU-kernel support are
three separate claims.

## Documented profiles, honest limits

The project ships explicit engineering profiles (llama.cpp/CUDA full offload,
ExLlamaV2/CUDA, MLX unified memory, TensorRT-LLM/CUDA) with overhead unknown
by design. A missing runtime from the user yields independent components
only — never a silent default runtime.

# Glossary

> Arabic counterpart: `docs/ar/terminology/glossary.md`

Precise terms, in the standard technical sense. When a term has a formal external
definition, the Atlas follows it and cites it rather than inventing its own.

- **LLM** — Large Language Model: a neural model trained to model and generate
  language, characteristically transformer-based at the scale this Atlas tracks.
- **VRAM** — Video RAM: dedicated GPU memory. The binding constraint for local
  inference on consumer GPUs; not to be confused with system RAM.
- **RAM** — System memory (CPU-side). Relevant for partial offload, but a separate
  budget from VRAM.
- **Parameters** — The model's learned weights, counted in billions (e.g. 8B).
  A capacity indicator, never a VRAM figure on its own.
- **Active Parameters** — Parameters participating in a single forward pass.
  The meaningful count for MoE and hybrid architectures, where it is far below
  the total.
- **Dense** — Architecture in which all parameters participate in every forward pass.
- **MoE** — Mixture of Experts: only a subset of experts is active per token.
  Total parameters overstate the per-token cost; active parameters and expert
  counts must be recorded.
- **Quantization** — Reducing the numerical precision of weights (and sometimes
  activations or the KV cache) below training precision to shrink size and memory.
- **GGUF** — A file format for single-file LLM distribution designed around
  `llama.cpp`, carrying its own quantization types. An extension, not a support proof.
- **AWQ** — Activation-aware Weight Quantization: a 4-bit method preserving salient
  weights, executed by compatible inference engines.
- **GPTQ** — A post-training quantization method with per-group scales, executed by
  compatible inference engines.
- **EXL2** — The ExLlamaV2 quantization format with mixed-precision tuning per layer.
- **MXFP4 / NVFP4** — 4-bit microscaling/narrow formats for efficient inference on
  supporting hardware and runtimes.
- **Ternary** — Native ~1.58-bit representations (weights in {-1, 0, +1} families);
  a trained property, not a post-training compression of arbitrary models.
- **Bits per Weight** — Average stored bits per parameter for a given quant; the
  comparable density figure across quant types.
- **KV Cache** — Key/value tensors cached during generation, growing with context
  length and batch size. A major VRAM consumer beyond the weights.
- **Context Length** — Maximum sequence the model handles. Three separate figures:
  advertised maximum, tested length, and the length used for a VRAM measurement.
- **Full GPU Offload** — All model layers resident on the GPU. The reference
  condition for baseline VRAM statements.
- **Partial Offload** — Some layers on GPU, the rest on CPU/RAM. Changes VRAM,
  speed, and comparability; always stated explicitly.
- **Open Source AI** — A model meeting the Open Source AI Definition 1.0 of the
  Open Source Initiative. Downloadable weights alone do not satisfy it.
- **Open Weights** — Weights available for download, permissive or restricted.
  Availability is not openness in the Open Source sense.
- **Base Model** — The pretrained foundation from which fine-tunes and quants derive.
- **Fine-tune** — A base model further trained for an objective, domain, or behavior.
- **Quantized Variant** — A base or fine-tuned model converted to lower precision
  by a quantizer; lineage and method are part of its identity.
- **Uncensored** — A variant claimed to have refusal behavior reduced or removed.
  A claim about alignment, independent of intelligence or quality.
- **Abliterated** — A variant produced by activation/refusal-direction ablation
  techniques. A method label, not a quality verdict.
- **Heretic** — A community alignment-variant label for models forked away from
  the base alignment posture. Recorded as labeled, with its own evidence.
- **Benchmark** — A reproducible evaluation procedure with a stated configuration,
  owner, and version — not a bare number.
- **Publisher Claim** — Any statement by the model publisher about its own model.
  Useful, citable, and never an independent fact.
- **Independent Verification** — Confirmation by a reproducible third-party source
  under stated conditions.
- **Atlas Verification** — Measurement performed inside this project under
  documented conditions.

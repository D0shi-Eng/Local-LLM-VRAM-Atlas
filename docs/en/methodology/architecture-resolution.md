# Architecture Resolution Methodology

> Arabic counterpart: `docs/ar/methodology/architecture-resolution.md`

## Purpose

Resolve model architecture accurately from bounded public metadata only.
No weights are downloaded, no models are executed, and no value is ever
filled from agent memory of famous models.

## Evidence order

Tier A (structured provider metadata at an immutable revision, GGUF metadata
exposed by the API, official specifications) outranks Tier B (model card
claims), Tier C (derivative/quantizer declarations), and Tier D (filename
hints). Filename inference never overrides structured metadata. The first
tier holding a field wins; disagreements are preserved as conflicts, and
cache calculations depending on a conflicted field refuse.

## Family-specific normalization

Configuration key meanings differ per architecture (`src/atlas/archinfo/`
key maps per family). There is no universal alias dictionary: every mapping
is documented for the family it applies to and tested. Framework class
defaults are never treated as source facts — only source-present values
become evidence. Nested composite configs (`text_config`, `language_config`,
`decoder_config`) define the language-model component boundary; vision,
audio, and encoder components never leak into language-model calculations.

## Head dimension and attention class

Explicit `head_dim` always wins. Calculation (`hidden_size /
num_attention_heads`) is allowed only when the division is exact and is
marked `calculated`. MHA/GQA/MQA classification comes from head counts with
documented semantics, never from the model name.

## Special architectures

MLA, SSM/Mamba/RWKV, hybrid, encoder-decoder, and custom remote-code
architectures never receive the standard KV equation. MLA/SSM key indicators
in config metadata override a standard-looking family name. Custom-code
configs (`auto_map`) are recorded as partial without executing anything.

## Provenance

Every critical field records value, source tier, resolved revision,
retrieval time, evidence class, inference method when calculated, and
conflict state. Unknown stays unknown and never becomes zero.

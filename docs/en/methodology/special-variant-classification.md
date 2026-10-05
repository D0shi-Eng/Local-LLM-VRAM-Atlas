# Special Variant Classification (Phase 4)

> Evidence-backed. No quality claims. Uncensored ≠ better.

## High compression

Structured evidence only: effective BPW, quant family, native low-bit
architecture, verified/source-reported format. Ordinary post-training
quantization stays distinct from native low-bit and ternary-native.
See `src/atlas/catalog/special.py`.

## Native low-bit

Requires training-architecture evidence (e.g. BitNet 1.58-bit
source-reported architecture). A 1-2bit post-training quant is never
labeled native.

## Ternary

Three separate concepts: `ternary-native`, post-training ternarization,
`TQ` format. Repo-name "Ternary" alone is not evidence.

## Uncensored / abliterated / heretic

Recorded as `variant_author_claim` with author, base model, method (or
"method undocumented"), and verification status. Capability retention and
refusal behavior require independent evidence deferred to later phases.
Popularity (likes/downloads) is never quality.

## Related

- `uncensored-classification.md`, `quantization-methodology.md`
- `evidence-confidence-methodology.md`

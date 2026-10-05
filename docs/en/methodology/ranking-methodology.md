# Ranking Methodology (Specification)

> Arabic counterpart: `docs/ar/methodology/ranking-methodology.md`

## Status

Specification only. Phase 0 implements no Atlas Score, no ranking, and no
"best model per VRAM" answer. Numeric weights are deliberately left undecided.

## Future inputs

A future score may consider intelligence, capability retention after
quantization, VRAM efficiency, runtime maturity, openness and license clarity,
context and features, multilingual and Arabic capability, and community adoption.
Each input must be measured or evidenced under this project's policies before it
can influence any score.

## Constraints

- Downloads and likes remain popularity factors only, never intelligence evidence.
- Publisher claims never enter the score as independent facts.
- Scores from different configurations are never averaged without a published method.
- `verified` (data documented/tested per policy) and `recommended` (quality and
  usage gates additionally passed) stay distinct: a model can be verified without
  being recommended.
- No final numeric weights are fixed without a dedicated study. Any weight
  introduced later must be published with its rationale and versioned with the
  specification.

## Lifecycle

Records carry `active`, `superseded`, `deprecated`, `withdrawn`, `unsafe`, or
`unavailable`, each with a stated reason. History and provenance are preserved;
deprecated entries are annotated, not silently erased.

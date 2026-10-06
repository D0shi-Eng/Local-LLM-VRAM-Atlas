# Recommendation Eligibility Methodology

Recommendation readiness builds a defensible state, not a winner. A strict
recommendation requires every domain to hold simultaneously.

## Required domains

| Domain | Required for strict eligibility |
|---|---|
| `quality` | `known` |
| `vram_fit` | `estimated_fit` |
| `runtime` | `documented` |
| `license` | `permissive` or `restricted` (with disclosure) |
| `variant_identity` | `exact` |
| `evidence_quality` | `complete` |

A strong model that cannot be proven to fit the tier does not become a strict
tier recommendation.

## Categories are never merged

| Category | Meaning |
|---|---|
| `eligible` | All declared domains satisfied (strict list) |
| `candidate` | Quality known but fit indeterminate, or fit known but quality unevaluated |
| `insufficient_evidence` | One or more domains unresolved |
| `ineligible` | Estimated not-fit for the tier |

The CLI reports these counts separately and says `Strict recommendations: 0`
when that is the truth. Weak candidates are never substituted for a strict
result.

## No false strict fit

If VRAM state is `insufficient_evidence`, `unsupported` or
`indeterminate_fit`, the model is not presented as "strictly fits 8GB". The
Existing classifier semantics are not weakened: every VRAM state
here is the existing estimate state, carried through unchanged.

Current catalog outcome: all 34 records classify as `insufficient_evidence`
(23) or `unsupported` (11) across all four tiers, because no record has a
trustworthy VRAM upper bound. Therefore strict recommendations are **0** at
4GB, 8GB, 12GB and 16GB. This is reported honestly rather than engineered away.

## External VRAM evidence

Atlas performs no measurement. Published external measurements may enrich a
record, and stronger provenance is preferred: official runtime measurement,
then independent reproducible measurement, then publisher measurement with full
conditions. Community anecdote is weakest. A bare claim such as "needs 7GB"
without model, revision, quant, runtime, backend, context, batch, KV format,
offload mode and stage is weak evidence.

`atlas_measured` is never overloaded with external data: no Atlas measurement
is preserved, and external evidence keeps its own origin label.

## License handling

A model with an unresolved or restrictive license stays in the catalog, and
the recommendation exposes the restriction explicitly. Custom restrictions are
never hidden. `unclear` and `proprietary` never qualify for strict
recommendation.

## Runtime handling

An unknown runtime cannot be a practical runtime recommendation. Such a model
remains a quality candidate with a runtime-evidence limitation.

## Quantization handling

If exact quant retention is unknown, the recommendation discloses "base quality
known / quant retention unknown" and the confidence category reflects it. An
alignment variant with no exact evidence is listed separately as unevaluated.

## Confidence is categorical

Confidence uses documented categories — `high_evidence`, `moderate_evidence`,
`limited_evidence`, `insufficient` — never invented probabilities such as
"93% confidence", which would require a calibrated model Atlas does not have.

## Ranking rules

Models are ranked against each other only when every compared entry satisfies
the declared policy. A strict evidence-backed entry is never ranked against an
unevaluated entry as if both had equal evidence.

## No bias, no hidden override

Recommendation order derives from policy and evidence only. Publisher brand,
quantizer reputation, popularity, parameter count, release recency and
alignment status carry no weight. No manual override exists; no preferred model
name is hard-coded anywhere.

## Determinism

Policy id and version are recorded on every result. The same catalog snapshot,
the same quality evidence snapshot and the same policy yield identical
recommendations.
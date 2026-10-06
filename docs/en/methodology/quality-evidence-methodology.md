# Quality Evidence Methodology

Atlas records quality as **evidence with an origin**, never as a number without
provenance. A quality claim exists only when a benchmark result, an identified
model release, an evaluation origin and a resolvable evidence record are all
present.

## Evidence source hierarchy

| Tier | Meaning | Weight in policy |
|---|---|---|
| `q1_independent_standardized` | Independent standardized evaluation under a published methodology | Eligible for recommendations |
| `q2_independent_academic` | Peer-reviewed or independently reproducible evaluation | Eligible |
| `q3_verified_community_with_logs` | Structured result with methodology and model identity plus logs | Eligible with disclosure |
| `q4_publisher` | Official model card or paper from the model creator | Context; never sufficient alone |
| `q5_community_anecdotal` | Unstructured community statement | Display-only |

Popularity is deliberately **outside** this hierarchy. Downloads, likes,
trending status, repository stars, publisher fame, release recency, parameter
count and quant-file counts are metadata. They never influence a quality axis,
a quality band or a recommendation order.

## Quality evidence status

Every model resolves to one status:

- `independent_multi_source` — two or more distinct independent sources
- `independent_single_source` — one independent source
- `verified_single_source` — a verified but single-run source
- `publisher_only` — publisher-reported results only
- `community_only` — community-reported results only
- `insufficient` / `unknown` — nothing defensible

Independence is counted by **original evaluation runs**, never by URLs. Two
websites republishing one publisher run remain a single publisher claim.

## Missing evidence is unknown, not zero

A missing benchmark is an **unevaluated** axis. It is never a failed benchmark
and never averaged as `0`. An unevaluated axis is reported as `unknown`, which
is a first-class state in every profile and every recommendation result.

## Evidence completeness

Every new quality claim requires a **persisted, schema-valid evidence record**.
Logical-only references are forbidden for quality evidence. Historical
references that cannot be reconstructed deterministically from data Atlas
already stores are recorded as `evidence_sidecar_unavailable`, an explicit
limitation, rather than a fabricated sidecar.

## Refusal behaviour is not intelligence

Refusal-rate reduction is a separate capability axis
(`safety_refusal_behavior`). Lower refusal never converts into higher
intelligence, and never raises a general-capability axis.

## Terminology domains stay separate

A source's own vocabulary is never copied into Atlas taxonomy. For example,
Artificial Analysis uses "open source" broadly for downloadable open-weight
models; that wording never alters Atlas openness classification, which follows
the Open Source AI Definition and the recorded license.

## Arabic quality

Arabic quality stays `unknown` unless an external Arabic-specific evaluation
with documented methodology exists. "Multilingual" support is never accepted as
evidence of Arabic quality. No credible Arabic-specific source with stable
public results was identified at the reference date, so the axis remains
unevaluated for the whole catalog.

## What Atlas does not do

Atlas ingests published results. It never downloads a model, runs a benchmark,
loads a tokenizer bundle through model-runtime APIs, or converts a base-model
score into a quantized artifact's score.
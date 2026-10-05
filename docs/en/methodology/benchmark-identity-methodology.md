# Benchmark Identity Methodology (Phase 6)

A benchmark score is meaningless without an exact evaluated identity. Atlas
attaches a result to a record only when publisher, repository, revision,
release, variant, reasoning mode and quantization all resolve.

## Match statuses

| Status | Meaning | Counted as exact evidence |
|---|---|---|
| `exact` | Repo identity **and** revision both resolve | Yes |
| `exact_repo_revision_unresolved` | Repo resolves; a revision is missing on one side | Yes, with disclosure |
| `ambiguous` | Identity cannot be resolved, or revisions disagree | **No** |
| `identity_conflict` | Sources disagree about what was evaluated | **No**, excluded from ranking |

Unstated revisions are never assumed equal to a known revision. A resolvable
repository with an unstated revision is still usable evidence, but it carries
`exact_repo_revision_unresolved` so the limitation is visible.

## Aliases are controlled, never fuzzy

Display-name variants, organization naming differences and provider aliases may
map to a canonical identity only through an explicit, declared mapping that
records its source and confidence. Atlas does not fuzzy-match arbitrary model
names and never declares two names identical because they look similar.

## Base, instruct, reasoning and fine-tunes are separate releases

Results never transfer automatically between base, instruct, chat, reasoning or
fine-tuned artifacts. A base-model result is refused for an instruct record when
explicit release markers contradict (for example `Base` versus `-Instruct`).

## Base model versus quantized artifact

A benchmark score for a base model is **not** a score for a quantized variant.
Quantization can change accuracy, reasoning, coding, instruction following and
long-context behaviour, so each requires its own evidence. The base score may
be displayed as `base_model_quality_context`, while the quantized artifact's own
retention remains `unknown` until comparable evidence exists.

## Alignment variants are separate evaluated artifacts

Uncensored, abliterated and heretic variants do not inherit the parent's
quality results as exact scores. The parent score may be shown as
`parent_reference_only`. To rank or recommend such a variant on quality, exact
variant evidence is required; otherwise `quality_status` is `unevaluated`.

## Native low-bit and ternary releases

Native low-bit models may have benchmark results published on the native
release itself. Those results represent that release when identity is clear,
and they are never compared against post-training quantization as if the method
were identical. Native ternary, trained ternary, post-training ternarization
and TQ-format artifacts remain separate; a repository name alone is never
sufficient evidence.

## Revision drift

When a result applies to revision A while the catalog's active revision is B,
Atlas does not transfer it. It is marked `historical_revision_evidence` unless
equivalence is proven.
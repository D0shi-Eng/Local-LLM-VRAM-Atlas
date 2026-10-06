# Quality Profiles Methodology

A quality profile is a **multi-axis** view of one model release, built
deterministically from canonical evaluation records. Atlas does not create a
single magic quality score.

## Why no single score

One combined number hides which capability was measured, which benchmark
produced it, and whether the evidence is independent. A single score would also
imply comparability across axes that do not have it. Axis values stay
separate and traceable instead.

## Declared axes

| Axis | Populated by (examples) |
|---|---|
| `general_intelligence` | MMLU, ARC, HellaSwag, PIQA, Winogrande |
| `reasoning` | GPQA, AIME, MATH-500, BBH, GSM8K |
| `coding` | HumanEval, MBPP, LiveCodeBench, Codeforces, Aider |
| `agentic_tool_use` | τ-bench, Terminal-Bench, SWE-bench |
| `instruction_following` | IFEval, MT-Bench, IFBench |
| `knowledge` | MMLU, TriviaQA, SimpleQA |
| `long_context` | AA-LCR, MLCR-AA, dedicated long-context suites |
| `multilingual` | Global-MMLU-Lite, MGSM, C-Eval |
| `arabic` | Arabic-specific evaluations only |
| `multimodal` | MMMU-Pro |
| `non_hallucination` | SimpleQA, faithfulness suites |
| `safety_refusal_behavior` | Refusal-specific evaluations only |
| `professional_tasks` | Professionally graded task suites |

An axis is emitted only for benchmarks with an explicit mapping in the policy
code. Axis assignment never falls back to popularity, size or repository name.
Every axis always exists in the profile; when no evidence exists its status is
`unknown`, never `0`.

## Capability support is not capability performance

`tool_calling_supported = true` is metadata. Agentic **performance** requires
an agentic evaluation. Likewise advertised context length is not long-context
performance, and generic benchmark performance is never presented as lower
hallucination without a hallucination-specific evaluation.

## Determinism

A profile identifier is a digest over the model id, the sorted set of exact
evaluation ids and the policy version. No timestamp enters profile identity, so
the same evidence snapshot always yields the same profile.

## Evidence status

Each profile carries one evidence status derived from the origins of its exact
evaluations: `independent_multi_source`, `independent_single_source`,
`verified_single_source`, `publisher_only`, `community_only`, `insufficient`,
`unknown`.

## `high_quality_candidate` is policy-defined

The flag is **not** a quality band and never means popular, large, new or
official. Eligibility requires exact-match evaluation evidence, at least one
axis with defensible evidence, an independent evidence status, no unresolved
identity conflict and no superseded evidence. Every decision carries a written
rationale. Current catalog outcome: no model qualifies, because every recorded
result is publisher-reported.

## Source disagreement

When two sources report different values for the same model, benchmark, version
and metric, the profile exposes the disagreement as an axis note. Results are
never cherry-picked to the highest value.

## No quality bands

Letter or numeric quality bands are deliberately **not** implemented. Defensible
bands require a populated cross-source population, which the current catalog
does not have. Same-benchmark ranking remains available. This refusal is
recorded in the quality-band policy with its rationale.
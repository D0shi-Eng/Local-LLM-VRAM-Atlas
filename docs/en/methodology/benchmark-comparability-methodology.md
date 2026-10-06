# Benchmark Comparability Methodology

Two scores may be compared only when everything that can change the number is
identical. Anything unknown blocks the comparison instead of being assumed
equal.

## The comparable-setting key

| Field | Why it matters |
|---|---|
| `benchmark_id` | Different tasks are different measurements |
| `benchmark_version` | Task content, prompt or scoring changes between versions |
| `metric` | `pass@1`, `cons@64` and accuracy are distinct metrics |
| `score_unit` | Percent, Elo rating, F1 points and judge scores are not comparable |
| `reasoning_mode` | Thinking and non-thinking runs differ materially |
| `tool_mode` | Tool availability changes agentic and coding results |
| `prompting_mode` | Zero-shot and few-shot are different setups |
| `context_configuration` | Context length changes long-context behaviour |

A benchmark v1 score is never compared directly with a v2 score unless the
source methodology explicitly permits it.

## Metric semantics are preserved

Direction is explicit (`higher_is_better` / `lower_is_better`); Atlas never
assumes higher is better. Raw source score and metric are always preserved. A
normalized score, when one exists, is stored alongside `raw_score`,
`raw_metric`, `normalization_formula` and `normalization_version` and never
replaces the source value.

Elo is not accuracy: an Elo rating is never compared with a percentage.
`pass@1` and `pass@10` are different metrics and are never merged. Different
harness implementations of "accuracy" are not assumed comparable.

## Same-benchmark ranking

Atlas may rank models inside one exact benchmark + version + mode population,
because scores are comparable under that source's methodology. The raw score,
rank, population size and (when calculated) percentile are all preserved.
A population of one yields no rank: a single result is not a ranking.

## Percentile rules

Percentiles are computed by Atlas and documented as such:

- population = exact comparable setup only;
- ties share the best rank achieved in that population;
- `percentile = (population - rank + 1) / population`, higher is better;
- missing or superseded results are excluded from the population, never counted
  as zero;
- a percentile is never attributed to the source unless that source publishes
  it.

## Cross-benchmark normalization

Raw MMLU accuracy, coding scores, Elo and `pass@k` are never averaged. Different
metrics require an explicit, versioned normalization with documented weights,
direction handling, pinned benchmark versions and explicit missingness
treatment. Where no defensible formula exists, **no aggregate is created** and
the aggregation is recorded as `refused` with its reason.

## Benchmark lineage and double counting

The same underlying run is never counted twice. If one leaderboard includes a
benchmark that another leaderboard also reports, the relationship is recorded as
benchmark lineage rather than treated as two independent results. Independence
counts original evaluation runs, not URLs.

## Supersession

When a benchmark version is superseded, the older record is preserved and
marked `superseded` with `superseded_by` pointing at the newer record. History
is never rewritten and a corrected score becomes a new superseding record.

## Freshness

Wall-clock age alone never invalidates a result. Freshness is expressed through
supersession, harness change and revision drift. The documented freshness policy
declares no arbitrary N-day expiry.
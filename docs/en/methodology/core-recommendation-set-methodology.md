# Core Recommendation Set Methodology

> Arabic counterpart: `docs/ar/methodology/core-recommendation-set-methodology.md`

## Why a bounded set

Deep evidence closure for 34 releases and 201 artifacts is not achievable
without executing models, running benchmarks or crawling. The closure stage therefore
declares a small **Core Recommendation Set** chosen by neutral eligibility
signals, and works only on that set.

## Declared candidates, recomputed signals

Selection is declared data (`src/atlas/closure/core_set.py`) so it is
auditable, and every signal is *recomputed* from canonical catalog records on
each run, so the declaration can never silently drift from the catalog.

Permitted signals:

- relevance to a target VRAM tier (artifact weight footprint against nominal
  tier capacity - a relevance signal, **never** a fit verdict);
- current availability (lifecycle active, revision resolved);
- known local inference format;
- architecture support under Atlas's canonical KV families;
- metadata completeness;
- runtime relevance;
- special low-bit relevance (native low-bit, ternary, high compression);
- adoption as a **discovery signal only**, never quality and never ranking.

Explicitly excluded: brand preference, repository-name prestige, personal
preference, desired final ranking, expected benchmark outcome, popularity as
quality, parameter count as quality, recency as quality.

## Bounded size

Approximately 3-6 candidates per tier with overlap allowed. A release may
appear with two different exact artifacts when that is what the tiers need. The
declared set is 19 exact release/artifact combinations over 16 unique releases.

## Exact artifact identity

Every candidate names one `artifact_set_id` including its variant, its revision
and its source-reported weight bytes. "Qwen 8B" is never a candidate; the
`Qwen3-8B.Q4_K_M.gguf` artifact inside a specific repository revision is.

Candidates that intentionally probe a limitation (an unlabeled GGUF variant, a
model whose declared context is shorter than the Atlas baseline, an
alignment-modified variant with no declared lineage) are declared on purpose so
the limitation is demonstrated in canonical data instead of being hidden.

# Evidence Closure Methodology (Phase 6.5)

> Arabic counterpart: `docs/ar/methodology/evidence-closure-methodology.md`

## Scope

Phase 6.5 closes evidence gaps for a small **Core Recommendation Set** instead
of trying to deeply evaluate all 34 catalog releases. Evidence closure means
one thing only: attaching more *true, traceable, revision-aware* evidence to a
bounded set of exact artifacts so that later phases can judge whether the data
layer is strong enough to publish.

Closure is not a new scoring system. Every formula, policy and classifier is
imported from Phases 0-6 and used unchanged.

## The four readiness states

| State | Meaning |
|---|---|
| `STRICT_READY` | every declared strict gate is satisfied by persisted evidence |
| `CANDIDATE_READY` | useful content with substantial evidence, one or more strict gates still open, and every missing gate listed |
| `CATALOG_ONLY` | legitimate catalog content without enough recommendation evidence |
| `BLOCKED` | a critical identity, license, security, lineage or evidence-integrity problem |

States are never merged, never waived, and never set by hand. There is no
manual override and no popularity, size, parameter-count, brand, recency or
adoption waiver.

## Strict gates

A strict recommendation requires all of these at once:

1. `exact_artifact_identity` - one `artifact_set_id`, never a bare model name;
2. `current_provenance_persisted` - new current evidence exists on disk;
3. `license_status_acceptable` - Phase 6 license domain is permissive or restricted;
4. `runtime_compatibility_documented` - Phase 6 runtime domain is `documented`;
5. `vram_fit_state_strict` - the Phase 2 classifier returns `estimated_fit` for the tier;
6. `independent_multi_source_quality` - at least two *distinct underlying runs*;
7. `no_unresolved_identity_conflict`;
8. `quant_retention_when_post_training_quantized` - direct comparable retention evidence;
9. `no_evidence_fabrication`.

A single missing gate lowers the state. It never raises it.

## Independence is counted per run

Two web pages that republish one evaluation run are **one** source. Phase 6.5
keys independence on
`(evaluator, benchmark, benchmark_version, suite_version, evaluation_date, metric)`
so syndication cannot manufacture multi-source status. A model with exactly one
independent run is reported as `independent_single_source` and stays
non-strict.

## Honest empty results

Zero strict recommendations is a valid outcome. Phase 6.5 records a
`TIER COVERAGE BLOCKER` instead of relaxing a threshold, a classifier state or a
source-class rule to produce a non-zero count.

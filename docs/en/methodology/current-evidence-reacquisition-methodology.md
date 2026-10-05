# Current Evidence Reacquisition Methodology (Phase 6.5)

> Arabic counterpart: `docs/ar/methodology/current-evidence-reacquisition-methodology.md`

## The problem

Phase 1-4 intake wrote nine evidence references per model. By design those
references were logical only, so Phase 5/6 measured **243 references without
persisted sidecars**. Those are not a bug to be deleted: they are the honest
record of what Atlas cannot prove about the past.

## The permanent rule

Historical provenance is never invented. No historical evidence identifier is
regenerated, renamed or backfilled.

Instead, for Core Recommendation Set records only, **current** evidence is
acquired now from public authoritative sources and persisted as new evidence
records with new `ev-v2-` digest identifiers.

## Both facts are preserved

For a Core record the following three statements are simultaneously true and
all three are persisted:

1. Historical sidecars: `evidence_sidecar_unavailable` (unchanged, 243 gaps).
2. Current reacquired evidence: `available` with new revision-aware ids.
3. The two are never merged, and one never stands in for the other.

## How current evidence is acquired

- anonymous public reads only (`token=False`); no credential is read or sent;
- the Phase 3 metadata allowlist is reused unchanged, so only `config.json`
  and index JSON on `huggingface.co` are reachable - no weight payload can be
  fetched by any code path;
- bounded requests and bounded bytes, with the budget declared in code;
- a repository that cannot be read anonymously is recorded as
  `source_unavailable` or `authentication_required` and is never substituted.

## Lineage is declared, never inferred from a name

When a GGUF repository publishes no configuration of its own, architecture
inputs are read from the lineage the **catalog already declares**
(`base_models`, followed transitively for at most two hops) and the derivation
is disclosed as `declared_base_model_config`. A repository whose name suggests a
parent model but declares none stays unresolved. A name is never lineage.

## Revision handling

A branch URL is not an immutable revision. The reacquired revision is recorded
separately from the catalog-recorded revision and their relationship is stated
explicitly (`matches_catalog`, `differs_from_catalog`,
`reacquired_catalog_absent`). Evidence identifiers include the resolved
revision, so two different revisions of the same claim produce two different
identifiers.

## Reference linking is additive

New identifiers are appended to the canonical record's
`verification.evidence_ids`. Nothing is removed or reordered, which keeps the
trace *recommendation -> policy -> profile -> evaluation -> artifact -> runtime
-> VRAM -> license -> source* walkable while the historical gap count stays at
243.

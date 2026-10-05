# Recommendation Readiness Workflow

> Arabic counterpart: [`docs/ar/workflows/recommendation-readiness.md`](../../ar/workflows/recommendation-readiness.md)
>
> Diagrams: English-labelled by design. Bilingual captions are collected in
> [`docs/diagrams/README.md`](../../diagrams/README.md).

## Scope

This document explains how a candidate artifact becomes — or fails to become — a
recommendation for a given VRAM tier, and how the repository reports that
outcome honestly.

## What "readiness" means

The Atlas does not publish a ranked list of "best models". It publishes a
**readiness state** for each candidate at each tier, derived from declared gates.
The state is categorical, and the categories are never merged.

| State | Meaning |
|---|---|
| `STRICT_READY` | Every declared strict gate is satisfied by persisted, walkable evidence. |
| `CANDIDATE_READY` | Substantial evidence, useful content, one or more strict gates still open, and every missing gate named. |
| `CATALOG_ONLY` | Legitimate catalog content without enough recommendation evidence. |
| `BLOCKED` | A critical identity, licence, runtime, lineage or evidence-integrity problem. |

## Figure 7 — Recommendation decision flow

```mermaid
flowchart TB
  classDef gate fill:#2A2416,stroke:#E8B45A,color:#F3E3C2
  classDef state fill:#0F1620,stroke:#7FA8C9,color:#DCE7F1
  classDef out fill:#14202C,stroke:#8FB8D8,color:#DCE7F1
  classDef stop fill:#2B1418,stroke:#C97B7B,color:#F0DADA

  CAND(["Core candidate<br/>model_id + artifact_set_id + revision + target tiers"]) --> G1

  G1{"1. exact_artifact_identity<br/>one artifact_set_id, not a bare name"}
  G1 -->|"fail"| BLK
  G2{"2. current_provenance_persisted<br/>new current evidence on disk"}
  G2 -->|"fail"| LOW
  G3{"3. license_status_acceptable<br/>permissive or restricted"}
  G3 -->|"fail"| BLK
  G4{"4. runtime_compatibility_documented<br/>runtime_status = documented"}
  G4 -->|"fail"| LOW
  G5{"5. vram_fit_state_strict<br/>classifier returns estimated_fit"}
  G5 -->|"fail"| LOW
  G6{"6. independent_multi_source_quality<br/>two or more distinct runs"}
  G6 -->|"fail"| LOW
  G7{"7. no_unresolved_identity_conflict"}
  G7 -->|"fail"| BLK
  G8{"8. quant_retention_when_post_training_quantized<br/>direct comparable evidence"}
  G8 -->|"fail"| LOW
  G9{"9. no_evidence_fabrication"}
  G9 -->|"fail"| BLK

  G9 -->|"pass"| STRICT["STRICT_READY<br/>all gates satisfied"]
  LOW["State lowered by the missing gate<br/>every missing gate is named"] --> CANDID
  CANDID["CANDIDATE_READY"]
  CATONLY["CATALOG_ONLY<br/>content is valid, recommendation evidence is not"]
  BLK["BLOCKED<br/>identity, licence or integrity problem"]

  LOW -->|"no usable content value"| CATONLY
  CATONLY --> REPORT

  STRICT --> REPORT
  CANDID --> REPORT
  CATONLY --> REPORT
  BLK --> REPORT

  REPORT["recommendation-result record<br/>per tier: eligibility, confidence_state,<br/>domain states, reasons"]
  REPORT --> AGG["Tier aggregation<br/>strict / candidate / insufficient / ineligible<br/>categories never merged"]
  AGG --> VIEWS["Bilingual views<br/>tier readiness and evidence-gap matrices"]
  AGG --> CLI["CLI: recommend tier --tier N<br/>recommend model <model_id>"]

  class G1,G2,G3,G4,G5,G6,G7,G8,G9 gate
  class STRICT,CANDID,CATONLY,LOW state
  class REPORT,AGG,VIEWS,CLI out
  class BLK stop
```

## Gate semantics

| Gate | Failure effect | Why it exists |
|---|---|---|
| `exact_artifact_identity` | `BLOCKED` | A score or size attached to "a model" cannot be attributed to a specific file. |
| `current_provenance_persisted` | state lowered | A record that no longer describes upstream must not be published as current. |
| `license_status_acceptable` | `BLOCKED` | An unclear or unacceptable licence is a governance problem, not an evidence gap. |
| `runtime_compatibility_documented` | state lowered | An artifact nobody has documented running is not a recommendation. |
| `vram_fit_state_strict` | state lowered | Without a reliable bound, "fits" is a guess. |
| `independent_multi_source_quality` | state lowered | One publisher table is not an independent quality assessment. |
| `no_unresolved_identity_conflict` | `BLOCKED` | A contradictory identity makes every derived number untrustworthy. |
| `quant_retention_when_post_training_quantized` | state lowered | Quantization can cost quality; that cost must be measured, not assumed. |
| `no_evidence_fabrication` | `BLOCKED` | The one gate that can never be waived. |

**A single missing gate lowers a state. It never raises one.**

## Hard rules

1. No policy threshold, classifier state or source-class rule is relaxed to
   produce a non-zero count.
2. No manual override exists, and there is no waiver by popularity, brand,
   recency, size or parameter count.
3. States are never merged, never waived and never set by hand.
4. Zero strict recommendations is a valid, publishable outcome.
5. Where a strict recommendation is absent, the repository says so and names the
   blocking gate.

## Signals that can never raise a state

```
downloads · likes · trending · parameter_count · artifact_byte_size
publisher_brand · release_recency · adoption
```

Popularity is recorded as a popularity signal and nothing else. It is never
converted into a quality benchmark, and it never contributes to eligibility.

## Current reported position

The repository reports **zero `STRICT_READY` candidates at 4, 8, 12 and 16 GB**.
The dominant blocking gates are `independent_multi_source_quality` and
`vram_fit_state_strict`, followed by
`quant_retention_when_post_training_quantized`.

This is not an unfinished state that a later release will quietly correct. It is
the current, evidence-backed answer, and the Atlas prefers it to a fabricated
non-zero count. Regenerate the live figures with:

```bash
python -m atlas.cli.main recommend tier --tier 8
python -m atlas.cli.main closure readiness
```

## Further reading

- [Recommendation eligibility methodology](../methodology/recommendation-eligibility-methodology.md)
- [Evidence closure methodology](../methodology/evidence-closure-methodology.md)
- [Evidence gaps methodology](../methodology/evidence-gaps-methodology.md)
- [Quality profiles methodology](../methodology/quality-profiles-methodology.md)
- [Publication readiness data policy](../methodology/publication-readiness-data-policy.md)
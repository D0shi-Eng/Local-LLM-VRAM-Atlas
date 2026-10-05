# Refresh and Evidence Ingestion Workflows

> Arabic counterpart: [`docs/ar/workflows/refresh-and-evidence-ingestion.md`](../../ar/workflows/refresh-and-evidence-ingestion.md)
>
> Diagrams: English-labelled by design. Bilingual captions are collected in
> [`docs/diagrams/README.md`](../../diagrams/README.md).

## Scope

This document covers the workflows that bring external reality into the Atlas:

1. **Source discovery and controlled intake**
2. **Architecture, memory and quantization analysis**
3. **Quality evidence ingestion**
4. **Retention and VRAM evidence flow**

Every workflow in this document is **bounded, anonymous, read-only with respect
to upstream**, and **dry-run by default** with respect to the local catalog.

---

## Workflow A — Source discovery and controlled intake

### Figure 3 — Discovery to canonical record

```mermaid
flowchart TB
  classDef gate fill:#2A2416,stroke:#E8B45A,color:#F3E3C2
  classDef step fill:#0F1620,stroke:#7FA8C9,color:#DCE7F1
  classDef data fill:#14202C,stroke:#8FB8D8,color:#DCE7F1
  classDef stop fill:#2B1418,stroke:#C97B7B,color:#F0DADA

  START(["Discovery request<br/>publisher or namespace pass"]) --> GUARD1{"URL and weight guard<br/>scheme, host, path"}
  GUARD1 -->|"refused"| STOP1["Record the refusal.<br/>No request is made."]
  GUARD1 -->|"allowed"| FETCH["Anonymous public read<br/>model_info, config, file list"]

  FETCH --> NORM["Normalize declared metadata<br/>parameters, licence, context,<br/>architecture, tags"]
  FETCH --> TREE["Group sibling files<br/>shards and companion components"]

  NORM --> CLASSIFY["Identity and licence classification<br/>openness, SPDX, lineage"]
  TREE --> CLASSIFY

  CLASSIFY --> SCHEMA{"Validate against<br/>JSON Schema"}
  SCHEMA -->|"invalid"| STOP2["Persist the validation error.<br/>Write nothing."]
  SCHEMA -->|"valid"| PROV["Attach provenance<br/>resolved revision, source, access method"]

  PROV --> EVID["Emit evidence records<br/>one field, one value, one level"]
  PROV --> PLAN(["Candidate change plan"])

  PLAN --> APPLY{"Explicit --apply?"}
  APPLY -->|"no"| DRY["Dry run complete.<br/>Canonical state unchanged."]
  APPLY -->|"yes"| WRITE["Transactional write<br/>catalog/models, catalog/artifacts,<br/>catalog/sources, catalog/evidence"]
  WRITE --> JOURNAL["Append change events<br/>catalog/changes journal"]

  class GUARD1,SCHEMA,APPLY gate
  class FETCH,NORM,TREE,CLASSIFY,PROV,EVID,WRITE,JOURNAL step
  class PLAN,DRY data
  class STOP1,STOP2 stop
```

### Rules

- A refused URL produces a **recorded refusal**, not an exception and not a
  silent skip. The absence of a refusal record would make a bounded search
  indistinguishable from an unfinished one.
- No credentials are read, stored or transmitted at any point.
- Weight-payload URLs are refused **before** a network request is made.
- Redirects are not followed.
- The canonical catalog is never modified without an explicit `--apply`.

---

## Workflow B — Architecture, memory and quantization analysis

### Figure 4 — From declared metadata to a memory range

```mermaid
flowchart LR
  classDef in fill:#12212F,stroke:#3E7CB1,color:#DCE7F1
  classDef calc fill:#0F1620,stroke:#7FA8C9,color:#DCE7F1
  classDef out fill:#14202C,stroke:#8FB8D8,color:#DCE7F1
  classDef guard fill:#2A2416,stroke:#E8B45A,color:#F3E3C2

  subgraph DECLARED["Declared inputs"]
    P["total_parameters_b"]
    AID["artifact_set_id<br/>declared byte total"]
    QN["quantization<br/>family and label"]
    CFG["config.json<br/>layers, kv heads, head dim,<br/>max position embeddings"]
  end

  subgraph RESOLVE["Architecture resolution"]
    FAM["Resolve architecture family"]
    SHAPE{"Are layers, kv_heads and<br/>head_dim all resolved?"}
    PLAN["Build canonical layer plan"]
  end

  subgraph BYTES["Byte arithmetic"]
    WB["Weight bytes<br/>from artifact size or params x bpw"]
    KVB["KV bytes per token<br/>2 x layers x kv_heads x head_dim x dtype"]
    KVT["KV bytes at context<br/>per-token rate x context x sequences"]
    SO["Static overhead"]
    DO["Dynamic overhead"]
  end

  subgraph RANGE["Range and classification"]
    LO["Lower bound"]
    HI["Upper bound"]
    CLASS{"Classify against<br/>4 / 8 / 12 / 16 GB"}
  end

  RES["memory-estimate record<br/>range, calculation profile,<br/>evidence status"]
  VERDICT["tier verdict per capacity<br/>estimated_fit | estimated_not_fit |<br/>insufficient_evidence | unsupported"]

  P --> WB
  QN --> WB
  AID --> WB
  CFG --> FAM --> SHAPE
  SHAPE -->|"incomplete"| PLAN
  PLAN -->|"unresolved dimensions"| GAP["Record the missing dimension.<br/>KV bytes stay absent."]
  SHAPE -->|"complete"| KVB
  PLAN --> KVB

  KVB --> KVT
  WB --> LO
  KVT --> LO
  SO --> LO
  LO --> HI
  DO -->|"published bound exists"| HI
  DO -->|"no published bound"| NOHI["Upper bound stays absent.<br/>No constant is invented."]
  NOHI --> HI

  LO --> CLASS
  HI --> CLASS
  GAP --> RES
  CLASS --> RES --> VERDICT

  class P,AID,QN,CFG in
  class FAM,SHAPE,PLAN,WB,KVB,KVT,SO,DO,LO,HI,CLASS calc
  class RES,VERDICT out
  class GAP,NOHI guard
```

### Rules

- **A range is not a verdict.** The classifier consumes a range plus an evidence
  state, and emits a tier verdict that may legitimately be
  `insufficient_evidence`.
- **A missing dimension stays missing.** If `num_key_value_heads` is unresolved,
  KV bytes are absent, not zero.
- **No invented overhead constant.** If the runtime publishes no static or
  dynamic GPU-memory overhead bound, the upper bound stays absent and no number
  is substituted. This single rule is why the Atlas currently reports zero
  strict tier fits, and it is a deliberate outcome rather than a gap to be
  papered over.
- **File size is not VRAM usage.** Weight bytes are one term in the range, not
  the answer.

---

## Workflow C — Quality evidence ingestion

### Figure 5 — From a published result to a quality axis

```mermaid
flowchart TB
  classDef gate fill:#2A2416,stroke:#E8B45A,color:#F3E3C2
  classDef step fill:#0F1620,stroke:#7FA8C9,color:#DCE7F1
  classDef data fill:#14202C,stroke:#8FB8D8,color:#DCE7F1
  classDef stop fill:#2B1418,stroke:#C97B7B,color:#F0DADA

  FOUND["Published evaluation result<br/>table, dataset card or transcription"] --> ORIGIN{"What is the origin?"}

  ORIGIN -->|"publisher or community"| PUBONLY["Record as publisher_or_community_only.<br/>Never as independent."]
  ORIGIN -->|"independent standardised"| IND["Candidate independent result"]

  IND --> IDENT{"Exact artifact identity?<br/>artifact_id + revision"}
  IDENT -->|"artifact absent, only the model is named"| BASE["Attach to the base release only.<br/>match_status = base_only"]
  IDENT -->|"artifact matches"| EXACT["Exact match accepted"]

  BASE --> PROFILE
  EXACT --> PROFILE
  PUBONLY --> PROFILE

  PROFILE["Quality profile per model<br/>axes: general, coding, reasoning,<br/>agentic tool use, long context,<br/>multilingual, Arabic"] --> STATUS{"Axis state"}
  STATUS -->|"at least one exact result"| KNOWN["status = known"]
  STATUS -->|"partial identity or partial coverage"| PART["status = partially_known"]
  STATUS -->|"no usable result"| UNK["status = unknown"]

  KNOWN --> SUMMARY["Profile summary<br/>evidence_status, candidate flag,<br/>written rationale"]
  PART --> SUMMARY
  UNK --> SUMMARY

  SUMMARY --> GAPS["Gap report<br/>which models lack which domain"]
  GAPS --> VIEWS["Bilingual generated views<br/>catalog/views/quality"]

  class ORIGIN,IDENT,STATUS gate
  class PUBONLY,IND,BASE,EXACT,PROFILE,KNOWN,PART,UNK,SUMMARY,GAPS,VIEWS step
  class FOUND data
  class STOP stop
```

### Rules

- **The base release's score is never transferred to a quantized derivative.** A
  post-training-quantized artifact with no exact result is `unevaluated`, not
  "approximately as good as the base".
- **An alignment-modified variant never inherits its parent's score.**
- **Publisher evidence is recorded, and labelled as publisher evidence.** It can
  never satisfy the independent-multi-source gate.
- **A multilingual claim is not Arabic evidence.** The Arabic quality axis stays
  `unknown` until an Arabic-specific result exists. See
  [`quality-evidence-methodology.md`](../methodology/quality-evidence-methodology.md).
- **Independence is counted per run**, keyed on evaluator, benchmark, benchmark
  version, suite version, evaluation date and metric, so that two pages
  republishing one run cannot manufacture multi-source status.

---

## Workflow D — Retention and VRAM evidence flow

### Figure 6 — Two evidence paths that must not be confused

```mermaid
flowchart LR
  classDef base fill:#12212F,stroke:#3E7CB1,color:#DCE7F1
  classDef path fill:#0F1620,stroke:#7FA8C9,color:#DCE7F1
  classDef res fill:#14202C,stroke:#8FB8D8,color:#DCE7F1
  classDef guard fill:#2A2416,stroke:#E8B45A,color:#F3E3C2

  subgraph QPATH["Quantization retention path - 'is it still as good?'"]
    BR["Base release result<br/>exact harness identity"]
    QR2["Quantized artifact result<br/>same benchmark, same suite version,<br/>same settings"]
    CMP["Compare only when every<br/>comparable-setting key matches"]
    DELTA["Quant-retention record<br/>absolute and relative delta,<br/>retention_status"]
    BR --> CMP
    QR2 --> CMP
    CMP -->|"keys match"| DELTA
    CMP -->|"any key differs"| NOCMP["No comparison.<br/>retention_status = insufficient_evidence"]
  end

  subgraph VPATH["VRAM evidence path - 'does it fit?'"]
    ARCHQ["Resolved architecture<br/>layers, kv heads, head dim"]
    CTX["Context and sequence count"]
    KVRATE["Documented KV rate<br/>publisher or runtime documentation"]
    CALC["Weight bytes + KV bytes<br/>+ overhead if published"]
    MREQ["Memory requirement record"]
    FIT{"Tier capacity comparison"}
    STATE["Tier verdict<br/>estimated_fit | estimated_not_fit |<br/>insufficient_evidence | unsupported"]
    ARCHQ --> CALC
    CTX --> CALC
    KVRATE --> CALC
    CALC --> MREQ --> FIT --> STATE
  end

  SCOPE["Scope limits are attached, never dropped"] -.-> MREQ
  SCOPE -.-> DELTA

  GUARD["A measurement on hardware larger than the tier<br/>is memory-requirement evidence,<br/>NOT hardware verification on that tier"] -.-> STATE

  class BR,QR2,ARCHQ,CTX,KVRATE base
  class CMP,CALC,MREQ,FIT path
  class DELTA,STATE res
  class NOCMP,SCOPE,GUARD guard
```

### Rules

- **Retention and fit are different questions.** Retention asks whether
  quantization degraded quality. Fit asks whether the artifact runs on a given
  capacity. Neither answer implies the other.
- **Comparability is all-or-nothing.** If any comparable-setting key differs, no
  delta is computed and the record says so.
- **A scope limit travels with the record.** A measurement taken at a
  100 000-token context is not a baseline-context fit measurement, and the record
  says exactly that.
- **Hardware is not substituted for capacity.** A measurement taken on hardware
  larger than the target tier is evidence about memory requirements, not
  verification that the artifact runs on the smaller tier.

---

## Running these workflows

Every workflow above is exposed through one CLI, dry-run by default:

```bash
python -m atlas.cli.main discover candidates          # controlled discovery passes
python -m atlas.cli.main discover delta              # bounded incremental discovery
python -m atlas.cli.main refresh plan                # dry-run plan
python -m atlas.cli.main refresh status              # checkpoints, queue, journal
python -m atlas.cli.main refresh apply --plan <file> # transactional apply
python -m atlas.cli.main quality sources --check     # quality source registry
python -m atlas.cli.main quality gaps                # missing evidence domains
python -m atlas.cli.main retention show <model_id>   # quantization retention
python -m atlas.cli.main closure evidence            # current provenance reacquisition
python -m atlas.cli.main closure vram                # tier fit states
python -m atlas.cli.main closure readiness           # publication readiness
```

### Exit-code contract

The refresh surface uses a documented exit-code contract so a caller can
distinguish "nothing to do" from "something needs a human".

| Code | Meaning |
|---|---|
| `0` | Success: no changes, or informational only. |
| `10` | Changes found: the plan contains operations. **This is the expected result of a successful planning run, not an error.** |
| `11` | Review required: critical or high-impact changes are pending. |
| `12` | Partial run: request budget exhausted, state persisted. |
| `13` | External source failure; checkpoints preserved. |
| `14` | Stale plan refused: the catalog moved since the plan was built. |
| `15` | Transaction failure; the change was rolled back. |
| `16` | Recovery required: an incomplete transaction marker was found. |
| `17` | Security block: unsafe URL, weight payload or authentication attempt. |
| `18` | Invalid input: bad arguments, schema failure or unreadable plan file. |

Because `10` is a success signal, scripts should test for `0` **or** `10` when
they only need to know that planning succeeded.

## Further reading

- [Transactional refresh methodology](../methodology/transactional-refresh.md)
- [Refresh planning](../methodology/refresh-planning.md)
- [Quantization retention methodology](../methodology/quantization-retention-methodology.md)
- [VRAM methodology](../methodology/vram-methodology.md)
- [Benchmark comparability methodology](../methodology/benchmark-comparability-methodology.md)
- [Metadata fetch security](../methodology/metadata-fetch-security.md)
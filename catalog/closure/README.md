# Evidence Closure

> Arabic counterpart: [`README_AR.md`](README_AR.md)

## What "closure" means here

**Closure is a domain term, not a development-phase label.** In this project it
names one specific engineering activity:

> Attaching more *true, traceable, revision-aware* evidence to a bounded set of
> exact artifacts, so that readiness can be judged on evidence rather than on
> assumption.

It is the same word used in *closure of a defect*, *closure of an evidence gap*,
or *topological closure*: bringing a bounded set to a decided state, and being
explicit about what remains undecided.

**Closure is not the same thing as completion.** A closed artifact is one whose
evidence question has been answered. An artifact can be closed and still be
`CATALOG_ONLY`. Nothing in this directory claims a recommendation exists.

## Why the directory exists

Closure exists because answering "can I run this on a 4GB card?" requires joining
five separate domains that are each independently incomplete:

1. **exact artifact identity** — which file, at which revision
2. **current provenance** — does the record still describe upstream reality
3. **architecture** — are the tensor dimensions resolved well enough to compute
   anything
4. **independent quality** — is there a measured result for this exact artifact
5. **quantization retention** — what did quantization cost, under a comparable harness

No single subsystem owns all five. Closure is where they are joined, once,
under one declared policy, and where the joined answer is recorded.

## Contents

| Path | Contents |
|---|---|
| `core-recommendation-set.json` | The Core Recommendation Set: 19 bounded candidates with their declared target tiers, plus the selection signals that were deliberately **excluded** |
| `readiness.json` | Publication readiness per candidate, per tier: four states, nine strict gates, every missing gate named |
| `quant-retention-closure.json` | Quantization retention per Core candidate, computed only where the comparable-setting key matches |
| `vram/` | One VRAM evidence record per Core candidate, per tier, with scope limits attached |
| `current-evidence/index.json` | Reacquired current-provenance evidence for Core records |
| `external/` | Normalized external evidence: source outcomes, measurement index, retention, identity findings, runtime-overhead finding, and the machine-readable evidence conditions |

## The policy contract

`readiness.json` carries the policy as data, not as code:

```text
policy_id:   atlas-closure-readiness
policy_kind: publication_readiness
states:      STRICT_READY, CANDIDATE_READY, CATALOG_ONLY, BLOCKED
strict gates: 9
```

The four states are never merged. No gate is waived. There is no manual override.

The same vocabulary appears in
[`recommendation-result.schema.json`](../../schemas/recommendation-result.schema.json),
so a consumer reading a record does not have to know which subsystem wrote it.

## Current result

| State | Count |
|---|---|
| `STRICT_READY` | 0 |
| `CANDIDATE_READY` | 6 |
| `CATALOG_ONLY` | 12 |
| `BLOCKED` | 1 |

Zero strict recommendations at 4, 8, 12 and 16 GB. The two decisive blockers are
documented rather than unknown: inference runtimes publish no GPU-memory
overhead bound, and no independent multi-source quality result exists for any
Core artifact.

See [Recommendation readiness](../../docs/en/workflows/recommendation-readiness.md)
for the gate semantics and
[Evidence closure methodology](../../docs/en/methodology/evidence-closure-methodology.md)
for the full method.

## Regeneration

```bash
python -m atlas.cli.main closure core-set        # build the Core Recommendation Set
python -m atlas.cli.main closure evidence        # reacquire current provenance
python -m atlas.cli.main closure vram            # candidate-level fit states
python -m atlas.cli.main closure readiness        # publication readiness
python -m atlas.cli.main closure gap-matrix      # the evidence-gap matrix
python -m atlas.cli.main closure views --apply   # bilingual EN/AR views
```

Every command is dry-run by default. `closure evidence` performs a bounded,
anonymous, read-only reacquisition and is the only command in this project that
makes network requests.

## Excluded file

`external/bonsai-existing-server.json` records an observation of a
pre-existing local model server on the owner's machine, including a process id and
a port. It is excluded from version control by `.gitignore`. The generic safety
properties it demonstrated are covered by
[`test_local_server_safety.py`](../../tests/security/test_local_server_safety.py).

## Further reading

- [Recommendation readiness](../../docs/en/workflows/recommendation-readiness.md)
- [Evidence closure methodology](../../docs/en/methodology/evidence-closure-methodology.md)
- [Core Recommendation Set methodology](../../docs/en/methodology/core-recommendation-set-methodology.md)
- [Catalog data generation](../../docs/en/workflows/catalog-data-generation.md)
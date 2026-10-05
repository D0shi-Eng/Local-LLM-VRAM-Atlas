# Changelog

All notable changes to Local LLM VRAM Atlas are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
the project versions its **internal specifications** (schemas, registries,
policies) with semantic versioning independently of its public release cadence.

## Scope of this file

This changelog records **capability and contract changes**. It deliberately does
not record internal engineering history, execution chronology, or machine-local
diagnostics. If a change did not alter a schema, a registry, a policy, a CLI
contract or the published dataset, it does not belong here.

## [Unreleased]

Nothing pending.

## [0.4.0] — Catalog curation and evidence closure

### Added

- **Canonical record model.** Model, artifact, source and evidence records with
  revision-aware provenance. Identity is exact: a record describes one
  `artifact_set_id` at one revision, never "a model" in the abstract.
- **Quantization registry (v0.2.0).** 46 versioned entries with bits-per-weight
  reasoning, plus artifact-set grouping for sharded files and companion
  components.
- **Architecture resolution.** Canonical layer plans from `config.json` and GGUF
  metadata, with GQA/MHA/MQA classification and explicit refusal when a required
  tensor dimension cannot be resolved.
- **Architecture-aware memory model.** Weight bytes, KV-cache bytes at a given
  context, and static and dynamic overhead, producing a **range** with an
  explicit evidence state.
- **VRAM range classification.** Classification against 4, 8, 12 and 16 GB, with
  `insufficient_evidence` and `unsupported` as first-class outcomes.
- **Quality evidence intelligence.** Evaluation ingestion keyed on exact artifact
  identity and full harness identity; multi-axis quality profiles; benchmark
  comparability checks; quantization retention records.
- **Recommendation readiness.** Nine declared strict gates producing four
  readiness states: `STRICT_READY`, `CANDIDATE_READY`, `CATALOG_ONLY`, `BLOCKED`.
- **Evidence closure.** Core Recommendation Set, current-provenance
  reacquisition, VRAM evidence closure, and publication-readiness reporting.
- **Bounded external acquisition.** Credential-free, GET/HEAD-only fetching with
  an explicit host allowlist, weight-payload refusal, redirect refusal, and
  enforced request and byte ceilings. Includes read-only inspection of a
  pre-existing local runtime.
- **Transactional refresh.** Content fingerprints, bounded incremental discovery,
  planning, snapshot/rollback application, and a change journal.
- **Bilingual generated views.** 28 views rendered into English and Arabic from a
  single canonical payload in the same process.
- **18 JSON Schema Draft 2020-12 specifications** covering models, artifacts,
  sources, evidence, quantization, architecture, memory estimates, runtimes,
  measurements, benchmarks, evaluation results, quality policies, quality
  profiles, quantization retention, recommendation results, refresh plans,
  discovery checkpoints and change events.

### Changed

- Every mutating CLI command is now **dry-run by default**; writing requires an
  explicit `--apply`.
- The refresh surface uses a documented exit-code contract, where `10` means
  "changes found" and is a success signal rather than an error.
- Popularity signals (downloads, likes, trending) are recorded as popularity data
  only, and can never contribute to recommendation eligibility.

### Honest limitations recorded

- **Zero strict recommendations** at 4, 8, 12 and 16 GB. The decisive blocker is
  documented rather than unknown: inference runtimes publish no static or dynamic
  GPU-memory overhead bound, so a reliable upper bound cannot be constructed and
  no constant was invented. The tier verdict therefore remains
  `insufficient_evidence` rather than becoming a guessed fit.
- **Independent multi-source quality evidence is 0.** A bounded, anonymous,
  read-only search of independent benchmark surfaces found results published only
  as client-rendered pages or as datasets this system does not download. No
  protection was circumvented and no private endpoint was used.
- **Arabic quality evidence is unresolved for all 34 catalogued releases.** A
  multilingual claim is not Arabic evidence.
- **VRAM fit evidence is missing for all 34 catalogued releases**, and
  **architecture is unresolved for 10**, which makes KV-cache bytes
  non-computable for those artifacts rather than zero.
- A base release's quality score is never transferred to a quantized derivative,
  and a parent release's score is never transferred to an alignment-modified
  variant.
- Exact-artifact identity discrepancies are **recorded, never silently
  repaired**, including catalog quantization labels that differ from the
  publisher's own labels.

## [0.1.0] — Foundation

### Added

- Project scaffolding: package layout, packaging metadata, linting and test
  configuration.
- JSON Schema Draft 2020-12 specifications and a validation CLI with documented
  exit codes.
- Bilingual documentation structure with mirrored English and Arabic
  directories.
- A governance baseline covering evidence policy, licensing policy, security
  policy and contribution policy.
- An offline test suite with synthetic fixtures and opt-in live tests.

### Limitations recorded

- The project licence was undecided at this point. It is fixed at Apache-2.0 in
  the current release; see `LICENSE` and `NOTICE`.

## Versioning policy

| Item | Versioned | Current |
|---|---|---|
| Project release | yes | 0.4.0 |
| Catalog | yes | 0.4.0 |
| Quantization registry | yes | 0.2.0 |
| Quality snapshot | yes | 0.6.0 |
| Individual schemas | yes | 0.1.0 – 0.6.0 |
| Recommendation policy | yes | 0.6.0 |
| Publication-readiness policy | yes | 0.1.0 |

A schema version change means a contract change, and is treated as a breaking
change for consumers of that schema regardless of the project version.

## Licence

Atlas code is licensed under the Apache License 2.0. External models retain
their own licences. See `LICENSE` and `NOTICE`.
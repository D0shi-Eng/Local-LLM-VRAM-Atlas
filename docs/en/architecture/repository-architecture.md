# Repository Architecture

> Arabic counterpart: [`docs/ar/architecture/repository-architecture.md`](../../ar/architecture/repository-architecture.md)

## Purpose

This document defines the published layout of Local LLM VRAM Atlas, the
responsibility of each directory, and the boundaries a change must respect.

It describes the **curated public surface**: what is version-controlled, and
what is deliberately withheld.

## Layout

```text
README.md / README_AR.md   project entry points (English / Arabic)
CHANGELOG.md               curated capability and contract history
LICENSE / NOTICE           Apache-2.0 grant and third-party scope
pyproject.toml             packaging, pytest, and Ruff configuration
.gitignore                 repository hygiene, including withheld paths

src/atlas/                 implementation, 113 modules
  intake/                  source adapters, normalisation, provenance, guards
  archinfo/                architecture resolution and layer plans
  quant/                   versioned quantization registry
  artifact/                artifact-set grouping
  memory/                  weight, KV-cache and overhead arithmetic
  vram/                    tier classification
  quality/                 evidence ingestion, profiles, retention, readiness
  catalog/                 canonical catalog assembly and view generation
  refresh/                 fingerprints, planning, transactional apply
  closure/                 core set, evidence closure, publication readiness
  external/                bounded external acquisition
  security/                network policy enforcement
  validation/              schema validation (verify only, never mutate)
  cli/                     command surface, dry-run by default

schemas/                   18 JSON Schema Draft 2020-12 specifications
catalog/                   canonical machine-readable dataset
  models/                  34 model records
  artifacts/               201 artifact records
  sources/                 source registry and observations
  evidence/                109 evidence sidecars
  benchmarks/evaluations/  21 benchmark results
  measurements/            external VRAM measurements
  quality/                 profiles, retention, gaps, manifest
  closure/                 core set, VRAM evidence, readiness, external evidence
  snapshots/               raw source snapshots kept for re-verification
  views/                   28 generated bilingual views
  manifest.json            counts, model ids, schema versions

docs/en, docs/ar           bilingual documentation with mirrored structure
  architecture/            system architecture, canonical record flow, this document
  workflows/               refresh, recommendation readiness, data generation
  catalog/                 catalog overview
  methodology/             published methodology
  governance/              licensing, evidence, security, contribution, metadata
  terminology/             glossary
docs/diagrams/             bilingual figure index
assets/branding/           icon, dark icon, banner, bilingual brand guidelines
tests/                     real tests plus synthetic fixtures (no real model data)
tools/                     publication proofreading aids
```

## Responsibilities

- `schemas/` is normative: every record shape is decided there, once, and every
  tool and test follows it. No rule is duplicated in prose and left to drift.
- `catalog/` is canonical: it is the single source of truth. Every Markdown page
  and JSON view is generated from it.
- `src/atlas/validation/` verifies records against schemas and reports readable
  errors with non-zero exit codes. It never edits records, never downloads
  anything, and never requires credentials.
- `tests/fixtures/valid/` holds synthetic records that must pass;
  `tests/fixtures/invalid/` holds records that must fail for a documented
  reason. Fixture names always contain `fixture-` so nobody mistakes them for
  real catalog data.
- `assets/branding/` holds original visual identity. No third-party brand mark
  appears anywhere in the tree.

## What is deliberately withheld

The following exist in a local working tree during development but are excluded
from version control by `.gitignore`, because they are internal engineering
history or machine-local state rather than public documentation:

| Withheld path | Reason |
|---|---|
| `docs/phases/` | Build-phase execution reports, closure reports, audits and handoff inventories |
| `catalog/refresh/` | Volatile per-run records |
| `catalog/checkpoints/` | Internal discovery scratch state |
| `catalog/changes/` | Operational change journal |
| `catalog/release-candidate-data-manifest.json` | Operational manifest carrying a machine-local absolute path |
| `catalog/closure/external/bonsai-existing-server.json` | Observation of the owner's own machine, including a process id and port |

None of these paths is required to read, validate or regenerate the published
dataset.

## Non-goals for this layout

- No model weights are ever stored in this tree; the project is a catalog, not a
  warehouse.
- No secrets, tokens, or `.env` files.
- No continuous integration workflow and no published site.
- No parallel representations of the same data (JSON plus hand-synced YAML,
  Markdown, or CSV). JSON records validated by JSON Schema are the single source
  of truth; tables and pages are generated from them.
- No second remote, no public mirror, and no visibility change are part of the
  repository contract.

## Boundaries for change

Discovery, metadata extraction, licence gating, runtime checks, VRAM
classification, and review (see [`data-flow.md`](data-flow.md)) may add new
modules, but they must consume `schemas/` and `src/atlas/validation/` rather
than redefining record shapes or re-implementing validation. Any change to a
record shape goes through the schema first, with tests.

Documentation changes follow the same discipline in reverse: every English
document needs an Arabic counterpart, and both are held to matching heading
structure by an automated test.

## Further reading

- [System architecture](atlas-system-architecture.md)
- [Canonical record flow](canonical-record-flow.md)
- [Catalog data generation workflow](../workflows/catalog-data-generation.md)
- [Licensing policy](../governance/licensing-policy.md)
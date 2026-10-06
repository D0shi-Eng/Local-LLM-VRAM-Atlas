<div align="center">

<img src="assets/branding/icon.svg" alt="Local LLM VRAM Atlas" width="128" height="128">

# Local LLM VRAM Atlas

**Evidence-aware atlas for local LLMs across 4 / 8 / 12 / 16 GB VRAM tiers**

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)
[![Catalog](https://img.shields.io/badge/catalog-34_models-3E7CB1.svg)](catalog/manifest.json)
[![Strict recommendations](https://img.shields.io/badge/strict_recommendations-0-E8B45A.svg)](docs/en/workflows/recommendation-readiness.md)

[English](README.md) · **[العربية](README_AR.md)**

</div>

<div align="center">

<img src="assets/branding/banner.svg" alt="Local LLM VRAM Atlas — evidence-aware atlas for local LLMs across VRAM tiers" width="100%">

</div>

---

## What this is

Local LLM VRAM Atlas is a **metadata-only, evidence-aware reference system** for
local and open-weight language models, organised around the question that
actually determines whether a model is usable on consumer hardware:

> Which model can I run on a GPU with 4GB, 8GB, 12GB or 16GB of VRAM — and how
> confident can anyone be in that answer?

The Atlas answers with **canonical records, declared evidence, and explicit
readiness states**. It does not publish a leaderboard. It does not tell you the
best model. Where the evidence does not support an answer, it reports that the
answer is unavailable, and it names the missing evidence.

**Atlas is currently a curated private repository.** The data is real, the
tooling is real, and the coverage is incomplete. Both facts are stated plainly
below rather than marketed around.

## Why parameter count is not enough

A parameter count such as "8B" does not determine whether a model fits in a given
VRAM budget. Two 8B models in different quantizations can differ by several
gigabytes at runtime, because actual consumption depends on:

- quantization format and effective bits per weight;
- runtime and backend, and their GPU-memory overhead;
- KV-cache dtype, context length, and sequence count;
- batch size and offload strategy;
- multimodal components and vision projectors.

File size is not VRAM usage either. A weight file smaller than the card's VRAM
does **not** prove the model runs there. The schemas here deliberately keep
`weight_file_size_gib` separate from `measured_vram_gib`, `minimum_vram_gib` and
`recommended_vram_gib`, and no tooling in this repository is permitted to infer
"fits" from file size alone.

## Current scope and honest position

This is the current state of the data, stated without hedging.

| Measure | Value |
|---|---|
| Model releases catalogued | 34 |
| Quantized artifact variants catalogued | 201 |
| JSON Schema specifications | 18 |
| Evidence records | 109 |
| Benchmark evaluation results | 21 |
| External memory measurements | 2 |
| Quantization retention records | 8 |
| Generated bilingual views | 28 |
| Offline tests | 687 passing, 8 skipped |
| **Strict recommendations at 4 / 8 / 12 / 16 GB** | **0** |

Readiness across the 19 candidates in the Core Recommendation Set:

| Readiness state | Count |
|---|---|
| `STRICT_READY` | 0 |
| `CANDIDATE_READY` | 6 |
| `CATALOG_ONLY` | 12 |
| `BLOCKED` | 1 |

Unresolved evidence domains:

| Domain | Affected models |
|---|---|
| Arabic quality evidence | 34 of 34 |
| VRAM fit evidence | 34 of 34 |
| Independent multi-source quality evidence | 34 of 34 |
| Quantization retention evidence | 8 |
| Resolved architecture | 10 |

### Why zero strict recommendations

Because a strict recommendation requires evidence that does not yet exist for
any artifact in the catalog. The two decisive blockers are documented, not
unknown:

1. **No published runtime overhead bound.** Inference runtimes report GPU
   allocations at runtime for a specific backend and model, but publish no
   static or dynamic overhead maximum. Atlas therefore keeps the upper memory
   bound absent rather than substituting an invented constant — which means the
   tier verdict stays `insufficient_evidence` instead of becoming a guessed fit.
2. **No independent multi-source quality results.** A bounded, anonymous,
   read-only search of independent benchmark surfaces found results published
   only as client-rendered pages or as datasets that this system does not
   download. No protection was circumvented and no private endpoint was used.

This is the intended behaviour. A fabricated non-zero count would be worse than
an honest zero.

## Core features

- **Canonical model records** — schema-validated JSON with provenance, licence,
  openness classification and per-field verification status.
- **Exact artifact identity** — a record is about one `artifact_set_id` at one
  revision, never about "a model" in the abstract. Two quantizations of one model
  are two different artifacts.
- **Quantization intelligence** — a versioned registry of 46 quantization
  entries with bits-per-weight reasoning, plus artifact grouping for sharded
  files and companion components.
- **Architecture-aware memory analysis** — weight bytes, KV-cache bytes, static
  and dynamic overhead, and a **range** with an explicit evidence state rather
  than a single fabricated number.
- **VRAM tier classification** — range-based classification against 4, 8, 12 and
  16 GB, where `insufficient_evidence` is a first-class outcome.
- **Quality evidence with provenance** — evaluation results attach to the exact
  artifact measured, with full harness identity, and never inherit a base
  model's score.
- **Quantization retention** — comparable base-versus-quantized deltas when
  every comparable-setting key matches, and no comparison at all when any key
  differs.
- **Recommendation readiness** — nine declared strict gates producing four
  readiness states that are never merged, never waived and never set by hand.
- **Bilingual output** — every generated view is rendered into English and Arabic
  from one canonical payload in the same process.
- **Bounded, credential-free acquisition** — anonymous public read only, GET and
  HEAD only, explicit request and byte ceilings, weight-payload URLs refused
  before a request is made, redirects never followed.

## What Atlas does not claim

- It does **not** claim a verified best model for any VRAM tier. It currently
  reports zero strict recommendations at every tier.
- It does **not** claim complete model coverage. The catalog is a curated
  selection built by controlled discovery passes, not exhaustive enumeration.
- It does **not** claim runtime certainty. It reports evidence states and names
  what is missing.
- It does **not** transfer a base model's quality score to a quantized
  derivative, or a parent model's score to an alignment-modified variant.
- It does **not** treat downloads, likes or trending status as quality signals.
- It does **not** infer open-source status from the ability to download weights.
- It does **not** host model weights. It is a catalog, not a model warehouse.
- It does **not** claim security properties beyond what it measures, and it does
  not claim a vulnerability-free state.

## Evidence levels

Every important claim carries a verification status, and a weaker status is never
promoted without a new observation.

| Status | Meaning |
|---|---|
| `unknown` | Not known, and must not be invented. |
| `unverified` | Recorded but not yet checked. |
| `estimated` | Produced under a documented method. |
| `publisher_claim` | Asserted by the model publisher; not an independent fact. |
| `quantizer_claim` | Asserted by the quantizer; not an independent fact. |
| `independently_verified` | Confirmed by an independent, reproducible source. |
| `atlas_verified` | Measured inside the Atlas under documented conditions. |

Publisher claims are never converted into independent facts.

## Recommendation semantics

Recommendation readiness is categorical. The four states are never merged.

| State | Meaning |
|---|---|
| `STRICT_READY` | Every declared strict gate is satisfied by persisted, walkable evidence. |
| `CANDIDATE_READY` | Substantial evidence and useful content, one or more strict gates still open, every missing gate named. |
| `CATALOG_ONLY` | Legitimate catalog content without enough recommendation evidence. |
| `BLOCKED` | A critical identity, licence, runtime, lineage or evidence-integrity problem. |

A single missing gate lowers a state. It never raises one. There is no manual
override and no waiver by popularity, size, parameter count, brand, recency or
adoption.

## Installation

Atlas is a Python library and CLI. It requires Python 3.10 or newer.

```bash
git clone <repository-url>
cd Local-LLM-VRAM-Atlas

python -m venv .venv
# Windows:      .venv\Scripts\activate
# Linux/macOS:  source .venv/bin/activate

pip install -e ".[dev]"
```

Runtime dependencies are `jsonschema` and `huggingface_hub`. Development adds
`pytest` and `ruff`.

The repository is usable directly from a checkout without installation:

```bash
$env:PYTHONPATH = 'src'          # Windows PowerShell
export PYTHONPATH=src            # Linux / macOS
```

## Quick start

Verify the dataset and the tooling:

```bash
python -m atlas.cli.main sources --check
python -m atlas.cli.main validate --schema model \
  --record catalog/models/openbmb-minicpm5-2b.json
python -m atlas.cli.main catalog stats
```

Read the current recommendation position:

```bash
python -m atlas.cli.main recommend tier --tier 8
```

```
tier_gb: 8
Strict recommendations: 0
Promising candidates: 0
Fit candidates — quality evidence incomplete: 0
Insufficient evidence: 34
Reason: no model satisfies every declared recommendation domain for this tier.
```

Inspect the evidence gaps, so the zero above is legible rather than mysterious:

```bash
python -m atlas.cli.main quality gaps
```

## CLI usage

Every mutating command is **dry-run by default**. Writing requires an explicit
`--apply`.

```bash
# Inspect public metadata without writing anything
python -m atlas.cli.main inspect openbmb/MiniCPM5-2B

# Schema validation
python -m atlas.cli.main validate --schema model \
  --record catalog/models/qwen-qwen3-8b.json

# Catalog queries
python -m atlas.cli.main catalog stats
python -m atlas.cli.main catalog list --vram-tier 8
python -m atlas.cli.main catalog show qwen-qwen3-8b
python -m atlas.cli.main catalog views

# Quantization registry
python -m atlas.cli.main quantization list --family q4

# Architecture resolution from a config file
python -m atlas.cli.main arch resolve --config path/to/config.json

# Recommendation readiness
python -m atlas.cli.main recommend tier --tier 12
python -m atlas.cli.main recommend model qwen-qwen3-8b --tier 8

# Quality evidence
python -m atlas.cli.main quality sources --check
python -m atlas.cli.main quality gaps
python -m atlas.cli.main quality show qwen-qwen3-8b
python -m atlas.cli.main retention show qwen-qwen3-8b

# Publication readiness
python -m atlas.cli.main closure readiness
python -m atlas.cli.main closure vram
python -m atlas.cli.main closure gap-matrix
```

The refresh surface uses a documented exit-code contract, where `10` means
"changes found" and is a **success** signal, not an error. See
[Refresh and evidence ingestion](docs/en/workflows/refresh-and-evidence-ingestion.md#exit-code-contract).

## Repository structure

```text
Local-LLM-VRAM-Atlas/
├── README.md                 This document (English)
├── README_AR.md              Arabic counterpart
├── CHANGELOG.md              Curated change history
├── LICENSE                   Apache License 2.0
├── NOTICE                    Attribution and third-party scope
├── pyproject.toml            Package metadata
├── .gitignore                Repository hygiene
│
├── src/atlas/                Implementation, 113 modules
│   ├── intake/               Source adapters, normalisation, provenance, guards
│   ├── archinfo/             Architecture resolution and layer plans
│   ├── quant/                Versioned quantization registry
│   ├── artifact/             Artifact-set grouping
│   ├── memory/               Weight, KV-cache and overhead arithmetic
│   ├── vram/                 Tier classification
│   ├── quality/              Evidence ingestion, profiles, retention, readiness
│   ├── catalog/              Canonical catalog assembly and view generation
│   ├── refresh/              Fingerprints, planning, transactional apply
│   ├── closure/              Core set, evidence closure, publication readiness
│   ├── external/             Bounded external acquisition
│   ├── security/             Network policy enforcement
│   ├── validation/           Schema validation
│   └── cli/                  Command surface, dry-run by default
│
├── schemas/                  18 JSON Schema Draft 2020-12 specifications
│
├── catalog/                  Canonical dataset
│   ├── models/               34 model records
│   ├── artifacts/            201 artifact records
│   ├── evidence/             109 evidence sidecars
│   ├── benchmarks/           21 evaluation results
│   ├── quality/              Profiles, retention, gaps
│   ├── closure/              Core set, VRAM evidence, readiness
│   ├── runtimes/             Runtime knowledge base and measurements
│   └── views/                28 generated bilingual views
│
├── docs/
│   ├── en/                   English documentation
│   │   ├── architecture/     System architecture, canonical record flow
│   │   ├── workflows/        Refresh, recommendation, data generation
│   │   ├── catalog/          Catalog overview
│   │   ├── methodology/      Published methodology
│   │   ├── governance/       Licensing, evidence, security, contribution
│   │   └── terminology/      Glossary
│   ├── ar/                   Arabic counterparts, same structure
│   └── diagrams/             Bilingual figure index
│
├── assets/branding/          Icon, banner, bilingual brand guidelines
├── tests/                    701 tests, 17 domain directories, synthetic fixtures
└── tools/                    Publication proofreading aids
```

### Where to look first

| If you want to understand | Read |
|---|---|
| How the system is put together | [System architecture](docs/en/architecture/atlas-system-architecture.md) |
| The data model | [Canonical record flow](docs/en/architecture/canonical-record-flow.md) |
| How evidence becomes a recommendation | [Recommendation readiness](docs/en/workflows/recommendation-readiness.md) |
| How external reality enters the catalog | [Refresh and evidence ingestion](docs/en/workflows/refresh-and-evidence-ingestion.md) |
| What is in the dataset | [Catalog overview](docs/en/catalog/catalog-overview.md) |
| All diagrams | [Figure index](docs/diagrams/README.md) |
| Terminology | [Glossary](docs/en/terminology/glossary.md) |

Methodology documents are named after the **method**, not after the order in
which it was written: `quantization-registry-methodology.md`, never
`phase-02-something.md`. Internal build reports are not published at all; see
[repository architecture](docs/en/architecture/repository-architecture.md).

## Architecture and workflows

Nine diagrams cover the system, the data model, the workflows and the repository
layout. All are Mermaid, embedded in Markdown, and render directly on the
repository host. See the [figure index](docs/diagrams/README.md).

## Development

```bash
python -m pytest -q
python -m ruff check src tests
```

The test suite is fully offline by default. Tests that contact the public
Hugging Face Hub are opt-in via the `live` marker:

```bash
python -m pytest -q -m live
```

Publication proofreading aids live in `tools/`:

```bash
python tools/qa_proofread.py --all      # bilingual text and script integrity
python tools/qa_doc_parity.py           # English/Arabic heading parity
python tools/qa_cli_refs.py             # every documented CLI command runs
```

## Documentation note

The documentation is bilingual by construction. English and Arabic generated
views are rendered from one canonical payload in the same process, so they cannot
diverge. Hand-written documents are held to the same rule by an automated test
that requires every English document to have an Arabic counterpart with matching
heading structure.

## License

Atlas code is licensed under the **Apache License 2.0**. See [`LICENSE`](LICENSE)
and [`NOTICE`](NOTICE).

External models retain their own licences. This repository contains **no model
weights**. Atlas catalogues and analyzes metadata and published evidence about
third-party models; it does not relicence them, redistribute them, or transfer
ownership of them. Benchmark results and publisher documentation retain the
rights of their original authors.

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by any model
publisher, quantizer, benchmark maintainer or inference runtime mentioned in the
catalog, unless such a relationship is explicitly documented and evidenced.

## Status

This repository is private and not yet a public launch. The tooling, the schemas
and the catalog are real and usable today. The evidence base is maturing, and the
Atlas reports its own incompleteness rather than concealing it. Public release
preparation is a separate, later step.

## Further reading

- [Licensing policy](docs/en/governance/licensing-policy.md)
- [Evidence policy](docs/en/governance/evidence-policy.md)
- [Security policy](docs/en/governance/security-policy.md)
- [Contribution policy](docs/en/governance/contribution-policy.md)
- [Glossary](docs/en/terminology/glossary.md)
- [VRAM methodology](docs/en/methodology/vram-methodology.md)
- [Quantization methodology](docs/en/methodology/quantization-methodology.md)
- [Quality evidence methodology](docs/en/methodology/quality-evidence-methodology.md)
- [Repository metadata proposal](docs/en/governance/repository-metadata.md)
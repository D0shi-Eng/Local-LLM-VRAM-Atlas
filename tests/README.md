# Test Suite

> Arabic counterpart: [`README_AR.md`](README_AR.md)

The `tests/` tree is organised by **engineering domain**, not by the order in
which the project was built. The directory names describe what the code does, so
a reader who has never seen this repository can infer the architecture from the
test layout alone.

## Running the suite

```bash
python -m pytest -q
```

The suite is **fully offline by default**. No test in the default run performs a
network request, starts a server, downloads a model, or writes to the canonical
catalog.

## Live tests

Tests that contact the public Hugging Face Hub are opt-in and marked `live`:

```bash
python -m pytest -q -m live
ATLAS_LIVE=1 python -m pytest -q -m live
```

They read **public metadata only**. They never download weights and never
authenticate.

## Domains

| Directory | Responsibility | Example |
|---|---|---|
| `architecture/` | Architecture resolution and canonical layer plans | `test_canonical_resolution.py` |
| `artifacts/` | File grouping into artifact sets | `test_artifact_grouping.py` |
| `catalog/` | Canonical catalog records, identity, qualification, tiering, and the ban on promotional claims | `test_catalog_qualification.py` |
| `cli/` | Command surface and exit codes | `test_cli_core.py` |
| `discovery/` | Candidate discovery and live intake | `test_incremental_discovery.py` |
| `documentation/` | English/Arabic document pairing | `test_doc_pairing.py` |
| `evidence/` | Evidence identifiers, sidecars, reacquisition and external acquisition | `test_evidence_ids.py` |
| `intake/` | Source adapters, normalisation, persistence, licence and lineage | `test_intake_pipeline.py` |
| `memory/` | Weight and KV arithmetic, static memory, VRAM classification and evidence | `test_kv_cache.py` |
| `quality/` | Quality profiles, comparability, retention, anti-manipulation | `test_quality_profiles.py` |
| `quantization/` | Quantization registry and bits-per-weight reasoning | `test_bits_per_weight.py` |
| `recommendations/` | Recommendation eligibility, readiness and anti-fabrication | `test_recommendation_readiness.py` |
| `refresh/` | Refresh planning, transactional apply, fingerprints | `test_refresh_plan_apply.py` |
| `runtimes/` | Runtime knowledge base and external measurement registry | `test_runtimes_measurements.py` |
| `security/` | URL safety, SSRF, weight refusal, secret scanning, zero-weight guarantees | `test_metadata_fetch_security.py` |
| `validation/` | Schema contracts and repository structure | `test_model_schema.py` |
| `builders/` | Shared synthetic record builders; not tests themselves | `candidates.py` |
| `fixtures/` | Synthetic JSON fixtures for validation; see below | `valid/`, `invalid/` |

## Fixture policy

`fixtures/valid/` holds synthetic records that **must** validate.
`fixtures/invalid/` holds records that **must** fail, each for one documented
reason. Every fixture filename contains `fixture-` so that no one can mistake it
for real catalog data.

Every fixture is fabricated. No fixture contains a real credential, a real
private path, or real personal data.

### The one secret-like fixture

`fixtures/invalid/fixture-secret-like.txt` deliberately contains a fabricated
token-shaped string. Its own header states that it is synthetic, that it grants
nothing, and that it exists so the secret scanner can prove it detects the pattern
without leaking. It is the only allowlisted file in the secret scan.

## Zero-weight guarantee

No test may load, download, or reference a model-weight file. `security/` contains
static guards that reject a downloader or loader being introduced into `src/`,
and `security/test_no_weight_files.py` fails the build if a weight extension ever
appears in the tree.

## Shared builders

`builders/candidates.py` and `builders/records.py` provide synthetic records —
candidates, model records, measurements, evaluations, architecture fields — reused
across the domains that need them. They exist so that two domains do not invent
incompatible shapes for the same record.

Import them by module path:

```python
from builders.candidates import candidate, model_record, measurement
from builders.records import model_record as quality_model_record
```

## Adding a test

1. Put it in the directory for the domain it exercises. If no directory fits, add
   one and name it after the subsystem, not after a milestone.
2. Name the file for the responsibility, not for the module under test alone:
   `test_recommendation_readiness.py`, not `test_phase6.py`.
3. Write the docstring in domain language. "Incremental refresh behaviour" — not
   "what phase 5 added".
4. Keep it offline. If it genuinely needs the public Hub, mark it `live`.
5. Use `builders/` rather than inventing a second shape for a record type.
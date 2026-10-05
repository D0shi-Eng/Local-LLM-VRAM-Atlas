# Catalog Overview

> Arabic counterpart: [`docs/ar/catalog/catalog-overview.md`](../../ar/catalog/catalog-overview.md)

## What the catalog is

The catalog is the Atlas's canonical, machine-readable dataset: a set of
schema-validated JSON records describing model releases and their concrete
artifacts, together with the evidence attached to them and the bilingual views
rendered from that evidence.

It is **not** a model warehouse. The repository contains no model weights.

## Current contents

| Quantity | Value |
|---|---|
| Model releases catalogued | 34 |
| Quantized artifact variants catalogued | 201 |
| JSON Schema specifications | 18 |
| Evidence records | 109 |
| Benchmark evaluation results | 21 |
| External memory measurements | 2 |
| Quantization retention records | 8 |
| Source registry entries | 15 |
| Quality evidence sources | 7 |
| Generated views | 28 |
| Catalog version | 0.4.0 |
| Quantization registry version | 0.2.0 |
| Quality snapshot version | 0.6.0 |
| Core recommendation set candidates | 19 |

Regenerate any figure above with:

```bash
python -m atlas.cli.main catalog stats
python -m atlas.cli.main quality profile
python -m atlas.cli.main closure core-set
```

## Directory layout

```text
catalog/
  manifest.json          Counts, model ids, schema versions
  models/                Canonical model records, one file per release
  artifacts/             Canonical artifact records, one file per quantized variant
  sources/               Source registry and per-source observations
  evidence/              Evidence sidecars: one field, one value, one level
  benchmarks/
    evaluations/         Benchmark results with full harness identity
  measurements/          External VRAM measurements, never produced locally
  quality/
    profiles/            Per-model multi-axis quality profiles
    retention/           Quantization retention records
    gaps.json            Missing evidence domains per model
    manifest.json        Quality snapshot manifest
  closure/               Core recommendation set, VRAM evidence, readiness
    external/            Normalized external evidence and source outcomes
  snapshots/             Raw source snapshots retained for re-verification
  views/                 Generated bilingual Markdown and JSON views
  refresh/               Volatile run records (not published)
  checkpoints/           Discovery checkpoints (not published)
  changes/               Operational change journal (not published)
```

## Record families

| Family | Schema | Count in tree |
|---|---|---|
| Model | `model.schema.json` | 34 |
| Artifact | `artifact.schema.json` | 201 |
| Source | `source.schema.json` | registry plus per-source records |
| Evidence | `evidence.schema.json` | 109 |
| Evaluation result | `evaluation-result.schema.json` | 21 |
| Measurement | `measurement.schema.json` | 2 |
| Quantization | `quantization.schema.json` | per model record |
| Architecture | `architecture.schema.json` | per model record |
| Quality profile | `quality-profile.schema.json` | 34 |
| Quant retention | `quant-retention.schema.json` | 8 |
| Recommendation result | `recommendation-result.schema.json` | derived, not stored per tier |
| Runtime | `runtime.schema.json` | registry plus per-model references |

## Coverage and openness

The catalog distinguishes openness precisely, and never infers open-source status
from the ability to download weights.

```text
open_source_ai / open_weights_permissive / open_weights_restricted
source_available / proprietary / unclear
```

Format distribution across the catalogued releases:

| Container format | Releases |
|---|---|
| GGUF | 12 |
| safetensors | 22 |

Quantization family distribution:

| Family | Artifacts |
|---|---|
| q2 | 2 |
| q8 | 1 |
| bf16 | 5 |
| unknown | 26 |

The large `unknown` family count is **honest data, not a gap in reporting**: those
releases carry no declared quantization family, and Atlas does not infer one from
a filename or a repository name.

## Generated views

Views are rendered from one canonical payload into both languages in the same
process, so the English and Arabic renderings cannot diverge.

| View family | Contents |
|---|---|
| `4gb`, `8gb`, `12gb`, `16gb` | Per-tier candidate listings |
| `quality/*` | Per-axis quality views, general through agentic tool use |
| `quality/tier-*` | Per-tier quality readiness split |
| `closure/core-set` | Core recommendation set with readiness states |
| `closure/tier-readiness` | Per-tier readiness matrix and blocking gates |
| `closure/vram-evidence` | VRAM evidence states per Core candidate |
| `closure/quant-retention` | Quantization retention closure |
| `closure/evidence-gap` | Evidence-gap matrix |
| `native-low-bit`, `ternary`, `high-compression` | Special-variant views |
| `uncensored`, `abliterated`, `heretic` | Alignment-variant views |

Every view carries a generated banner and must not be hand-edited. Regeneration
overwrites it by design.

## Honest coverage statement

The catalog is a **curated selection**, not a complete index of local models. The
following limits are structural and are reported rather than hidden:

- **Not every model is catalogued.** The catalog is built by controlled discovery
  passes, not by exhaustive enumeration.
- **Evidence coverage is uneven.** Three quality axes — Arabic quality, VRAM fit
  evidence, and independent multi-source quality — are unresolved across the
  catalog. Arabic quality is `unknown` for all 34 releases, and VRAM fit evidence
  and independent multi-source quality are missing for all 34.
- **Zero strict recommendations.** See
  [Recommendation readiness](../workflows/recommendation-readiness.md) for why, and
  for the exact blocking gates.
- **Architecture is unresolved for 10 releases**, which makes KV-cache bytes
  non-computable for those artifacts rather than zero.

## Validation

Validate any record against its schema:

```bash
python -m atlas.validation.cli --schema model \
  --record catalog/models/openbmb-minicpm5-2b.json
```

Or through the main CLI:

```bash
python -m atlas.cli.main validate --schema model \
  --record catalog/models/openbmb-minicpm5-2b.json
```

## Further reading

- [Generated documentation policy](../methodology/generated-documentation-policy.md)
- [Catalog views methodology](../methodology/catalog-views.md)
- [Catalog qualification](../methodology/catalog-qualification.md)
- [Catalog population](../methodology/catalog-population.md)
- [Model identity](../methodology/model-intake.md)
# Catalog

> **النسخة العربية:** [README_AR.md](README_AR.md)

**Status:** curated metadata-only dataset — 34 model releases, 201 quantized
artifact variants, 109 evidence records. Not a complete database, not a ranking.

This directory holds the canonical machine-readable catalog:

| Path | Contents | Schema |
|---|---|---|
| `manifest.json` | Counts, model ids, schema versions | — |
| `models/` | Model records, one file per release | `model.schema.json` |
| `artifacts/` | Quantized artifact variants, one file each | `artifact.schema.json` |
| `sources/` | Source registry and per-source observations | `source.schema.json` |
| `evidence/` | Evidence sidecars, one field per record | `evidence.schema.json` |
| `benchmarks/evaluations/` | Benchmark results with full harness identity | `evaluation-result.schema.json` |
| `measurements/` | Externally reported VRAM observations | `measurement.schema.json` |
| `quality/` | Profiles, retention records, evidence gaps, manifest | `quality-profile.schema.json`, `quant-retention.schema.json` |
| `closure/` | Core recommendation set, VRAM evidence, readiness | — |
| `snapshots/` | Raw public-metadata snapshots (audit inputs, **not** canonical records, **not** schema-validated) | — |
| `runtimes/` | Reserved for runtime records; currently empty by design | `runtime.schema.json` |
| `views/` | Generated bilingual Markdown and JSON views | — |

## Rules

- JSON records validated by JSON Schema are the single source of truth.
- No model weights are ever stored here.
- No record may claim `verified` or `recommended` status without the provenance
  required by the [evidence policy](../docs/en/governance/evidence-policy.md).
- File size is never treated as VRAM usage.
- An absent field means "not known" and is never filled in by estimation.

## Coverage

The catalog is a **curated selection**, not an exhaustive index of local models.
Three evidence domains remain unresolved across the catalogued releases: Arabic
quality evidence, VRAM fit evidence, and independent multi-source quality
evidence. The consequence is that **zero strict recommendations** are reported at
4, 8, 12 and 16 GB.

That is an evidence outcome, not an unfinished feature. See
[recommendation readiness](../docs/en/workflows/recommendation-readiness.md) for
the exact blocking gates.

## Generated output

Everything under `views/` is generated from the canonical records by the same
pipeline that produces both languages from one payload. Do not hand-edit a
generated view: the next regeneration overwrites it.

## Excluded paths

`refresh/`, `checkpoints/` and `changes/` hold volatile run state and an
operational journal. They are regenerated on demand and are not part of the
published repository.

## Further reading

- [Catalog overview](../docs/en/catalog/catalog-overview.md)
- [Catalog views methodology](../docs/en/methodology/catalog-views.md)
- [Catalog qualification](../docs/en/methodology/catalog-qualification.md)
- [Catalog data generation](../docs/en/workflows/catalog-data-generation.md)
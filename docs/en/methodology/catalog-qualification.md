# Catalog Qualification Methodology

> Status: curated snapshot. Metadata-only. No ranking, no score.

## What "qualified" means

"Qualified" means Atlas holds enough trustworthy metadata to include the
model under current catalog rules. It does **not** mean best, recommended,
safe, fastest, or fully VRAM-verified.

- `qualified` → stored as `catalog_status: verified`
- `qualified_with_limitations` → stored as `catalog_status: experimental`
  with every limitation explicit (architecture partial, license custom,
  runtime support unknown, VRAM fit indeterminate, revision unresolved).
- `blocked` / `rejected` / `deprecated` preserve the reason; nothing is
  silently discarded.

Existing `model.schema.json` enums are reused; see
`src/atlas/catalog/qualification.py` for the stable map. No schema drift.

## Required evidence

Identity, source (with resolved revision or documented limitation), license
status, lineage status, artifact metadata, quantization/format status,
architecture status, provenance. Missing data is never fabricated to reach
`qualified`.

## Related

- `model-intake.md`, `metadata-verification.md`, `evidence-confidence-methodology.md`
- `static-vram-classification.md` (fit states stay distinct)
- `uncensored-classification.md` (alignment claims stay claims)

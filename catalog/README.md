# Catalog

> **النسخة العربية:** [README_AR.md](README_AR.md)

**Status:** Phase 1 seed data only — 7 real intake records proving the
pipeline (6 engineering seeds + 1 third-party derivative). Not a complete
database, not a ranking.

This directory will hold the future machine-readable catalog:

- `models/` — validated model records conforming to `schemas/model.schema.json`.
- `sources/` — source records conforming to `schemas/source.schema.json`
  (including `registry.json`, the trusted source list).
- `evidence/` — evidence records conforming to `schemas/evidence.schema.json`,
  one per critical field, linked from model records via `evidence_ids`.
- `snapshots/` — raw public-metadata snapshots (audit inputs, NOT canonical
  records, NOT schema-validated; they show exactly what the source said).
- `runtimes/` — runtime compatibility records conforming to `schemas/runtime.schema.json`.
- `benchmarks/` — benchmark records conforming to `schemas/benchmark.schema.json`.

Rules:

- JSON records validated by JSON Schema are the single source of truth.
- No model weights are ever stored here (see security policy).
- No record may claim `verified` / `recommended` status without the provenance
  required by the evidence policy.
- File size is never treated as VRAM usage.

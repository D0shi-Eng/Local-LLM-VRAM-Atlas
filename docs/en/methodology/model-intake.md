# Model Intake

> Arabic counterpart: `docs/ar/methodology/model-intake.md`

## Scope

Model intake converts public, anonymous, metadata-only snapshots into Atlas
canonical records. It never downloads weights, never runs models, never
assigns VRAM tiers, never ranks, and never invents missing values.

## Stage order

```text
Public Model ID → Source Resolution → Metadata Fetch → Revision Resolution
→ Raw Metadata Boundary → Normalization → Source/Officiality Assessment
→ License Extraction → Architecture Extraction → Artifact Inventory
→ Lineage Resolution → Evidence Construction → Canonical Record Build
→ Schema Validation → Persistence
```

Each stage fails loudly instead of producing a misleading record.

## Boundaries

Raw external metadata (`RawModelMetadata`) never crosses into the domain:
a normalizer translates it into a canonical record, and Hugging Face SDK
classes never leak past the adapter. Platform-specific fields that have no
canonical home (pipeline tags, library names, sibling lists) stay in
evidence notes, never in the model schema.

## Dry-run first, idempotent writes

`atlas intake <repo>` is a dry-run by default: it fetches, builds,
validates, and prints a summary without writing. `--write` persists only
after validation, atomically (temp file + replace). Re-running the same
`repo + resolved revision` is idempotent; a changed revision refuses to
overwrite silently without `--allow-update`.

## States

`discovered`, `pending_metadata`, `pending_license`, `pending_lineage`
(tracked as `pending_metadata` on the record — see the schema compatibility
report), `metadata_verified` (recorded as `experimental`, i.e. documented
per policy, never `recommended`), `blocked`, `rejected`. `verified` here
means provenance-and-structure verified, not good, fast, or fitting a GPU.

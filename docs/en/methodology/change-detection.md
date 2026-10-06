# Change Detection

Revision change ≠ semantic change. A new SHA may carry README-only edits.

## Taxonomy

`model_discovered, repository_revision_changed, metadata_changed,
artifact_added, artifact_removed, artifact_changed, quant_variant_added,
quant_variant_removed, license_changed, openness_changed, lineage_changed,
architecture_changed, base_model_changed, gating_changed,
repository_disabled, repository_unavailable, repository_restored,
alignment_claim_changed, runtime_evidence_changed,
source_officiality_changed, popularity_changed`.

## Semantic fingerprints

Eight deterministic SHA-256 fingerprints, each over canonical JSON of its
domain only: `identity, license, openness, lineage, architecture,
artifact_manifest, quantization, alignment`. A dedicated `popularity`
fingerprint exists but is informational only. Volatile fields
(`retrieved_at, observed_at, downloads, likes, trending_score`) are excluded
from every semantic fingerprint, so time passing or popularity drift never
fabricates a semantic change.

## Severity and review

Severity is catalog-integrity impact, never model quality:
`critical > high > medium > low > informational`.
`license_changed / openness_changed` are critical; lineage/architecture/
withdrawal/identity-conflict are high. Critical and high map to
`review_required`; medium/low to `safe_auto_apply`; popularity/discovery to
`informational_only`. Critical changes are never silently auto-applied.

## Domain policies

- **License/openness:** history stays tied to its revision; active
  interpretation changes only after review. `unclear → open_source_ai`
  never happens without methodology-satisfying evidence.
- **Artifacts:** additions pass grouping/quant/source/size/revision/VRAM
  reclassification (size alone never implies fit). Removals become
  `unavailable/removed/superseded` in the current view; history for the old
  revision is preserved.
- **Availability:** network failure, rate limit, temporary unavailability,
  404, gated, and disabled are distinguished. One transient failure never
  deletes a model; tombstones preserve last verified revision, time, reason,
  and evidence. Restoration reuses canonical identity (no duplicate).
- **Lineage/architecture/quantization/alignment:** conflicts recorded, never
  silently overwritten; affected resolvers (Architecture Resolver, Layer Plan,
  Static Memory Model, VRAM classification) re-run only for impacted records.
- **Runtime knowledge:** revalidated separately; a runtime-docs change does
  not re-fetch every model.

# Provenance Methodology — Phase 1

> Arabic counterpart: `docs/ar/methodology/provenance-methodology-phase-01.md`

## What is recorded per intake

Every intake preserves: platform (`hugging-face`), repository ID verbatim
(never destructively lowercased — the normalized key is separate),
namespace/owner, source URL, requested revision (`main`), resolved
immutable revision (SHA) with retrieval timestamp (ISO 8601, UTC), metadata
source type, publisher-claim status, and verification status.

## Where it lives

The canonical model record carries no free-form provenance fields (its
schema forbids them), so provenance lives in linked records: one source
record per repository (with `revision`/`commit_or_revision` and an explicit
`officiality_status=unverified` note) and one evidence record per critical
field — license, openness, base model, architecture, parameter count,
context, quantization, popularity, resolved revision. The model record's
`verification.evidence_ids` binds them together.

## Field-level evidence, conflicts kept

Different fields may come from different evidence; provenance is therefore
per field, not per model. When sources disagree, both are kept with a
`conflict_detected` / `unresolved` status — priority never silently hides a
conflict.

## Revisions

`main` is a request, never an identity. `publisher/model@revision-A` and
`publisher/model@revision-B` are distinct point-in-time identities. A new
resolved revision never overwrites an old record silently; without
`--allow-update` the pipeline refuses. If no immutable revision is
returned, `resolved_revision` stays `null` with status `unverified`.

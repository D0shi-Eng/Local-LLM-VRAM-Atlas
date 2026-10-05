# Catalog Population Methodology (Phase 4)

> Controlled snapshot. 25–50 model releases, up to ~200 artifact variants.
> Sequential, budgeted, anonymous (`token=False`). No crawl of the Hub.

## Passes

A. Official publisher models in relevant parameter ranges.
B. GGUF-tagged variants for qualified base families.
C. Specialist quantizer derivatives.
D. Native low-bit / ternary candidates (evidence-gated downstream).
E. Alignment-modified variants (claims only).

Every pass is capped; results are deduplicated before metadata retrieval.
See `src/atlas/catalog/discovery.py` and `catalog/sources/discovery-registry.json`.

## Writes

Dry-run by default (`atlas discover candidates`, `atlas intake` without
`--write`). Explicit apply persists atomically (`atomic_write_json`) with
idempotency on `(repo, resolved revision, artifacts)`. One malformed
candidate never aborts the run; systemic schema/security failures stop it.

## Identity

`platform:repo@revision [variant]`; timestamps never enter identity. See
`src/atlas/catalog/identity.py`. Mirrors and derivatives are never collapsed.

## Related

- `huggingface-adapter.md`, `model-intake.md`, `source-registry.md`
- `artifact-methodology.md`, `provenance-methodology.md`

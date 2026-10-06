# Catalog Views Methodology

> Generated from canonical records. Never hand-edited. Deterministic order.

## Tiers

`catalog/views/4gb|8gb|12gb|16gb/` each contain `view.json` plus
`index.en.md` / `index.ar.md`. Sections are explicit fit states:

Verified Fit, Estimated Fit, Indeterminate Candidates, Does Not Fit,
Insufficient Evidence (plus `unsupported` where applicable).

A 6 GiB artifact never becomes an "8GB model" by size alone. Lower-bound-only
without a trustworthy upper bound stays `indeterminate`/`insufficient`,
never `estimated_fit`. See `static-vram-classification.md` and
`src/atlas/catalog/tiering.py`.

Storage bands (`remote_artifact_under_8_gib`) are navigation aids only and
never claim VRAM compatibility.

## Special views

`high-compression/`, `native-low-bit/`, `ternary/`, `uncensored/`,
`abliterated/`, `heretic/` — each with `view.json` + EN/AR pages from the
same data. See `special-variant-classification.md`.

## Manifest

`catalog/manifest.json` (`catalog_version 0.4.0`, pre-1.0) lists model ids
deterministically for future consumers without duplicating full records.

## Related

- `vram-tier-methodology.md`, `runtime-support-methodology.md`
- `generated-documentation-policy.md`

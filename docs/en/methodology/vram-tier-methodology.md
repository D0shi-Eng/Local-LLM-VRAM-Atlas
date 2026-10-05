# VRAM Tier Methodology

> Arabic counterpart: `docs/ar/methodology/vram-tier-methodology.md`

## Tiers and units

The official Atlas tiers are **4GB, 8GB, 12GB, 16GB** (`src/atlas/vram/`).
Internally everything is canonical bytes; GiB is a display conversion and GB
(decimal) is never mixed into calculations. A tier label is a user-facing
category; the authoritative value is always the byte figure beside it. Nominal
capacity follows policy `atlas-tier-nominal-v1` (tier GiB in bytes); usable
capacity is lower and will enter later through a calibrated
`system_headroom_profile`, never through a hidden constant.

## Range-based classification

Given a trustworthy `[lower, upper]` range and a tier capacity:

- `upper ≤ capacity` → `estimated_fit`
- `lower ≤ capacity < upper` → `indeterminate_fit`
- `lower > capacity` (trustworthy lower) → `estimated_not_fit`
- no trustworthy bound, or an unsupported architecture →
  `insufficient_evidence` / `unsupported`

`verified_fit` requires a real measurement and cannot be produced in Phase 2;
there is no `tight fit` language until a headroom policy is calibrated, and no
fixed percentage margin is applied silently.

## What classification is not

Artifact bytes alone never produce a fit verdict: a 6 GiB weight file says
`artifact_weight_storage ≈ 6 GiB`, never `Fits 8GB`. A regression test
forbids the file-size-to-fit shortcut. The classifier may report an
`estimated_minimum_nominal_tier_gb` when evidence allows, but **Recommended
VRAM stays deferred** (`recommendation_headroom_status: not_calibrated`)
until runtime measurements and a headroom policy exist. Display/GPU driver and
OS consumption likewise wait for the system-headroom profile instead of a
global invented number.

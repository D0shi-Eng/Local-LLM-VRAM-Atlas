# Publication Readiness Data Policy

> Arabic counterpart: `docs/ar/methodology/publication-readiness-data-policy.md`

## What readiness decides

Publication readiness decides whether the **data layer** is strong enough for a later
publication step. It does not publish, package, mirror, tag, upload or prepare
a public tree, and it does not choose a project license.

## Default technical target

At least one `STRICT_READY` recommendation in each of the 4 GB, 8 GB, 12 GB and
16 GB tiers.

If any tier has zero, the readiness report must state **TIER COVERAGE BLOCKER**.
Engineering can still pass; publication readiness defaults to **NOT READY**
unless the owner explicitly accepts reduced coverage.

## Hard rules

1. No policy threshold, classifier state or source-class rule is relaxed to
   produce a non-zero count.
2. No strict recommendation exists without persisted, walkable evidence for
   every gate.
3. No manual override exists, and no waiver by popularity or brand exists.
4. Historical evidence sidecars are never fabricated.
5. The project code license is fixed at Apache-2.0 and is recorded in `LICENSE`
   and `NOTICE`. Per-model licensing is still evaluated per record, so the
   readiness payload keeps a `license_decision_required` flag describing whether
   an individual candidate's licence is acceptable for recommendation, which is
   a separate question from the repository's own licence.

## Evidence gap matrix

Every Core candidate is reported across identity, current provenance, license,
architecture, runtime, independent quality, VRAM, retention and the general /
coding / reasoning axes, plus its strict tier eligibility. Status values are
categorical (`present`, `missing`, `refused`). No numerical percentages are
invented and no calibrated confidence is produced.

## Bilingual views

Generated recommendation and evidence-gap views are produced in English and
Arabic from one canonical payload so the two languages cannot diverge. An empty
view is written as an explicitly empty state, never omitted and never padded.

## Alignment variants are non-blocking

`uncensored`, `abliterated` and `heretic` releases require exact-variant quality
evidence. Failing to obtain it does **not** by itself block publication: they may
remain Experimental / Unevaluated with clear labels. An alignment variant with
no *declared* lineage is a lineage problem and is reported as `BLOCKED`.

## Arabic quality is optional for a global release

Arabic-specific model performance evidence is desirable but is not a mandatory
blocker unless the product explicitly promises Arabic model-quality
recommendations. A bilingual interface does not mean every model needs an Arabic
evaluation. Where no credible Arabic-specific result exists, Arabic quality
stays `unknown`; "multilingual" claims are never used as Arabic evidence.

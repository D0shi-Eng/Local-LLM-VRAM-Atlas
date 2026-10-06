# Contribution and Data-Quality Policy

> Arabic counterpart: `docs/ar/governance/contribution-policy.md`

## Status

The quality bar is defined for the implementation and its schemas. Catalog
policy exists so the bar is fixed before any data arrives.

## What counts as a contribution

A contribution is a validated JSON record (or a correction to one) with complete
provenance: source records, evidence links, retrieval timestamps, and revisions
where reproducibility matters. Opinions, rankings from memory, and unsourced
specifications are not contributions.

## Quality bar

- Every important claim carries a verification status from the evidence policy;
  `unknown` is an acceptable, honest value.
- Numbers carry units (GiB vs GB, billions of parameters, tokens of context) and,
  for measurements, the conditions under which they were taken.
- File size is never submitted as VRAM usage; popularity signals are never
  submitted as quality evidence; a file extension is never submitted as runtime
  support.
- Publisher text is labeled `publisher_claim`; community text is labeled
  community report; neither is relabeled upward without new evidence.
- Corrections preserve history: superseded and deprecated records keep their
  reason instead of being silently deleted.

## Review

Records advance through `discovered`, `pending_*`, `experimental`, `verified`, and
only then possibly `recommended`, `rejected`, or `deprecated`. Each transition
requires the evidence the schemas demand. Reviewers check that evidence supports
the claim, not merely that fields are filled.

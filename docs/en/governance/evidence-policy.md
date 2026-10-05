# Evidence Policy

> Arabic counterpart: `docs/ar/governance/evidence-policy.md`

## Principle

The Atlas is evidence-first, not popularity-first. Likes, downloads, trending flags,
vendor marketing, and community enthusiasm are recorded for what they are; none of
them is a benchmark.

## Separation of statement kinds

Every claim belongs to exactly one kind, and the kinds are never merged:

1. Source facts (what the artifact and its metadata observably are).
2. Publisher claims (what the publisher says about its own model).
3. Quantizer claims (what the quantizer says about its own artifact).
4. Independent benchmark results (reproducible, third-party measurements).
5. Atlas results (measured inside this project under documented conditions).
6. Community reports (issues, discussions, forum posts).

## Verification statuses

`unknown`, `unverified`, `estimated`, `publisher_claim`, `quantizer_claim`,
`independently_verified`, `atlas_verified`. These are not synonyms. A publisher claim
never becomes an independent fact by repetition, and missing data is recorded as
`unknown` or `unverified` — never filled in with assumptions.

## Provenance requirement

Any record with status `independently_verified` or `atlas_verified` must reference
at least one evidence record (`evidence_ids`), and each evidence record points to a
source record with URL, publisher, source type, retrieval timestamp, relevant
revision, and verification status. The schema enforces the presence of `evidence_ids`;
reviewers enforce that the evidence actually supports the claim. Evidence records
reference sources; they do not duplicate long external content.

## Source hierarchy

- **Tier A (primary authoritative):** official model repositories, official developer
  documentation, official licenses, official runtime documentation, official
  specifications, original papers.
- **Tier B (strong independent):** reputable independent benchmarks, peer-reviewed or
  reproducible evaluations, reputable independent technical measurements.
- **Tier C (specialist derivative):** quantizer repositories, quantization
  specialists, reproducible technical reports.
- **Tier D (community):** GitHub issues, Hugging Face discussions, Reddit, Discord,
  forum reports. Useful for discovering problems; never automatically a fact.

Primary official sources are always preferred over secondary coverage. A link pointing
at a moving branch (`main`/`master`) is not an immutable revision; reproducibility
requires a recorded commit, hash, or tag.

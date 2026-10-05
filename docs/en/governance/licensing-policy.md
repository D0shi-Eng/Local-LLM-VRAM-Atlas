# Licensing Policy

> Arabic counterpart: `docs/ar/governance/licensing-policy.md`

## Two separate questions

The Atlas keeps two licensing questions strictly apart:

1. **Under what license is the Atlas code itself distributed?**
   Answer: **Apache License 2.0.** The decision is recorded in the repository
   `LICENSE` file and in `NOTICE`, and is reflected in `pyproject.toml`.
2. **Under what license is each model artifact distributed?**
   Answered per model, per record, from the project's first intake onward.

The first question has one answer for the whole repository. The second has a
different answer for every record, and none of those answers is Atlas's to give.

## What the Apache-2.0 grant covers, and what it does not

The Apache-2.0 grant covers **Atlas-authored material only**:

| Covered by Apache-2.0 | Not covered by Apache-2.0 |
|---|---|
| Python source under `src/atlas/` | Third-party model weights and their derivatives |
| JSON Schema specifications under `schemas/` | Model licences, which vary per upstream project |
| Tests and synthetic fixtures under `tests/` | Benchmark results published by third parties |
| Generated documentation under `docs/` | Publisher documentation quoted as evidence |
| Visual-identity assets under `assets/branding/` | Trademarks, logos and product names of any party |
| Canonical records authored by the Atlas | Runtime and library licences (Python, `jsonschema`, `huggingface_hub`, `pytest`, `ruff`) |

The repository contains **no model weights**. Atlas catalogues and analyzes
metadata and published evidence about external models; it does not relicence
them, redistribute them, or transfer ownership of them. See `NOTICE`.

## License kinds the catalog distinguishes

Project code license, model weights license, base model license, quantized
derivative license, dataset license, custom model license, restricted license.
A quantized derivative can carry different terms than its base model; the Atlas
records both instead of inheriting one from the other.

## Openness classification

```text
open_source_ai / open_weights_permissive / open_weights_restricted
source_available / proprietary / unclear
```

Downloadable weights alone never imply `open_source_ai`. When the label
`open_source_ai` is used, the record cites the definition standard applied
(baseline: Open Source AI Definition 1.0, Open Source Initiative) as an
informational reference, not as a legal ruling by the Atlas. When in doubt,
the value is `unclear`.

## Recording practice

Licenses use SPDX identifiers where the license is SPDX-listed; custom licenses
keep their own identifiers and are never coerced into MIT or Apache. Each record
stores `license_id`, `license_name`, `license_url`, `license_source`,
`commercial_use_status`, `redistribution_status`, `derivative_use_status`,
`license_notes`, and `verification_status`, with unclear terms recorded as
`unclear`. The Atlas never gives definitive legal advice; it records what the
source says and how well that was verified.

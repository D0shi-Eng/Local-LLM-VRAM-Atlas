# Evidence Gaps Methodology

Evidence gaps are a **feature of the catalog**, not a failure. Atlas reports
what it does not know so that absence is never mistaken for strength or for
weakness.

## Reported gap categories

| Category | Meaning |
|---|---|
| `missing_independent_quality_evidence` | No independent evaluation attached |
| `missing_quant_retention_evidence` | Quantized artifact with no exact quant benchmark |
| `missing_vram_fit_evidence` | No tier with a trustworthy fit verdict |
| `missing_runtime_evidence` | No runtime compatibility hint for the format |
| `alignment_variant_unevaluated` | Uncensored/abliterated/heretic variant without its own evidence |
| `arabic_quality_unknown` | No Arabic-specific evaluation exists |
| `architecture_unresolved` | Architecture unknown, blocking VRAM estimation |
| `publisher_only_quality` | Only publisher-reported results exist |

## Current catalog gaps (34 records)

- missing independent quality evidence: **34**
- missing VRAM fit evidence: **34** (23 `insufficient_evidence`, 11 `unsupported`)
- missing quantization retention evidence: **8**
- alignment variants unevaluated: **3**
- architecture unresolved: **10**
- Arabic quality unknown: **34**
- publisher-only quality: **3**

Zero gaps in runtime evidence: every catalog record's format has at least one
documented runtime hint.

## How to read a gap

A missing benchmark means **unevaluated**, not failed. A model listed under
`missing_vram_fit_evidence` is not a poor VRAM fit; Atlas simply cannot prove
one. No gap is ever converted into a zero score, a negative score or a
downgrade in an existing classification.

## Why gaps are surfaced

Hiding gaps would make an empty catalog look authoritative. The gap report and
the `quality gaps` CLI command exist so a reader can tell the difference
between "Atlas has no evidence" and "Atlas found evidence of a problem".

## Resolution path

A gap closes only through new evidence under the same rules as any other claim:

- an independent evaluation with an exact model identity, or
- a trustworthy VRAM upper bound under documented conditions, or
- an exact quantized-variant benchmark, or
- a documented Arabic-specific evaluation.

Closing a gap by inference, popularity, size or brand is not permitted.
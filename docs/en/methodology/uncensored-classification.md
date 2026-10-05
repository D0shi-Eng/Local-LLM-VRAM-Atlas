# Uncensored Classification Methodology

> Arabic counterpart: `docs/ar/methodology/uncensored-classification.md`

## Separate labels, separate evidence

`uncensored`, `abliterated`, and `heretic` are not interchangeable scientific terms.
The record keeps them in distinct fields: `alignment_variant` (one of `standard`,
`uncensored`, `abliterated`, `heretic`, `other`, `unknown`), `uncensored_claimed`,
`uncensoring_method`, `method_documented`, `base_model`, `variant_author`,
`variant_source`, `capability_retention_evidence`, `refusal_evaluation`, and
`verification_status`.

## The central rule

Uncensored does not mean better. It does not mean smarter, safer, more accurate,
or lower hallucination. Abliteration alone is not evidence of capability
retention. Intelligence, accuracy, safety, and refusal behavior are recorded
independently, each with its own evidence — an alignment label never substitutes
for any of them.

## Practice

An uncensored claim without a documented method stays exactly that: a claim, with
`method_documented: false` and the appropriate verification status. Community
assertions about a variant's behavior are community reports until an independent
or Atlas evaluation exists. As elsewhere, `unknown` is recorded as `unknown`.

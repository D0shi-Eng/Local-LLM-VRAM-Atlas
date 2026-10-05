# Metadata Verification

> Arabic counterpart: `docs/ar/methodology/metadata-verification.md`

## Meaning of `metadata_verified`

In Phase 1, `metadata_verified` means exactly this: the required
metadata for this stage was obtained, its provenance and structure were
checked under the rules. It does not mean the model is good, smart, fast,
fitting a VRAM budget, recommended, benchmark-verified, or safety-verified.

## What is checked

Schema conformance of the canonical candidate, the source record, and all
nine evidence records; presence of requested vs. resolved revision;
license normalization without force-mapping; lineage recorded as declared,
not verified; artifact names and source-reported sizes stored without
downloading; popularity kept as popularity; `unknown`/`null` preserved
(`null` never becomes `0`, `unknown` never becomes `false`).

## What is not done

No parameter inference from repository names (`Model-7B` alone proves
nothing). No file-size-to-VRAM inference (a dedicated regression test
locks this: the canonical record carries no `vram` block at all in
Phase 1). No advertised-context passed off as tested context. No runtime
claim (`works with llama.cpp`) upgraded without a runtime test. No
`uncensored` label treated as a capability verdict.

## License and openness separation

`raw_license_value`, normalized id, SPDX verdict, source, and verification
status are stored separately. A permissive weight license yields
`open_weights_permissive`, never `open_source_ai`, which additionally
requires the full OSI criteria with a cited reference. Custom licenses
keep their literal id. No legal advice is given; unclear stays `unclear`.

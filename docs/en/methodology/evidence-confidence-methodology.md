# Evidence and Confidence Methodology

> Arabic counterpart: `docs/ar/methodology/evidence-confidence-methodology.md`

## Every memory number carries its source

Memory figures use the evidence classes in `src/atlas/evidence_classes.py`:
`atlas_measured`, `independently_measured`, `runtime_documented`,
`publisher_measured`, `calculated_from_verified_metadata`,
`calculated_from_source_metadata`, `estimated`, `filename_inferred`,
`community_report`, `publisher_claim`, `quantizer_claim`, `unknown`. An
ordinal comparison (`stronger_than`) exists for triage; numeric confidence
scores such as `0.92` are forbidden without a justified scientific model.

## Measured, calculated, estimated — never mixed

- **Measured** requires a real measurement with recorded hardware, runtime,
  context, batch, and method. A formula application is never called a
  measurement, and third-party numbers stay attributed to their origin —
  never relabeled Atlas-measured — with full conditions or not used as hard
  calibration.
- **Calculated** means known inputs plus a known versioned formula, with no
  hidden empirical fitting.
- **Estimated** means assumptions or ranges exist, and every assumption is
  recorded alongside the number.

Publisher statements remain publisher claims no matter how plausible;
community channels (forums, chat logs) may motivate investigation but never
fix the mathematical foundation, and any performance numbers encountered by
accident never become rankings: memory and format analysis covers arithmetic only, and
quantization size never implies quality (`Q5 > Q4 > Q3` is not a verdict).

# External Measurement Evidence Methodology

> Arabic counterpart: `docs/ar/methodology/external-measurement-evidence.md`

## Atlas stores, never performs

The Atlas performs no measurements. The registry (`src/atlas/measurements/`)
structures externally reported VRAM observations with full conditions:
measurement id, model and revision, artifact variant, runtime and version,
backend, GPU and driver, OS, RAM, context, batch/sequences, KV format,
offload mode, reported bytes, stage, method, source, origin, and date.

## Origins stay explicit

`official_runtime_measurement`, `publisher_measurement`,
`independent_measurement`, `community_measurement`. An external measurement
is never relabeled `atlas_measured`, and calculated values are never stored
as measured — the schema forbids it structurally (official claims require a
source). Only a tiny number of official-shaped examples validate the schema;
no forum crawling is performed.

## Calculated versus measured

`calculated` (known inputs plus a known formula) and `measured` (a real
observation under documented conditions) are different domains kept in
different records. `verified_fit` can only ever rest on sufficiently
documented external measurement, never on Atlas calculation.

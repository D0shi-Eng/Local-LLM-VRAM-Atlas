# Runtime records

> Arabic counterpart: [`README_AR.md`](README_AR.md)

This directory is the declared home for **persisted runtime records** — one JSON
record per runtime, validated against [`schemas/runtime.schema.json`](../../schemas/runtime.schema.json).

## Current state: empty, deliberately

There are **no persisted runtime records yet**, and this directory stays in the
repository with this file rather than being deleted, because the path is part of
the published contract and the runtime schema is part of the public surface.

Nothing here is missing data that ought to be filled in. It is a reserved
address for a record type that the project does not yet persist.

## Where runtime knowledge actually lives today

| Concern | Location |
|---|---|
| Runtime knowledge base, derived from documentation only | [`src/atlas/runtimes/knowledge.py`](../../src/atlas/runtimes/knowledge.py) |
| Runtime record contract | [`schemas/runtime.schema.json`](../../schemas/runtime.schema.json) |
| Runtime evidence classes and identity | [`schemas/evidence.schema.json`](../../schemas/evidence.schema.json) |
| How runtime support is evaluated | [`docs/en/methodology/runtime-support-methodology.md`](../../docs/en/methodology/runtime-support-methodology.md) |
| How the runtime knowledge model is built | [`docs/en/methodology/runtime-knowledge-model.md`](../../docs/en/methodology/runtime-knowledge-model.md) |

## What belongs here when it exists

One file per runtime, named by runtime id, conforming to
`runtime.schema.json`. A runtime record states:

- which container formats the runtime is documented to support;
- the evidence level of that documentation (publisher documentation is not
  independent verification);
- backend and offload support, and how completely each is documented;
- **scope limits**, carried on the record rather than dropped.

## The rule that keeps this directory empty for now

A runtime is recorded only when its compatibility claim is **documented by the
runtime's own publisher**. An observed local run, a community report, or an
inference from a filename does not create a runtime record.

See the [runtime support methodology](../../docs/en/methodology/runtime-support-methodology.md)
for the full rule and the Arabic counterpart of this note.
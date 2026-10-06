# Data Flow (Concept)

> Arabic counterpart: `docs/ar/architecture/data-flow.md`

## Status

Concept only. This document records the intended flow shape; the implemented
scheduled, or connected to any external service.

## Intended pipeline

```text
Public Model Sources
        ↓
Discovery
        ↓
Metadata Extraction
        ↓
Provenance Resolution
        ↓
License Gate
        ↓
Architecture Detection
        ↓
Quantization Detection
        ↓
Runtime Compatibility
        ↓
VRAM Classification
        ↓
Evidence Aggregation
        ↓
Quality Qualification
        ↓
Human/Automated Review
        ↓
Catalog
```

## Rules attached to each stage

- **Discovery** finds candidates; it never promotes them. New models enter as
  `discovered`, never as `recommended`.
- **Metadata Extraction** is metadata-first: no weights are downloaded to inspect a model.
- **Provenance Resolution** rebuilds the lineage chain (variant, quantized model,
  modified model, base model, original family) before any quality statement.
- **License Gate** blocks records whose license is unresolved from advancing to
  `verified` or `recommended`.
- **Runtime Compatibility** binds every support statement to runtime, version, and
  backend. A file extension is not a support statement.
- **VRAM Classification** separates weight file size from measured, estimated,
  minimum, and recommended VRAM, always with conditions attached.
- **Evidence Aggregation** attaches each important claim to its source and tier;
  community reports stay labeled as community reports.
- **Quality Qualification and Review** keep `verified` (data documented per policy)
  separate from `recommended` (quality gates additionally passed).

## Automation boundaries

Future automation may observe public hubs, official organizations, quantization
repositories, runtime projects, and official releases, and it must be able to discover
previously unknown publishers rather than working from a hard-coded vendor list.
Automation must never auto-trust: every promotion between lifecycle states requires
the evidence the schemas demand. No crawler, watcher or scheduler exists.

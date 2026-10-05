# Data Flow — Phase 1 (Implemented)

> Arabic counterpart: `docs/ar/architecture/phase-01-data-flow.md`

## Status

Implemented and live-tested against 7 real repositories on 2026-10-05.
Phase 0's concept flow is unchanged; this document names the actual code.

## Actual pipeline

```text
Hugging Face Public API (anonymous, token=False, timeout)
        │
        ▼
HuggingFaceSourceClient (src/atlas/intake/hf_client.py)
        │  read-only model_info + files_metadata; failure mapping;
        │  never snapshot/download/upload
        ▼
RawModelMetadata DTO (src/atlas/intake/models.py)
        │  SDK-independent boundary; original repo_id preserved
        ▼
Normalizer (src/atlas/intake/normalize.py)
        │
        ├── License Resolver (licenses.py + spdx.py)
        ├── Lineage Resolver (lineage.py)
        ├── Artifact Classifier (in normalize.py: GGUF/safetensors,
        │   filename-inference only) + Weight Guard (weight_guard.py)
        └── Provenance Builder (provenance.py: 1 source + 9 evidence records)
        │
        ▼
Canonical Model Record (dict, no vram block in Phase 1)
        │
        ▼
JSON Schema Validation (atlas.validation.validator, exit 0/1/2)
        │
        ▼
Atomic Persistence (store.py: temp file + os.replace)
        │
        ▼
catalog/models/<model-id>.json + catalog/sources/<id>.json
  + catalog/evidence/<id>.json (+ catalog/snapshots/*.raw.json audit input)
```

Cross-cutting: `url_safety.py` (SSRF guard incl. numeric-IP obfuscation),
`format.py` (single bytes→GiB helper), `errors.py` (failure taxonomy),
`source_registry.py` (9-entry trusted list), CLI (`atlas/cli/main.py`:
inspect / intake --write / validate / sources --check).

"""Catalog manifest: deterministic machine-readable index."""

from __future__ import annotations

CATALOG_VERSION = "0.4.0"
SOURCE_REGISTRY_VERSION = "0.1.0"
QUANT_REGISTRY_VERSION = "0.2.0"


def build_manifest(
    *,
    generated_at: str,
    model_ids: list[str],
    artifact_count: int,
    schema_versions: dict[str, str] | None = None,
) -> dict:
    """Build a deterministic manifest (sorted ids, no duplication)."""
    unique = sorted(set(model_ids))
    return {
        "catalog_version": CATALOG_VERSION,
        "generated_at": generated_at,
        "model_count": len(unique),
        "artifact_count": int(artifact_count),
        "source_registry_version": SOURCE_REGISTRY_VERSION,
        "quant_registry_version": QUANT_REGISTRY_VERSION,
        "schema_versions": schema_versions
        or {
            "model": "0.1.0",
            "artifact": "0.2.0",
            "source": "0.1.0",
            "evidence": "0.1.0",
            "measurement": "0.3.0",
            "memory-estimate": "0.3.0",
            "architecture": "0.3.0",
            "runtime": "0.3.0",
            "benchmark": "0.1.0",
            "quantization": "0.2.0",
        },
        "model_ids": unique,
    }

"""Artifact catalog records from source-reported siblings.

No downloads. Reuses artifact grouping: split shards stay together,
quant variants stay separate, BF16/projector/tokenizer/config/index
companions are recorded apart from primary weights.
"""

from __future__ import annotations

from atlas.artifact.grouping import group_siblings
from atlas.intake.store import canonical_json_bytes
from atlas.quant.detection import detect_from_filename


def _container_from_extension(ext: str, filename: str) -> str:
    lowered = (ext or "").lower()
    if lowered == ".gguf":
        return "GGUF"
    if lowered == ".safetensors":
        return "safetensors"
    if lowered in (".bin", ".pt", ".pth", ".ckpt", ".onnx"):
        return lowered.lstrip(".")
    if "mmproj" in filename.lower():
        return "GGUF"
    return "unknown"


def build_artifact_records(
    *,
    model_id: str,
    revision: str | None,
    siblings: list[dict],
) -> tuple[list[dict], list[str]]:
    """Group siblings into artifact-set dicts conforming to artifact.schema.json."""
    sets, _aux, warnings = group_siblings(siblings, model_id=model_id, revision=revision)
    records: list[dict] = []
    for s in sets:
        files = [
            {
                "filename": f.filename,
                "path": f.path,
                "extension": f.extension or None,
                "source_reported_size_bytes": f.source_reported_size_bytes,
            }
            for f in s.files
        ]
        records.append(
            {
                "schema_version": "0.2.0",
                "artifact_set_id": s.artifact_set_id,
                "model_id": s.model_id,
                "revision": s.revision,
                "variant": s.variant,
                "format": s.format if s.format != "unknown" else "unknown",
                "kind": s.kind,
                "files": files,
                "shard_count": s.shard_count,
                "shard_total": s.shard_total,
                "shards_complete": s.shards_complete,
                "total_source_reported_bytes": s.total_source_reported_bytes,
                "primary_weight_bytes": s.primary_weight_bytes,
                "auxiliary_bytes": s.auxiliary_bytes,
                "companion_components": list(s.companion_components or []),
                "verification_status": "source_reported",
            }
        )
    return records, list(warnings)


def quant_candidate_for(filename: str) -> dict:
    """Filename-only quant hint; always filename_inferred, never verified."""
    det = detect_from_filename(filename)
    return {
        "quant_name": det.get("quant_name"),
        "quant_family": det.get("quant_family"),
        "detection_method": det.get("detection_method", "unknown"),
        "registry_id": det.get("registry_id"),
        "verification": "filename_inferred" if det.get("quant_name") else "unknown",
    }


def storage_band_label(total_bytes: int | None) -> str:
    """Non-VRAM storage band; naming never claims VRAM compatibility."""
    if not isinstance(total_bytes, int) or total_bytes < 0:
        return "remote_artifact_size_unknown"
    gib = total_bytes / (1024**3)
    if gib < 4:
        return "remote_artifact_under_4_gib"
    if gib < 8:
        return "remote_artifact_under_8_gib"
    if gib < 12:
        return "remote_artifact_under_12_gib"
    if gib < 16:
        return "remote_artifact_under_16_gib"
    return "remote_artifact_over_16_gib"


def canonical_artifact_bytes(records: list[dict]) -> bytes:
    """Deterministic encoding for artifact record lists."""
    return canonical_json_bytes({"artifacts": sorted(records, key=lambda r: r["artifact_set_id"])})

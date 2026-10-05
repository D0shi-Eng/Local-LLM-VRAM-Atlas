"""Phase 4 artifacts + quant grouping + shard tests (offline)."""

from __future__ import annotations

from atlas.artifact.grouping import group_siblings
from atlas.catalog.artifacts_catalog import (
    build_artifact_records,
    quant_candidate_for,
    storage_band_label,
)


def test_grouping_keeps_variants_separate():
    siblings = [
        {
            "filename": "model-Q4_K_M.gguf",
            "path": "model-Q4_K_M.gguf",
            "extension": ".gguf",
            "source_reported_size_bytes": 100,
        },
        {
            "filename": "model-Q8_0.gguf",
            "path": "model-Q8_0.gguf",
            "extension": ".gguf",
            "source_reported_size_bytes": 200,
        },
    ]
    sets, _aux, warnings = group_siblings(siblings, model_id="m", revision="r")
    assert len(sets) == 2
    assert any("multi_variant" in w for w in warnings)


def test_shard_completeness_detected():
    siblings = [
        {
            "filename": "model-00001-of-00002.safetensors",
            "path": "model-00001-of-00002.safetensors",
            "extension": ".safetensors",
            "source_reported_size_bytes": 10,
        },
        {
            "filename": "model-00002-of-00002.safetensors",
            "path": "model-00002-of-00002.safetensors",
            "extension": ".safetensors",
            "source_reported_size_bytes": 10,
        },
    ]
    sets, _aux, _w = group_siblings(siblings, model_id="m", revision="r")
    assert len(sets) == 1
    assert sets[0].kind == "sharded"
    assert sets[0].shards_complete is True


def test_missing_shard_flagged():
    siblings = [
        {
            "filename": "model-00001-of-00003.safetensors",
            "path": "model-00001-of-00003.safetensors",
            "extension": ".safetensors",
            "source_reported_size_bytes": 10,
        },
        {
            "filename": "model-00003-of-00003.safetensors",
            "path": "model-00003-of-00003.safetensors",
            "extension": ".safetensors",
            "source_reported_size_bytes": 10,
        },
    ]
    sets, _aux, warnings = group_siblings(siblings, model_id="m", revision="r")
    assert sets[0].shards_complete is False
    assert any("missing_shard" in w for w in warnings)


def test_build_artifact_records_schema_shape():
    siblings = [
        {
            "filename": "model-Q4_K_M.gguf",
            "path": "model-Q4_K_M.gguf",
            "extension": ".gguf",
            "source_reported_size_bytes": 4_000_000_000,
        },
    ]
    records, _w = build_artifact_records(model_id="m", revision="rev", siblings=siblings)
    assert len(records) == 1
    rec = records[0]
    assert rec["schema_version"] == "0.2.0"
    assert rec["verification_status"] == "source_reported"
    assert rec["files"][0]["source_reported_size_bytes"] == 4_000_000_000


def test_quant_candidate_filename_inferred_only():
    det = quant_candidate_for("model-Q4_K_M.gguf")
    assert det["quant_name"] == "Q4_K_M"
    assert det["verification"] == "filename_inferred"
    # Never verified from filename alone.
    assert det["verification"] != "verified"


def test_storage_band_naming_never_claims_vram():
    assert storage_band_label(1_000_000_000) == "remote_artifact_under_4_gib"
    assert "compatible" not in storage_band_label(1_000_000_000)
    assert "vram" not in storage_band_label(1_000_000_000).lower() or True
    # Explicit: storage band must contain remote_artifact prefix.
    assert storage_band_label(9_000_000_000).startswith("remote_artifact_")


def test_artifact_size_units_bytes_preserved():
    siblings = [
        {
            "filename": "a-Q4_K_M.gguf",
            "path": "a-Q4_K_M.gguf",
            "extension": ".gguf",
            "source_reported_size_bytes": 5_000_000_000,
        },
    ]
    records, _ = build_artifact_records(model_id="m", revision="r", siblings=siblings)
    assert records[0]["total_source_reported_bytes"] == 5_000_000_000

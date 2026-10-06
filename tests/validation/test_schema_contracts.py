"""Schema contracts validate canonical records and measurements."""

from atlas.validation.validator import SUPPORTED_KINDS, validate_record


def _architecture_record(**overrides):
    record = {
        "schema_version": "0.3.0",
        "architecture_family": "llama",
        "requested_revision": "main",
        "resolution_status": "resolved",
    }
    record.update(overrides)
    return record


def _measurement_record(**overrides):
    record = {
        "schema_version": "0.3.0",
        "measurement_id": "m-001",
        "model_id": "org/model",
        "evidence_level": "community_measurement",
    }
    record.update(overrides)
    return record


def test_new_schema_kinds_registered():
    assert "architecture" in SUPPORTED_KINDS
    assert "measurement" in SUPPORTED_KINDS
    # Three operational contracts exist (change-event, refresh-plan,
    # discovery-checkpoint) at 0.5.0 without mutating the 10 existing schemas.
    assert "change-event" in SUPPORTED_KINDS
    assert "refresh-plan" in SUPPORTED_KINDS
    assert "discovery-checkpoint" in SUPPORTED_KINDS
    # Five quality and recommendation contracts are specified at 0.6.0 without
    # mutating any existing schema (validator kinds 13 -> 18).
    for quality_contract_kind in (
        "evaluation-result",
        "quality-profile",
        "quant-retention",
        "quality-policy",
        "recommendation-result",
    ):
        assert quality_contract_kind in SUPPORTED_KINDS
    assert len(SUPPORTED_KINDS) == 18


def test_architecture_schema_accepts_canonical():
    record = _architecture_record(
        model_type="llama",
        num_hidden_layers=32,
        num_attention_heads=32,
        num_key_value_heads=8,
        head_dim=128,
        head_dim_source="calculated",
        custom_remote_architecture=False,
        conflict_detected=False,
    )
    assert validate_record(record, "architecture") == []


def test_architecture_schema_rejects_zero_as_unknown():
    record = _architecture_record(num_hidden_layers=0)
    assert validate_record(record, "architecture") != []


def test_architecture_schema_rejects_bad_status():
    record = _architecture_record(resolution_status="confidence_92")
    assert validate_record(record, "architecture") != []


def test_measurement_schema_accepts_external():
    record = _measurement_record(
        revision="abc123",
        runtime="llama.cpp",
        measurement_stage="peak",
        measurement_method="nvidia_smi",
        reported_vram_bytes=9_000_000_000,
        source="https://example.com/evidence",
    )
    assert validate_record(record, "measurement") == []


def test_measurement_schema_rejects_atlas_measured():
    record = _measurement_record(evidence_level="atlas_measured")
    assert validate_record(record, "measurement") != []


def test_measurement_schema_requires_source_for_official():
    record = _measurement_record(evidence_level="official_runtime_measurement")
    assert validate_record(record, "measurement") != []
    record["source"] = "https://example.com/runtime-docs"
    assert validate_record(record, "measurement") == []

"""Phase 3: runtime knowledge base and external measurement registry."""

from atlas.measurements.registry import (
    MEASUREMENT_ORIGINS,
    ExternalMeasurement,
    validate_measurement,
)
from atlas.runtimes.knowledge import SUPPORT_STATUSES, list_capabilities


def test_runtime_claims_have_source_version_observed():
    capabilities = list_capabilities()
    assert len(capabilities) >= 5
    for item in capabilities:
        assert item.runtime
        assert item.runtime_version_or_revision
        assert item.support_status in SUPPORT_STATUSES
        assert item.source.startswith("https://")
        assert item.observed_at
        assert item.support_status in (
            "official",
            "documented",
            "experimental",
            "deprecated",
            "unsupported",
            "unknown",
        )


def test_runtime_knowledge_has_no_perf_numbers():
    import dataclasses

    for item in list_capabilities():
        fields = {f.name for f in dataclasses.fields(item)}
        assert "tokens_per_second" not in fields
        assert "latency" not in fields
        assert "throughput" not in fields


def test_measurement_origins_explicit():
    assert set(MEASUREMENT_ORIGINS) == {
        "official_runtime_measurement",
        "publisher_measurement",
        "independent_measurement",
        "community_measurement",
    }


def test_valid_community_measurement():
    measurement = ExternalMeasurement(
        measurement_id="m-001",
        model_id="org/model",
        revision="abc123",
        runtime="llama.cpp",
        runtime_version="b1234",
        backend="CUDA",
        gpu="RTX 4070",
        context_tokens=8192,
        reported_vram_bytes=9_000_000_000,
        measurement_stage="peak",
        measurement_method="nvidia_smi",
        source="https://example.com/evidence",
        evidence_level="community_measurement",
        observed_at="2026-10-05T00:00:00Z",
    )
    assert validate_measurement(measurement) == []


def test_atlas_measured_label_forbidden():
    measurement = ExternalMeasurement(
        measurement_id="m-002",
        model_id="org/model",
        evidence_level="atlas_measured",  # type: ignore[arg-type]
    )
    assert validate_measurement(measurement) != []


def test_official_without_source_rejected():
    measurement = ExternalMeasurement(
        measurement_id="m-003",
        model_id="org/model",
        evidence_level="official_runtime_measurement",
        source=None,
    )
    assert validate_measurement(measurement) != []


def test_official_with_source_accepted():
    measurement = ExternalMeasurement(
        measurement_id="m-004",
        model_id="org/model",
        evidence_level="official_runtime_measurement",
        source="https://example.com/runtime-docs",
    )
    assert validate_measurement(measurement) == []

"""External VRAM measurement registry: Atlas stores, never performs.

Origins stay explicit (official_runtime_measurement, publisher_measurement,
independent_measurement, community_measurement). An external measurement is
never relabeled atlas_measured, and calculated values are never stored as
measured. The registry holds a tiny number of official-shaped examples for
schema validation only; no forum crawling is performed.
"""

from __future__ import annotations

from dataclasses import dataclass

MEASUREMENT_ORIGINS = (
    "official_runtime_measurement",
    "publisher_measurement",
    "independent_measurement",
    "community_measurement",
)

MEASUREMENT_STAGES = (
    "weights_loaded",
    "kv_allocated",
    "prefill_done",
    "decoding",
    "peak",
    "unknown",
)

MEASUREMENT_METHODS = (
    "nvidia_smi",
    "runtime_reported",
    "profiler",
    "documented",
    "unknown",
)


@dataclass(frozen=True)
class ExternalMeasurement:
    """One externally reported VRAM observation with full conditions."""

    measurement_id: str
    model_id: str
    revision: str | None = None
    artifact_variant: str | None = None
    runtime: str | None = None
    runtime_version: str | None = None
    backend: str | None = None
    gpu: str | None = None
    gpu_vram: str | None = None
    driver: str | None = None
    os: str | None = None
    system_ram: str | None = None
    context_tokens: int | None = None
    batch_or_sequences: int | None = None
    kv_format: str | None = None
    offload_mode: str | None = None
    reported_vram_bytes: int | None = None
    measurement_stage: str = "unknown"
    measurement_method: str = "unknown"
    source: str | None = None
    evidence_level: str = "community_measurement"
    observed_at: str | None = None


def validate_measurement(measurement: ExternalMeasurement) -> list[str]:
    """Validate a measurement record; return error list (empty means valid)."""
    errors: list[str] = []
    if not measurement.measurement_id or not measurement.measurement_id.strip():
        errors.append("measurement_id is required")
    if not measurement.model_id or not measurement.model_id.strip():
        errors.append("model_id is required")
    if measurement.evidence_level not in MEASUREMENT_ORIGINS:
        errors.append(f"unknown origin: {measurement.evidence_level!r}")
    if measurement.evidence_level == "official_runtime_measurement" and not measurement.source:
        errors.append("official measurements require a source URL")
    if measurement.measurement_stage not in MEASUREMENT_STAGES:
        errors.append(f"unknown stage: {measurement.measurement_stage!r}")
    if measurement.measurement_method not in MEASUREMENT_METHODS:
        errors.append(f"unknown method: {measurement.measurement_method!r}")
    if measurement.reported_vram_bytes is not None and (
        isinstance(measurement.reported_vram_bytes, bool) or measurement.reported_vram_bytes <= 0
    ):
        errors.append("reported_vram_bytes must be a positive integer when present")
    if measurement.context_tokens is not None and (
        isinstance(measurement.context_tokens, bool) or measurement.context_tokens <= 0
    ):
        errors.append("context_tokens must be positive when present")
    # Atlas never performed it: the forbidden label is rejected structurally.
    if getattr(measurement, "evidence_level", None) == "atlas_measured":
        errors.append("atlas_measured is forbidden for external measurements")
    return errors

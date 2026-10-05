"""External VRAM evidence handling and candidate-level fit states (Phase 6.5).

Atlas performs no measurement. This module only:

- derives the VRAM evidence source class (V1-V5) from an already-stored
  external measurement plus its configuration completeness;
- decides whether an external measurement may support a tier verdict for one
  exact artifact, preserving runtime, context, KV format, offload, shared
  memory and hardware-tier distinctions;
- feeds the Phase 2 estimator and Phase 2 classifier with newly reacquired
  architecture inputs for one exact artifact.

Hard invariants:

- an artifact's byte size alone can never create a fit verdict;
- a measurement taken on a larger GPU is *measured memory-requirement
  evidence*, never verified fit on the target tier's hardware;
- a measurement at a context other than the Atlas baseline never becomes
  baseline-context evidence;
- CPU offload, partial offload, shared/system-memory spill and unknown runtime
  version never become a full GPU-resident fit;
- anecdotal statements (V5) can never create strict fit;
- the classifier is used unchanged, so no tier verdict is weakened.
"""

from __future__ import annotations

import json
from pathlib import Path

from atlas.closure import CLOSURE_SCHEMA_VERSION
from atlas.intake.store import atomic_write_json
from atlas.measurements.registry import MEASUREMENT_METHODS, MEASUREMENT_ORIGINS
from atlas.memory.calc_profile import ATLAS_TEXT_8K_BASELINE_V1
from atlas.memory.estimator import EstimateInputs, estimate_peak_vram
from atlas.vram.classifier import classify_all_tiers

VRAM_SOURCE_CLASSES = ("V1", "V2", "V3", "V4", "V5")

VRAM_SOURCE_CLASS_DEFINITIONS = {
    "V1": "independent reproducible measurement with exact configuration",
    "V2": "official runtime/vendor benchmark with exact configuration",
    "V3": "publisher measurement with sufficiently complete conditions",
    "V4": "structured community measurement with reproducible conditions",
    "V5": "anecdotal statement; cannot create strict fit",
}

# Fields that must be present before a measurement can be called reproducible.
_CONFIGURATION_FIELDS = (
    "revision",
    "artifact_variant",
    "runtime",
    "runtime_version",
    "backend",
    "gpu",
    "gpu_vram",
    "context_tokens",
    "offload_mode",
    "reported_vram_bytes",
)

_ORIGIN_TO_CLASS = {
    "independent_measurement": "V1",
    "official_runtime_measurement": "V2",
    "publisher_measurement": "V3",
    "community_measurement": "V4",
}

FULL_GPU_OFFLOAD = ("full", "full_gpu", "all", "none", "gpu")
NON_GPU_RESIDENT = ("cpu", "partial", "none_cpu", "layer_partial", "system_ram", "shared", "hybrid")


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    return None


def configuration_completeness(measurement: dict) -> list[str]:
    """Names of missing configuration fields for one external measurement."""
    return [name for name in _CONFIGURATION_FIELDS if measurement.get(name) in (None, "")]


def derive_vram_source_class(measurement: dict) -> str:
    """Derive the V1-V5 VRAM evidence class from origin plus completeness.

    A community measurement without exact configuration is anecdotal, and an
    official claim without a documented configuration is not a reproducible
    benchmark; both collapse to V5 rather than being promoted.
    """
    origin = str(measurement.get("evidence_level") or "")
    if origin not in MEASUREMENT_ORIGINS:
        return "V5"
    base = _ORIGIN_TO_CLASS.get(origin, "V5")
    missing = configuration_completeness(measurement)
    if missing:
        return "V5"
    if base == "V4":
        if str(measurement.get("measurement_method")) not in (
            "nvidia_smi",
            "runtime_reported",
            "profiler",
        ):
            return "V5"
        return "V4"
    return base


def fit_support(
    measurement: dict,
    *,
    tier_gb: int,
    expected_artifact_id: str | None = None,
) -> dict:
    """Can this external measurement support a tier verdict for this artifact?

    The verdict vocabulary is deliberately narrow: ``supports_measured_requirement``
    means the measurement documents a memory *requirement* under a named
    configuration. It never means the target tier's hardware was executed.
    """
    reasons: list[str] = []
    source_class = derive_vram_source_class(measurement)
    identity_state = "not_compared"
    if expected_artifact_id is not None:
        observed = str(measurement.get("artifact_variant") or "")
        identity_state = "exact" if observed == str(expected_artifact_id) else "mismatch"
        if identity_state == "mismatch":
            reasons.append(
                f"measurement artifact {observed!r} is not the candidate artifact "
                f"{expected_artifact_id!r}: a filename similarity never attaches it"
            )
    if source_class == "V5":
        reasons.append("anecdotal_or_incompletely_configured: cannot support a fit verdict")
    if str(measurement.get("measurement_method")) not in MEASUREMENT_METHODS:
        reasons.append("unknown measurement method")
    reported = _positive_int(measurement.get("reported_vram_bytes"))
    if reported is None:
        reasons.append("no reported peak VRAM value")
    context = _positive_int(measurement.get("context_tokens"))
    if context is None:
        reasons.append("context not stated: cannot be compared with the Atlas baseline")
    elif context != ATLAS_TEXT_8K_BASELINE_V1.context_tokens:
        reasons.append(
            f"context {context} differs from the Atlas baseline "
            f"{ATLAS_TEXT_8K_BASELINE_V1.context_tokens}: baseline-context evidence not "
            "established"
        )
    offload = str(measurement.get("offload_mode") or "").strip().lower()
    if not offload:
        reasons.append("offload mode unknown: full GPU residency not established")
    elif offload in NON_GPU_RESIDENT:
        reasons.append(f"offload_mode={offload}: not a full GPU-resident measurement")
    if not measurement.get("runtime_version"):
        reasons.append("runtime version unknown: evidence strength reduced")
    supports = not reasons
    return {
        "supports_measured_requirement": supports,
        "vram_source_class": source_class,
        "artifact_identity": identity_state,
        "reasons": reasons,
        "hardware_verification": "not_performed_by_atlas",
        "tier_gb": tier_gb,
        "note": (
            "A measurement on a larger GPU is measured memory-requirement evidence subject to "
            "runtime, driver, allocation, offload and context limits. It is not verified fit "
            "on the target tier's hardware."
        ),
    }


def measurements_dir(repo_root: Path) -> Path:
    """Canonical external measurement directory."""
    return repo_root / "catalog" / "measurements"


def load_measurements(repo_root: Path) -> dict[str, dict]:
    """Load persisted external measurements keyed by measurement_id."""
    base = measurements_dir(repo_root)
    out: dict[str, dict] = {}
    if not base.is_dir():
        return out
    for path in sorted(base.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        measurement_id = record.get("measurement_id")
        if isinstance(measurement_id, str) and measurement_id:
            out[measurement_id] = record
    return out


FULL_ATTENTION_TYPES = ("full_attention", "attention", "self_attention")
SLIDING_ATTENTION_TYPES = ("sliding_attention", "sliding_window_attention")
# Layer types whose state cache Atlas cannot account for. Their presence
# together with full-attention layers makes the architecture hybrid, and a
# hybrid must be refused rather than estimated from the attention layers only.
UNMODELED_ATTENTION_TYPES = (
    "linear_attention",
    "ssm",
    "mamba",
    "mamba2",
    "state_space",
    "mamba_ssm",
    "recurrent",
)


def attention_regime(architecture_fields: dict) -> str:
    """Classify the declared per-layer attention pattern.

    ``standard`` means every layer is full or sliding attention.
    ``hybrid`` means unmodeled state-space layers coexist with attention
    layers, which Atlas refuses because the state cache is unknown.
    ``unknown`` means no per-layer declaration exists.
    """
    layer_types = architecture_fields.get("layer_types")
    if not isinstance(layer_types, (list, tuple)) or not layer_types:
        return "unknown"
    names = [str(t).strip().lower() for t in layer_types]
    has_attention = any(n in FULL_ATTENTION_TYPES or n in SLIDING_ATTENTION_TYPES for n in names)
    has_unmodeled = any(n in UNMODELED_ATTENTION_TYPES for n in names)
    if has_unmodeled and has_attention:
        return "hybrid"
    if has_attention and not has_unmodeled:
        return "standard"
    if has_unmodeled:
        return "state_space_only"
    return "unknown"


def _refusal(
    *,
    candidate: dict,
    reason: str,
    detail: str,
    family: str | None = None,
) -> dict:
    """Explicit refusal payload; no bound and no tier verdict is produced."""
    return {
        "schema_version": CLOSURE_SCHEMA_VERSION,
        "candidate_id": candidate["candidate_id"],
        "artifact_set_id": candidate["artifact_set_id"],
        "architecture_family": family,
        "calculation_profile_id": ATLAS_TEXT_8K_BASELINE_V1.profile_id,
        "calculation_context_tokens": ATLAS_TEXT_8K_BASELINE_V1.context_tokens,
        "estimate_status": "refused",
        "refusal_reason": reason,
        "refusal_detail": detail,
        "lower_bytes": None,
        "upper_bytes": None,
        "by_tier": {str(tier): "unsupported" for tier in (4, 8, 12, 16)},
        "tier_reasons": {str(tier): detail for tier in (4, 8, 12, 16)},
        "runtime_overhead_state": (
            "absent: no runtime memory profile carries documented overhead, so the reliable "
            "upper bound required for an estimated fit does not exist"
        ),
        "note": (
            "Refusal is a correct outcome. Artifact byte size alone can never create a fit "
            "verdict, and an unmodeled component is never counted as zero."
        ),
    }


def build_candidate_estimate(
    *,
    candidate: dict,
    architecture_fields: dict,
    advertised_max_context: int | None,
    multimodal_wrapper: bool = False,
) -> dict:
    """Estimate one exact artifact with reacquired architecture inputs.

    The Phase 2 formulas and the Phase 2 classifier are used unchanged. No
    runtime overhead profile is invented, so the upper bound stays absent and
    the classifier's own semantics decide the tier state.
    """
    from atlas.archinfo.layer_plan import build_layer_plan
    from atlas.catalog.tiering import canonical_family_for
    from atlas.closure.current_evidence import language_model_fields
    from atlas.memory.calc_profile import kv_bytes_per_element

    language_fields = language_model_fields(architecture_fields)
    family = canonical_family_for(
        language_fields.get("architectures") or language_fields.get("model_type")
    )
    regime = attention_regime(language_fields)
    if regime in ("hybrid", "state_space_only"):
        return _refusal(
            candidate=candidate,
            reason="hybrid_or_state_space_attention",
            detail=(
                f"attention regime {regime}: Atlas has no state-cache model, so estimating from "
                "attention layers alone would understate memory and could create a false fit"
            ),
            family=family,
        )

    layers = _positive_int(language_fields.get("num_hidden_layers"))
    kv_heads = _positive_int(language_fields.get("num_key_value_heads"))
    head_dim = _positive_int(language_fields.get("head_dim"))
    if head_dim is None:
        hidden = _positive_int(language_fields.get("hidden_size"))
        attn = _positive_int(language_fields.get("num_attention_heads"))
        if hidden is not None and attn is not None and hidden % attn == 0:
            head_dim = hidden // attn
    sliding_window = None
    if language_fields.get("use_sliding_window") is True:
        sliding_window = _positive_int(language_fields.get("sliding_window"))
    if layers is None or kv_heads is None or head_dim is None:
        return _refusal(
            candidate=candidate,
            reason="architecture_cache_inputs_missing",
            detail=(
                "num_hidden_layers / num_key_value_heads / head_dim are required by the "
                "standard KV equation and are not resolved from current evidence"
            ),
            family=family,
        )

    layer_plan = build_layer_plan(
        language_fields,
        global_values={
            "num_layers": layers,
            "num_key_value_heads": kv_heads,
            "num_attention_heads": _positive_int(language_fields.get("num_attention_heads")),
            "head_dim": head_dim,
        },
        source="current_config_metadata",
    )
    weight_bytes = candidate.get("artifact_weight_bytes")
    if not isinstance(weight_bytes, int) or weight_bytes <= 0:
        return _refusal(
            candidate=candidate,
            reason="artifact_weight_bytes_unavailable",
            detail="exact artifact weight bytes are unknown, so no weight component exists",
            family=family,
        )
    inputs = EstimateInputs(
        architecture_family=family,
        total_parameters=None,
        weight_bytes_verified=weight_bytes,
        effective_bits_per_weight=None,
        num_layers=layers,
        num_kv_heads=kv_heads,
        head_dim=head_dim,
        kv_bytes_per_element=kv_bytes_per_element(ATLAS_TEXT_8K_BASELINE_V1.kv_dtype or "fp16"),
        sliding_window=sliding_window if layer_plan is None else None,
        advertised_max_context=advertised_max_context,
    )
    estimate = estimate_peak_vram(
        inputs,
        ATLAS_TEXT_8K_BASELINE_V1,
        None,
        layer_plan=layer_plan,
    )
    tiered = classify_all_tiers(
        lower_bound_bytes=estimate.estimated_vram_lower_bytes,
        upper_bound_bytes=estimate.estimated_vram_upper_bytes,
        estimate_status=estimate.estimate_status,
    )
    return {
        "schema_version": CLOSURE_SCHEMA_VERSION,
        "candidate_id": candidate["candidate_id"],
        "artifact_set_id": candidate["artifact_set_id"],
        "architecture_family": family,
        "attention_regime": regime,
        "multimodal_wrapper": multimodal_wrapper,
        "multimodal_note": (
            "release ships a vision tower; the Atlas baseline profile is text-only, so encoder "
            "residency is not represented in these bounds"
            if multimodal_wrapper
            else None
        ),
        "architecture_inputs": {
            "num_layers": layers,
            "num_key_value_heads": kv_heads,
            "head_dim": head_dim,
            "sliding_window": sliding_window,
            "layer_plan_used": layer_plan is not None,
            "layer_plan_heterogeneous": bool(layer_plan.heterogeneous) if layer_plan else None,
        },
        "calculation_profile_id": ATLAS_TEXT_8K_BASELINE_V1.profile_id,
        "calculation_context_tokens": ATLAS_TEXT_8K_BASELINE_V1.context_tokens,
        "estimate_status": estimate.estimate_status,
        "evidence_basis": estimate.evidence_basis,
        "formula_refs": list(estimate.formula_refs),
        "device_weight_bytes": estimate.components.device_weight_bytes,
        "kv_or_state_cache_bytes": estimate.components.kv_or_state_cache_bytes,
        "lower_bytes": estimate.estimated_vram_lower_bytes,
        "upper_bytes": estimate.estimated_vram_upper_bytes,
        "unknown_components": list(estimate.unknown_components),
        "unsupported_components": list(estimate.unsupported_components),
        "assumptions": list(estimate.assumptions),
        "warnings": list(estimate.warnings),
        "by_tier": {str(d.tier_gb): d.classification for d in tiered.decisions},
        "tier_reasons": {str(d.tier_gb): d.reason for d in tiered.decisions},
        "runtime_overhead_state": (
            "absent: no runtime memory profile carries documented overhead, so the reliable "
            "upper bound required for an estimated fit does not exist"
        ),
        "note": (
            "Artifact byte size supplies the weight component only. The KV/cache component "
            "comes from current architecture inputs and the Atlas baseline profile. A fit "
            "verdict still requires a reliable upper bound."
        ),
    }


def external_evidence_index(*, repo_root: Path, core_set: dict) -> dict:
    """Summarize external VRAM evidence coverage for the Core set."""
    measurements = load_measurements(repo_root)
    artifact_ids = {str(c["artifact_set_id"]) for c in core_set.get("candidates", [])}
    covered: list[str] = []
    by_class: dict[str, int] = {name: 0 for name in VRAM_SOURCE_CLASSES}
    rejected: list[dict] = []
    for measurement_id, measurement in sorted(measurements.items()):
        derived = derive_vram_source_class(measurement)
        by_class[derived] = by_class.get(derived, 0) + 1
        artifact = str(measurement.get("artifact_variant") or "")
        if artifact in artifact_ids:
            covered.append(measurement_id)
        verdict = fit_support(measurement, tier_gb=0)
        if not verdict["supports_measured_requirement"]:
            rejected.append({"measurement_id": measurement_id, "reasons": verdict["reasons"]})
    return {
        "schema_version": CLOSURE_SCHEMA_VERSION,
        "measurement_count": len(measurements),
        "core_artifacts_with_external_measurement": sorted(covered),
        "source_class_counts": by_class,
        "not_supporting_a_fit_verdict": rejected,
        "source_class_definitions": dict(VRAM_SOURCE_CLASS_DEFINITIONS),
        "note": (
            "Atlas stores external measurements and never performs any. An anecdotal or "
            "incompletely configured measurement can never create strict fit."
        ),
    }


def write_vram_evidence(
    *,
    repo_root: Path,
    estimates: list[dict],
    index: dict,
    dry_run: bool = True,
) -> dict:
    """Persist candidate-level fit states and the external-evidence index."""
    base = repo_root / "catalog" / "closure" / "vram"
    written: list[str] = []
    for estimate in estimates:
        target = base / f"{estimate['candidate_id']}.json"
        written.append(str(target))
        if not dry_run:
            atomic_write_json(target, estimate)
    index_target = base / "external-evidence-index.json"
    written.append(str(index_target))
    if not dry_run:
        atomic_write_json(index_target, index)
    return {"dry_run": dry_run, "files_written": written}


def load_candidate_estimates(repo_root: Path) -> dict[str, dict]:
    """Load persisted candidate-level estimates keyed by candidate_id."""
    base = repo_root / "catalog" / "closure" / "vram"
    out: dict[str, dict] = {}
    if not base.is_dir():
        return out
    for path in sorted(base.glob("core-*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        candidate_id = record.get("candidate_id")
        if isinstance(candidate_id, str):
            out[candidate_id] = record
    return out

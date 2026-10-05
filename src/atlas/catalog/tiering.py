"""VRAM tiering integration (Phase 4).

Uses only the established Phase 2/3 classifier. Never infers fit from
file size alone. Lower-bound-only without a trustworthy upper bound stays
indeterminate/insufficient, never estimated_fit.
"""

from __future__ import annotations

from atlas.memory.calc_profile import ATLAS_TEXT_8K_BASELINE_V1
from atlas.memory.estimator import EstimateInputs, estimate_peak_vram
from atlas.vram.classifier import classify_all_tiers
from atlas.vram.tiers import SUPPORTED_TIERS_GB

TIER_GBS = tuple(SUPPORTED_TIERS_GB)


def canonical_family_for(architecture_raw: object) -> str:
    """Map a publisher architecture name to a Phase 3 canonical KV family.

    Unknown stays unknown; BitNet/hybrid have no standard KV model. Shared by
    Phase 4 record tiering and Phase 6.5 candidate-level estimation so a
    second, divergent mapping never appears.
    """
    arch_raw = str(architecture_raw or "unknown")
    family = arch_raw.lower() if arch_raw != "unknown" else "unknown"
    # Map publisher architecture names to Phase 3 canonical KV families.
    # Unknown stays unknown; BitNet/hybrid have no standard KV model.
    if "qwen3" in family and "moe" in family:
        family = "qwen3_moe"
    elif "qwen3_5" in family or "qwen3.5" in family:
        family = "qwen3_5"
    elif "qwen3" in family:
        family = "qwen3"
    elif "qwen2" in family:
        family = "qwen2"
    elif "qwen" in family:
        family = "qwen3"
    elif "llama" in family:
        family = "llama"
    elif "mistral3" in family or "mistral_3" in family:
        family = "mistral3"
    elif "mistral" in family or "mixtral" in family:
        family = "mistral" if "mistral" in family else "mixtral"
    elif "phi" in family:
        family = "phi"
    elif "gemma4" in family or "gemma_4" in family or "gemma4unified" in family:
        family = "gemma4_unified"
    elif "gemma3" in family:
        family = "gemma3"
    elif "gemma2" in family:
        family = "gemma2"
    elif "gemma" in family:
        family = "gemma"
    elif "gptoss" in family or "gpt_oss" in family or "gpt-oss" in family:
        family = "gpt_oss"
    elif "minicpm" in family:
        family = "minicpm"
    elif "deepseek" in family:
        family = "unknown"
    elif "bitnet" in family:
        family = "unknown"
    else:
        from atlas.memory.architecture import architecture_status

        if architecture_status(family).get("status") == "unknown_family":
            family = "unknown"
    return family


def estimate_for_record(record: dict) -> dict:
    """Conservative static estimate from canonical record metadata only.

    Weight bytes come from source-reported artifact sizes; architecture
    fields come from publisher metadata. Unknowns stay unknown. No
    file-size-to-fit shortcut is applied here or downstream.
    """
    quant = record.get("quantization") or {}
    weight_bytes = quant.get("file_size_bytes")
    if not isinstance(weight_bytes, int) or weight_bytes <= 0:
        weight_bytes = None
    total_b = record.get("total_parameters_b")
    total_params = None
    if isinstance(total_b, (int, float)) and total_b > 0:
        total_params = int(total_b * 1_000_000_000)
    family = canonical_family_for(record.get("architecture"))
    bpw = quant.get("bits_per_weight")
    if not isinstance(bpw, (int, float)) or bpw <= 0:
        bpw = None
    ctx = record.get("context_length") or {}
    adv = ctx.get("advertised_max") if isinstance(ctx, dict) else None
    adv = adv if isinstance(adv, int) and adv > 0 else None
    inputs = EstimateInputs(
        architecture_family=family,
        total_parameters=total_params,
        weight_bytes_verified=weight_bytes,
        effective_bits_per_weight=float(bpw) if bpw else None,
        num_layers=None,
        num_kv_heads=None,
        head_dim=None,
        kv_bytes_per_element=2.0,
        advertised_max_context=adv,
    )
    est = estimate_peak_vram(inputs, ATLAS_TEXT_8K_BASELINE_V1, None)
    return {
        "estimate_status": est.estimate_status,
        "evidence_basis": est.evidence_basis,
        "lower_bytes": est.estimated_vram_lower_bytes,
        "upper_bytes": est.estimated_vram_upper_bytes,
        "unknown_components": list(est.unknown_components),
        "warnings": list(est.warnings),
    }


def classify_record(record: dict) -> dict:
    """Classify one canonical record across 4/8/12/16GB tiers."""
    est = estimate_for_record(record)
    tiered = classify_all_tiers(
        lower_bound_bytes=est["lower_bytes"],
        upper_bound_bytes=est["upper_bytes"],
        estimate_status=est["estimate_status"],
    )
    decisions = [
        {"tier_gb": d.tier_gb, "state": d.classification, "reason": d.reason}
        for d in tiered.decisions
    ]
    return {
        "estimate_status": tiered.estimate_status,
        "lower_bytes": tiered.lower_bytes,
        "upper_bytes": tiered.upper_bytes,
        "decisions": decisions,
        "by_tier": {str(d.tier_gb): d.classification for d in tiered.decisions},
        "estimated_minimum_nominal_tier_gb": tiered.estimated_minimum_nominal_tier_gb,
    }


def group_by_tier_state(classifications: dict[str, dict]) -> dict:
    """Group model ids per tier per fit state for generated views."""
    grouped: dict[str, dict[str, list[str]]] = {str(t): {} for t in TIER_GBS}
    for model_id, cls in sorted(classifications.items()):
        by_tier = cls.get("by_tier", {})
        for tier in TIER_GBS:
            state = str(by_tier.get(str(tier), "insufficient_evidence"))
            grouped[str(tier)].setdefault(state, []).append(model_id)
    for tier in grouped:
        for state in grouped[tier]:
            grouped[tier][state] = sorted(grouped[tier][state])
    return grouped

"""Metadata-only architecture pipeline: ModelInfo/config dicts to canonical.

Evidence order (Tier A first): structured provider metadata (config at an
immutable revision, GGUF metadata exposed by the API), official docs, model
card (Tier B), derivative declarations (Tier C). Filename hints (Tier D)
never override structured metadata. No weight download, no remote code.
"""

from __future__ import annotations

from atlas.archinfo.canonical import CanonicalArchitectureRecord, FieldEvidence
from atlas.archinfo.capabilities import assess_capabilities
from atlas.archinfo.gguf import normalize_gguf_metadata
from atlas.archinfo.layer_plan import LayerPlan, build_layer_plan
from atlas.archinfo.normalize import (
    classify_attention,
    derive_head_dim,
    detect_custom_code,
    detect_encoder_decoder,
    detect_mla_signals,
    detect_ssm_signals,
    extract_lm_component,
    normalize_config_values,
)

# Tier order for field resolution: first tier holding the field wins.
TIER_ORDER = (
    "tier_a_config",
    "tier_a_gguf",
    "tier_a_docs",
    "tier_b_card",
    "tier_c_derivative",
)

EVIDENCE_CLASS_BY_TIER = {
    "tier_a_config": "calculated_from_source_metadata",
    "tier_a_gguf": "calculated_from_source_metadata",
    "tier_a_docs": "runtime_documented",
    "tier_b_card": "publisher_claim",
    "tier_c_derivative": "quantizer_claim",
}


def _text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, float) and value.is_integer() and value > 0:
        return int(value)
    return None


def config_url_for(repo_id: str, revision: str) -> str:
    """Build the immutable-revision config.json URL for an allowlisted host."""
    cleaned = repo_id.strip().strip("/")
    rev = (revision or "main").strip() or "main"
    return f"https://huggingface.co/{cleaned}/resolve/{rev}/config.json"


def _tier_values(
    tier: str,
    *,
    config: dict | None,
    gguf_metadata: dict | None,
    official_docs: dict | None,
    card: dict | None,
    derivative: dict | None,
    model_type: str | None,
) -> tuple[dict[str, object], str | None, list[str]]:
    """Collect candidate values for one tier with its component note."""
    warnings: list[str] = []
    if tier == "tier_a_config" and isinstance(config, dict):
        values, note, used_generic = normalize_config_values(config, model_type=model_type)
        if used_generic and values:
            warnings.append("generic_key_map_used: family-specific rule absent")
        if note:
            warnings.append(note)
        return values, note, warnings
    if tier == "tier_a_gguf" and isinstance(gguf_metadata, dict):
        values, _origins, gguf_warnings = normalize_gguf_metadata(gguf_metadata)
        warnings.extend(gguf_warnings)
        cleaned = {k: v for k, v in values.items() if k != "architecture_family"}
        return cleaned, None, warnings
    if tier == "tier_a_docs" and isinstance(official_docs, dict):
        out: dict[str, object] = {}
        for key in (
            "hidden_size",
            "intermediate_size",
            "num_hidden_layers",
            "num_attention_heads",
            "num_key_value_heads",
            "vocab_size",
            "max_position_embeddings",
            "sliding_window",
            "head_dim",
            "num_experts",
            "num_experts_per_token",
            "num_shared_experts",
        ):
            parsed = _positive_int(official_docs.get(key))
            if parsed is not None:
                out[key] = parsed
        return out, None, warnings
    if tier in ("tier_b_card", "tier_c_derivative"):
        payload = card if tier == "tier_b_card" else derivative
        if isinstance(payload, dict):
            out = {}
            for key in (
                "hidden_size",
                "intermediate_size",
                "num_hidden_layers",
                "num_attention_heads",
                "num_key_value_heads",
                "vocab_size",
                "max_position_embeddings",
                "sliding_window",
                "head_dim",
            ):
                parsed = _positive_int(payload.get(key))
                if parsed is not None:
                    out[key] = parsed
            return out, None, warnings
    return {}, None, warnings


def resolve_canonical(
    *,
    config: dict | None = None,
    gguf_metadata: dict | None = None,
    official_docs: dict | None = None,
    card: dict | None = None,
    derivative: dict | None = None,
    hub_architecture_name: str | None = None,
    requested_revision: str | None = None,
    resolved_revision: str | None = None,
    retrieved_at: str | None = None,
) -> tuple[CanonicalArchitectureRecord, LayerPlan | None]:
    """Resolve a canonical record from metadata tiers with conflict preservation.

    First tier holding a field wins; disagreements are recorded as conflicts
    and block dependent cache calculations downstream (callers check
    conflict_detected for KV-critical fields).
    """
    tier_payloads = {
        "tier_a_config": config,
        "tier_a_gguf": gguf_metadata,
        "tier_a_docs": official_docs,
        "tier_b_card": card,
        "tier_c_derivative": derivative,
    }
    # model_type / family from strongest source first (config, then hub name).
    model_type: str | None = None
    family: str = "unknown"
    family_tier = "unknown"
    if isinstance(config, dict):
        candidate = _text(config.get("model_type"))
        if candidate:
            model_type = candidate
            family = candidate.lower()
            family_tier = "tier_a_config"
        else:
            lm_view, _ = extract_lm_component(config)
            nested_type = _text(lm_view.get("model_type"))
            if nested_type:
                model_type = nested_type
                family = nested_type.lower()
                family_tier = "tier_a_config"
    if family == "unknown" and isinstance(gguf_metadata, dict):
        for key in ("general.architecture", "general.type", "architecture"):
            candidate = _text(gguf_metadata.get(key))
            if candidate:
                family = candidate.lower()
                family_tier = "tier_a_gguf"
                break
    if family == "unknown":
        candidate = _text(hub_architecture_name)
        if candidate:
            family = candidate.lower()
            family_tier = "tier_b_card"

    merged: dict[str, object] = {}
    origins: dict[str, str] = {}
    conflicts: list[str] = []
    all_warnings: list[str] = []
    for tier in TIER_ORDER:
        payload = tier_payloads[tier]
        if not isinstance(payload, dict) or not payload:
            continue
        values, _note, tier_warnings = _tier_values(
            tier,
            config=config,
            gguf_metadata=gguf_metadata,
            official_docs=official_docs,
            card=card,
            derivative=derivative,
            model_type=model_type,
        )
        all_warnings.extend(tier_warnings)
        for key, value in values.items():
            if key in merged and merged[key] != value:
                conflicts.append(f"{key}: {merged[key]!r}({origins[key]}) vs {value!r}({tier})")
                continue
            if key not in merged:
                merged[key] = value
                origins[key] = tier

    # Architectures list: source-present only, never filename-derived.
    architectures: tuple[str, ...] = ()
    if isinstance(config, dict):
        raw_archs = config.get("architectures")
        if isinstance(raw_archs, (list, tuple)):
            cleaned = [str(a).strip() for a in raw_archs if str(a).strip()]
            architectures = tuple(cleaned[:8])

    custom_code = detect_custom_code(config or {})
    if custom_code:
        all_warnings.append(
            "custom_remote_architecture: auto_map requires remote code (never executed)"
        )
    encoder_decoder = detect_encoder_decoder(config or {}, model_type)

    # MLA/SSM config-key signals override the family name: a model_type that
    # looks standard but carries kv_lora_rank (MLA) or d_state (SSM) keys must
    # never receive the standard KV formula.
    cache_family = family
    if detect_mla_signals(config or {}, model_type):
        cache_family = "mla"
        all_warnings.append("mla_signals: latent-attention keys refuse standard KV")
    elif detect_ssm_signals(config or {}, model_type):
        cache_family = "mamba"
        all_warnings.append("ssm_signals: state-space keys refuse Transformer KV")

    # head_dim: explicit wins; calculated only when exact.
    explicit_head_dim = _positive_int(merged.get("head_dim"))
    hidden = _positive_int(merged.get("hidden_size"))
    q_heads = _positive_int(merged.get("num_attention_heads"))
    head_dim, head_dim_kind = derive_head_dim(hidden, q_heads, explicit_head_dim)
    if head_dim_kind == "calculated":
        all_warnings.append("head_dim_calculated: hidden_size/num_attention_heads exact")

    kv_heads = _positive_int(merged.get("num_key_value_heads"))
    attention_kind = classify_attention(q_heads, kv_heads)

    has_window = _positive_int(merged.get("sliding_window")) is not None
    capabilities = assess_capabilities(
        architecture_family=cache_family,
        is_encoder_decoder=encoder_decoder,
        has_sliding_window=has_window,
        custom_remote_architecture=custom_code,
    )

    # Per-field evidence with revision + tier.
    evidence: dict[str, FieldEvidence] = {}
    for key, value in merged.items():
        tier = origins.get(key, "unknown")
        evidence[key] = FieldEvidence(
            value=value,
            source=tier,
            evidence_class=EVIDENCE_CLASS_BY_TIER.get(tier, "unknown"),
            resolved_revision=resolved_revision,
            retrieved_at=retrieved_at,
            conflict=any(c.startswith(f"{key}:") for c in conflicts),
        )
    if head_dim is not None and head_dim_kind == "calculated":
        evidence["head_dim"] = FieldEvidence(
            value=head_dim,
            source=origins.get("hidden_size", "tier_a_config"),
            evidence_class="calculated",
            resolved_revision=resolved_revision,
            retrieved_at=retrieved_at,
            inference_method="calculated:hidden_size/num_attention_heads exact division",
        )
    elif head_dim is not None:
        evidence["head_dim"] = FieldEvidence(
            value=head_dim,
            source=origins.get("head_dim", "tier_a_config"),
            evidence_class=EVIDENCE_CLASS_BY_TIER.get(
                origins.get("head_dim", ""), "calculated_from_source_metadata"
            ),
            resolved_revision=resolved_revision,
            retrieved_at=retrieved_at,
        )
    evidence["architecture_family"] = FieldEvidence(
        value=family,
        source=family_tier,
        evidence_class=EVIDENCE_CLASS_BY_TIER.get(family_tier, "unknown"),
        resolved_revision=resolved_revision,
        retrieved_at=retrieved_at,
    )

    # Layer plan: per-layer overrides win; absent means global path.
    layer_plan: LayerPlan | None = None
    if isinstance(config, dict):
        layer_plan = build_layer_plan(
            config,
            global_values={
                "num_attention_heads": q_heads,
                "num_key_value_heads": kv_heads,
                "head_dim": head_dim,
                "sliding_window": _positive_int(merged.get("sliding_window")),
                "num_experts": _positive_int(merged.get("num_experts")),
                "num_experts_per_token": _positive_int(merged.get("num_experts_per_token")),
            },
        )
        if layer_plan is not None and layer_plan.warnings:
            all_warnings.extend(layer_plan.warnings)

    # Resolution status from capability + completeness.
    if custom_code or capabilities.standard_kv_model == "unsupported":
        if family in ("unknown",):
            status = "insufficient_evidence"
        elif custom_code:
            status = "partial"
        else:
            status = "unsupported"
    elif not merged or family == "unknown":
        status = "insufficient_evidence"
    elif conflicts:
        status = "partial"
    else:
        status = "resolved"
        if (
            hidden is None
            or _positive_int(merged.get("num_hidden_layers")) is None
            or kv_heads is None
            or head_dim is None
        ):
            status = "partial"

    def _int(name: str) -> int | None:
        return _positive_int(merged.get(name))

    def _number(name: str) -> float | None:
        raw = merged.get(name)
        if isinstance(raw, bool):
            return None
        if isinstance(raw, (int, float)) and raw > 0:
            return float(raw)
        return None

    tie_raw = merged.get("tie_word_embeddings")
    record = CanonicalArchitectureRecord(
        architecture_family=family,
        model_type=model_type,
        architectures=architectures,
        hidden_size=hidden,
        intermediate_size=_int("intermediate_size"),
        num_hidden_layers=_int("num_hidden_layers"),
        num_attention_heads=q_heads,
        num_key_value_heads=kv_heads,
        head_dim=head_dim,
        head_dim_source=head_dim_kind,
        vocab_size=_int("vocab_size"),
        max_position_embeddings=_int("max_position_embeddings"),
        sliding_window=_int("sliding_window"),
        attention_pattern="dense"
        if attention_kind in ("mha", "gqa", "mqa")
        else (attention_kind if attention_kind != "unknown" else None),
        attention_type=attention_kind if attention_kind != "unknown" else None,
        is_encoder_decoder=encoder_decoder,
        tie_word_embeddings=tie_raw if isinstance(tie_raw, bool) else None,
        num_experts=_int("num_experts"),
        num_experts_per_token=_int("num_experts_per_token"),
        num_shared_experts=_int("num_shared_experts"),
        moe_intermediate_size=_int("moe_intermediate_size"),
        state_size=_int("state_size"),
        conv_kernel=_int("conv_kernel"),
        expand_factor=_number("expand_factor"),
        custom_remote_architecture=custom_code,
        requested_revision=requested_revision,
        resolved_revision=resolved_revision,
        retrieved_at=retrieved_at,
        evidence=evidence,
        conflict_detected=bool(conflicts),
        conflict_detail="; ".join(conflicts) if conflicts else None,
        resolution_status=status,
        warnings=tuple(all_warnings + [f"attention:{attention_kind}"]),
    )
    return record, layer_plan


def model_info_to_canonical(
    info: object, *, repo_id: str
) -> tuple[
    CanonicalArchitectureRecord,
    LayerPlan | None,
    dict[str, object],
]:
    """Build a canonical record from an HfApi ModelInfo object (metadata only).

    Reads config/gguf/cardData/sha attributes without downloading anything.
    Returns (record, layer_plan, stats) where stats counts sources used.
    """
    requested = "main"
    retrieved_at = getattr(info, "retrieved_at", None)
    resolved = getattr(info, "sha", None)
    raw_config = getattr(info, "config", None)
    config = dict(raw_config) if isinstance(raw_config, dict) else None
    raw_gguf = getattr(info, "gguf", None)
    gguf_metadata = dict(raw_gguf) if isinstance(raw_gguf, dict) else None
    raw_card = getattr(info, "card_data", None) or getattr(info, "cardData", None)
    card = dict(raw_card) if isinstance(raw_card, dict) else None
    transformers_info = getattr(info, "transformers_info", None)
    hub_arch: str | None = None
    for source in (raw_config, transformers_info):
        if isinstance(source, dict):
            for key in ("model_type", "architecture", "architectures"):
                value = source.get(key)
                if isinstance(value, (list, tuple)) and value and str(value[0]).strip():
                    hub_arch = str(value[0]).strip()
                    break
                if isinstance(value, str) and value.strip():
                    hub_arch = value.strip()
                    break
        else:
            for key in ("model_type", "architecture", "architectures"):
                value = getattr(source, key, None)
                if isinstance(value, (list, tuple)) and value and str(value[0]).strip():
                    hub_arch = str(value[0]).strip()
                    break
                if isinstance(value, str) and value.strip():
                    hub_arch = value.strip()
                    break
        if hub_arch:
            break
    record, plan = resolve_canonical(
        config=config,
        gguf_metadata=gguf_metadata,
        card=card,
        hub_architecture_name=hub_arch,
        requested_revision=requested,
        resolved_revision=str(resolved).strip() if resolved else None,
        retrieved_at=str(retrieved_at) if retrieved_at else None,
    )
    stats: dict[str, object] = {
        "repo_id": repo_id,
        "config_present": config is not None,
        "gguf_present": gguf_metadata is not None,
        "card_present": card is not None,
    }
    return record, plan, stats

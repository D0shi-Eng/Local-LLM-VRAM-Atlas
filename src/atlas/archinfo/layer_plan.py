"""Canonical Layer Plan: per-layer truth wins over global values.

A global config field is safe only when it applies to all relevant layers.
When per-layer overrides exist, the per-layer value is used for that layer
and globals are never silently multiplied across heterogeneous layers.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LayerPlanEntry:
    """One layer's memory-relevant facts; only evidenced fields are set."""

    layer_index: int
    layer_type: str = "unknown"
    attention_present: bool | None = None
    attention_type: str | None = None
    num_attention_heads: int | None = None
    num_key_value_heads: int | None = None
    head_dim: int | None = None
    sliding_window: int | None = None
    mlp_type: str | None = None
    is_moe: bool | None = None
    expert_count: int | None = None
    experts_active: int | None = None
    state_space_component: str | None = None


@dataclass(frozen=True)
class LayerPlan:
    """Ordered per-layer plan with global fallback provenance."""

    entries: tuple[LayerPlanEntry, ...]
    layer_count: int
    heterogeneous: bool
    source: str
    evidence_class: str
    warnings: tuple[str, ...] = ()


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    return None


def _entry_from_dict(index: int, raw: dict, fallback: dict[str, object]) -> LayerPlanEntry:
    """Build one entry: per-layer value wins, global fills the rest."""

    def pick(name: str) -> int | None:
        local = _positive_int(raw.get(name))
        if local is not None:
            return local
        candidate = fallback.get(name)
        return candidate if isinstance(candidate, int) and candidate > 0 else None

    attention_raw = raw.get("attention_present", raw.get("has_attention"))
    attention_present = attention_raw if isinstance(attention_raw, bool) else None
    layer_type = raw.get("layer_type") or raw.get("type") or "unknown"
    attention_type = raw.get("attention_type") or fallback.get("attention_type")
    moe_raw = raw.get("is_moe", raw.get("moe"))
    is_moe = moe_raw if isinstance(moe_raw, bool) else None
    return LayerPlanEntry(
        layer_index=index,
        layer_type=str(layer_type),
        attention_present=attention_present,
        attention_type=str(attention_type) if isinstance(attention_type, str) else None,
        num_attention_heads=pick("num_attention_heads"),
        num_key_value_heads=pick("num_key_value_heads"),
        head_dim=pick("head_dim"),
        sliding_window=_positive_int(raw.get("sliding_window"))
        or (
            fallback.get("sliding_window")
            if isinstance(fallback.get("sliding_window"), int)
            else None
        ),
        mlp_type=str(raw["mlp_type"]) if isinstance(raw.get("mlp_type"), str) else None,
        is_moe=is_moe,
        expert_count=pick("expert_count") or pick("num_experts"),
        experts_active=pick("experts_active") or pick("num_experts_per_token"),
        state_space_component=str(raw["state_space_component"])
        if isinstance(raw.get("state_space_component"), str)
        else None,
    )


def build_layer_plan(
    config: dict,
    *,
    global_values: dict[str, object] | None = None,
    source: str = "config_metadata",
    evidence_class: str = "calculated_from_source_metadata",
) -> LayerPlan | None:
    """Build a Layer Plan from per-layer config when present, else None.

    Recognized per-layer keys: 'layers', 'layer_configs', 'per_layer',
    'block_configs'. A list of per-layer type names in 'layer_types' is also
    recognized: an alternating full/sliding attention pattern is only
    representable per layer, and collapsing it into one global sliding window
    would understate the cache and produce a false fit. Returns None (caller
    keeps the global path) when no per-layer structure exists. Heterogeneity
    is detected by comparing entries rather than assumed.
    """
    if not isinstance(config, dict):
        return None
    fallback = dict(global_values or {})
    layer_types = config.get("layer_types")
    if isinstance(layer_types, (list, tuple)) and layer_types:
        entries: list[LayerPlanEntry] = []
        for index, raw_type in enumerate(layer_types):
            name = str(raw_type).strip() or "unknown"
            lowered = name.lower()
            if lowered in ("full_attention", "attention", "self_attention"):
                attention: bool | None = True
                sliding = None
            elif lowered in ("sliding_attention", "sliding_window_attention"):
                attention = True
                sliding = _positive_int(config.get("sliding_window"))
            elif lowered in ("linear_attention", "ssm", "mamba", "state_space"):
                attention = False
                sliding = None
            else:
                # An unrecognized type refuses rather than defaulting to
                # "has attention", which would fabricate a cache contribution.
                return None
            entries.append(
                LayerPlanEntry(
                    layer_index=index,
                    layer_type=name,
                    attention_present=attention,
                    num_key_value_heads=fallback.get("num_key_value_heads")
                    if isinstance(fallback.get("num_key_value_heads"), int)
                    else None,
                    num_attention_heads=fallback.get("num_attention_heads")
                    if isinstance(fallback.get("num_attention_heads"), int)
                    else None,
                    head_dim=fallback.get("head_dim")
                    if isinstance(fallback.get("head_dim"), int)
                    else None,
                    sliding_window=sliding,
                )
            )
        return _finalize_plan(entries, source=source, evidence_class=evidence_class)
    raw_layers: object = None
    for key in ("layers", "layer_configs", "per_layer", "block_configs"):
        candidate = config.get(key)
        if isinstance(candidate, (list, tuple)) and candidate:
            raw_layers = candidate
            break
    if raw_layers is None:
        return None
    entries = []
    for index, raw in enumerate(raw_layers):
        if not isinstance(raw, dict):
            return None
        entries.append(_entry_from_dict(index, raw, fallback))
    if not entries:
        return None
    return _finalize_plan(entries, source=source, evidence_class=evidence_class)


def _finalize_plan(
    entries: list[LayerPlanEntry],
    *,
    source: str,
    evidence_class: str,
) -> LayerPlan:
    """Assemble a LayerPlan and detect heterogeneity from the entries."""
    signatures = {
        (
            e.layer_type,
            e.attention_present,
            e.attention_type,
            e.num_attention_heads,
            e.num_key_value_heads,
            e.head_dim,
            e.sliding_window,
            e.mlp_type,
            e.is_moe,
            e.expert_count,
            e.experts_active,
            e.state_space_component,
        )
        for e in entries
    }
    heterogeneous = len(signatures) > 1
    warnings: tuple[str, ...] = ()
    if heterogeneous:
        warnings = ("heterogeneous_layers: per-layer values used; globals not multiplied",)
    return LayerPlan(
        entries=tuple(entries),
        layer_count=len(entries),
        heterogeneous=heterogeneous,
        source=source,
        evidence_class=evidence_class,
        warnings=warnings,
    )


def attention_layer_count(plan: LayerPlan) -> int:
    """Count layers with attention present (None counts as unknown, excluded)."""
    return sum(1 for entry in plan.entries if entry.attention_present is True)

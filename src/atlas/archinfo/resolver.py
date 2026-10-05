"""محلل بيانات البنية: جمع الأدلة بترتيب موثق مع حفظ التعارض."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ArchitectureInfo:
    """بيانات بنية محلولة مع مصدر كل حقل."""

    architecture_family: str
    architecture_type: str
    num_layers: int | None = None
    num_attention_heads: int | None = None
    num_key_value_heads: int | None = None
    head_dim: int | None = None
    hidden_size: int | None = None
    sliding_window: int | None = None
    is_moe: bool = False
    total_params: int | None = None
    evidence_order: tuple[str, ...] = ()
    conflict_detected: bool = False
    conflict_detail: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)


def hub_fields_from_model_info(info: object) -> dict[str, dict]:
    """استخراج حقول البنية من كائن model_info دون شبكة أو تنفيذ شيفرة.

    يعيد config/gguf/card/transformers كقواميس JSON فقط؛ الغائب يبقى {}.
    """

    def _as_dict(value: object) -> dict:
        if isinstance(value, dict):
            return {k: v for k, v in value.items() if isinstance(k, str)}
        if value is None:
            return {}
        result: dict = {}
        for key in (
            "architectures",
            "model_type",
            "hidden_size",
            "intermediate_size",
            "num_hidden_layers",
            "num_attention_heads",
            "num_key_value_heads",
            "head_dim",
            "vocab_size",
            "max_position_embeddings",
            "sliding_window",
            "tie_word_embeddings",
            "is_encoder_decoder",
            "layer_types",
            "num_experts",
            "num_local_experts",
            "num_experts_per_tok",
            "num_experts_per_token",
            "router_topk",
            "num_shared_experts",
            "auto_map",
            "max_sequence_length",
            "context_length",
        ):
            candidate = getattr(value, key, None)
            if candidate is not None:
                result[key] = candidate
        return result

    config = _as_dict(getattr(info, "config", None))
    gguf = _as_dict(getattr(info, "gguf", None))
    card = _as_dict(getattr(info, "card_data", None))
    transformers_info = _as_dict(getattr(info, "transformers_info", None))
    hub_structured: dict = {}
    for key in ("architectures", "model_type", "architecture", "base_models"):
        candidate = getattr(info, key, None)
        if candidate is not None:
            hub_structured[key] = candidate
    return {
        "hub_metadata": hub_structured,
        "config_metadata": config,
        "gguf_metadata": gguf,
        "publisher_card": card,
        "transformers_info": transformers_info,
    }


def _positive_int(value: object) -> int | None:
    """قبول الأعداد الصحيحة الموجبة فقط دون تخمين."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, float) and value.is_integer() and value > 0:
        return int(value)
    return None


def _text(value: object) -> str | None:
    """توحيد النصوص المعلنة دون استنتاج."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def resolve_architecture(
    *,
    hub_metadata: dict | None = None,
    config_metadata: dict | None = None,
    official_docs: dict | None = None,
    gguf_metadata: dict | None = None,
    publisher_card: dict | None = None,
) -> ArchitectureInfo:
    """جمع بيانات البنية بترتيب الأدلة وحفظ التعارض.

    الترتيب: Hub المنظم ثم config ثم التوثيق الرسمي ثم GGUF metadata ثم بطاقة
    الناشر. اسم المستودع ليس مصدرًا أبدًا.
    """
    sources = [
        ("hub_metadata", hub_metadata or {}),
        ("config_metadata", config_metadata or {}),
        ("official_docs", official_docs or {}),
        ("gguf_metadata", gguf_metadata or {}),
        ("publisher_card", publisher_card or {}),
    ]
    merged: dict[str, object] = {}
    origins: dict[str, str] = {}
    conflicts: list[str] = []
    for origin, payload in sources:
        if not isinstance(payload, dict):
            continue
        for key in (
            "architecture_family",
            "architecture",
            "architecture_type",
            "num_layers",
            "num_hidden_layers",
            "num_attention_heads",
            "num_key_value_heads",
            "head_dim",
            "hidden_size",
            "sliding_window",
            "is_moe",
            "total_params",
            "total_parameters",
        ):
            if key not in payload or payload[key] is None:
                continue
            if key in merged and merged[key] != payload[key]:
                conflicts.append(
                    f"{key}: {merged[key]!r}({origins[key]}) vs {payload[key]!r}({origin})"
                )
                continue
            if key not in merged:
                merged[key] = payload[key]
                origins[key] = origin
    family = _text(merged.get("architecture_family")) or _text(merged.get("architecture"))
    family = family or "unknown"
    raw_type = (_text(merged.get("architecture_type")) or "unknown").lower()
    arch_type = raw_type if raw_type in ("dense", "moe", "hybrid", "unknown") else "unknown"
    layers_raw = merged.get("num_layers")
    if layers_raw is None:
        layers_raw = merged.get("num_hidden_layers")
    layers = _positive_int(layers_raw)
    total_raw = merged.get("total_params")
    if total_raw is None:
        total_raw = merged.get("total_parameters")
    used = tuple(
        origins.get(key, "?") for key in ("architecture_family", "num_layers") if key in origins
    ) or ("none",)
    warnings: list[str] = []
    if family == "unknown":
        warnings.append("architecture_unknown: estimation must refuse, not guess")
    if conflicts:
        warnings.append("conflict_detected: architecture sources disagree; first evidence kept")
    return ArchitectureInfo(
        architecture_family=family,
        architecture_type=arch_type,
        num_layers=layers,
        num_attention_heads=_positive_int(merged.get("num_attention_heads")),
        num_key_value_heads=_positive_int(merged.get("num_key_value_heads")),
        head_dim=_positive_int(merged.get("head_dim")),
        hidden_size=_positive_int(merged.get("hidden_size")),
        sliding_window=_positive_int(merged.get("sliding_window")),
        is_moe=merged.get("is_moe") is True or arch_type == "moe",
        total_params=_positive_int(total_raw),
        evidence_order=used,
        conflict_detected=bool(conflicts),
        conflict_detail="; ".join(conflicts) if conflicts else None,
        warnings=tuple(warnings),
    )

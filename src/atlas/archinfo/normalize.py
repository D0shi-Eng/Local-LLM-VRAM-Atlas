"""Config normalization: component boundaries and per-architecture key rules.

Every mapping below is documented with the architecture it applies to; no
universal alias dictionary is assumed to share semantics across families.
Framework class defaults are never treated as source facts: only values
present in the source metadata become evidence.
"""

from __future__ import annotations

# Nested configs holding the language-model component of composite models.
TEXT_COMPONENT_KEYS = ("text_config", "language_config", "decoder_config")

# Nested configs that must never leak into language-model calculations.
NON_LM_COMPONENT_KEYS = ("vision_config", "audio_config", "encoder_config")

# Explicit custom-code signal inside a config.json: executing it would require
# remote code loading, which Atlas never performs.
CUSTOM_CODE_KEYS = ("auto_map",)

# Architectures documented as encoder-decoder (decoder-only KV formulas refuse).
ENCODER_DECODER_TYPES = frozenset(
    {"bart", "t5", "pegasus", "mbart", "marian", "whisper", "encoder_decoder"}
)

# Config-key indicators of Multi-head Latent Attention, valid even when the
# family name differs (ported from the reconciled GGUF/config-key survey).
MLA_CONFIG_KEYS = frozenset({"kv_lora_rank", "qk_rope_head_dim", "qk_nope_head_dim", "v_head_dim"})

# Config-key indicators of state-space layers (ported likewise).
SSM_CONFIG_KEYS = frozenset(
    {
        "mamba_d_state",
        "state_size",
        "conv_kernel",
        "conv_kernel_size",
        "expand",
        "expand_factor",
    }
)

# Architecture-specific config-key maps. Each entry lists, per canonical
# field, the config keys carrying that meaning FOR THAT FAMILY ONLY.
# Semantics were checked against the official Transformers configuration
# documentation at implementation time (see runtime-knowledge report).
ARCH_KEY_MAPS: dict[str, dict[str, tuple[str, ...]]] = {
    "llama": {
        "hidden_size": ("hidden_size",),
        "intermediate_size": ("intermediate_size",),
        "num_hidden_layers": ("num_hidden_layers",),
        "num_attention_heads": ("num_attention_heads",),
        "num_key_value_heads": ("num_key_value_heads",),
        "vocab_size": ("vocab_size",),
        "max_position_embeddings": ("max_position_embeddings",),
        "sliding_window": ("sliding_window",),
        "tie_word_embeddings": ("tie_word_embeddings",),
    },
    "mistral": {
        "hidden_size": ("hidden_size",),
        "intermediate_size": ("intermediate_size",),
        "num_hidden_layers": ("num_hidden_layers",),
        "num_attention_heads": ("num_attention_heads",),
        "num_key_value_heads": ("num_key_value_heads",),
        "vocab_size": ("vocab_size",),
        "max_position_embeddings": ("max_position_embeddings",),
        "sliding_window": ("sliding_window",),
        "tie_word_embeddings": ("tie_word_embeddings",),
    },
    "mixtral": {
        "hidden_size": ("hidden_size",),
        "intermediate_size": ("intermediate_size",),
        "num_hidden_layers": ("num_hidden_layers",),
        "num_attention_heads": ("num_attention_heads",),
        "num_key_value_heads": ("num_key_value_heads",),
        "vocab_size": ("vocab_size",),
        "max_position_embeddings": ("max_position_embeddings",),
        "sliding_window": ("sliding_window",),
        "num_experts": ("num_local_experts",),
        "num_experts_per_token": ("num_experts_per_tok",),
        "tie_word_embeddings": ("tie_word_embeddings",),
    },
    "qwen2": {
        "hidden_size": ("hidden_size",),
        "intermediate_size": ("intermediate_size",),
        "num_hidden_layers": ("num_hidden_layers",),
        "num_attention_heads": ("num_attention_heads",),
        "num_key_value_heads": ("num_key_value_heads",),
        "vocab_size": ("vocab_size",),
        "max_position_embeddings": ("max_position_embeddings",),
        "sliding_window": ("sliding_window",),
        "tie_word_embeddings": ("tie_word_embeddings",),
    },
    "qwen3": {
        "hidden_size": ("hidden_size",),
        "intermediate_size": ("intermediate_size",),
        "num_hidden_layers": ("num_hidden_layers",),
        "num_attention_heads": ("num_attention_heads",),
        "num_key_value_heads": ("num_key_value_heads",),
        "vocab_size": ("vocab_size",),
        "max_position_embeddings": ("max_position_embeddings",),
        "sliding_window": ("sliding_window",),
        "tie_word_embeddings": ("tie_word_embeddings",),
        "head_dim": ("head_dim",),
    },
    "qwen3_moe": {
        "hidden_size": ("hidden_size",),
        "intermediate_size": ("moe_intermediate_size", "intermediate_size"),
        "num_hidden_layers": ("num_hidden_layers",),
        "num_attention_heads": ("num_attention_heads",),
        "num_key_value_heads": ("num_key_value_heads",),
        "vocab_size": ("vocab_size",),
        "max_position_embeddings": ("max_position_embeddings",),
        "num_experts": ("num_experts", "num_local_experts"),
        "num_experts_per_token": (
            "num_experts_per_tok",
            "num_experts_per_token",
            "router_topk",
        ),
        "num_shared_experts": ("num_shared_experts", "n_shared_experts"),
        "moe_intermediate_size": ("moe_intermediate_size",),
        "tie_word_embeddings": ("tie_word_embeddings",),
        "head_dim": ("head_dim",),
    },
    "gemma": {
        "hidden_size": ("hidden_size",),
        "intermediate_size": ("intermediate_size",),
        "num_hidden_layers": ("num_hidden_layers",),
        "num_attention_heads": ("num_attention_heads",),
        "num_key_value_heads": ("num_key_value_heads",),
        "vocab_size": ("vocab_size",),
        "max_position_embeddings": ("max_position_embeddings",),
        "sliding_window": ("sliding_window",),
        "tie_word_embeddings": ("tie_word_embeddings",),
        "head_dim": ("head_dim",),
    },
    "gemma2": {
        "hidden_size": ("hidden_size",),
        "intermediate_size": ("intermediate_size",),
        "num_hidden_layers": ("num_hidden_layers",),
        "num_attention_heads": ("num_attention_heads",),
        "num_key_value_heads": ("num_key_value_heads",),
        "vocab_size": ("vocab_size",),
        "max_position_embeddings": ("max_position_embeddings",),
        "sliding_window": ("sliding_window",),
        "tie_word_embeddings": ("tie_word_embeddings",),
        "head_dim": ("head_dim",),
        "attention_type": ("attention_type",),
    },
    "gpt_oss": {
        "hidden_size": ("hidden_size",),
        "intermediate_size": ("intermediate_size",),
        "num_hidden_layers": ("num_hidden_layers",),
        "num_attention_heads": ("num_attention_heads",),
        "num_key_value_heads": ("num_key_value_heads",),
        "vocab_size": ("vocab_size",),
        "max_position_embeddings": ("max_position_embeddings",),
        "sliding_window": ("sliding_window",),
        "num_experts": ("num_experts", "num_local_experts"),
        "num_experts_per_token": ("experts_per_token", "num_experts_per_token"),
        "tie_word_embeddings": ("tie_word_embeddings",),
        "head_dim": ("head_dim",),
    },
    "gemma3": {
        # Multimodal composite: language facts live under text_config.
        # Dotted aliases are resolved against the root config.
        "hidden_size": ("hidden_size", "text_config.hidden_size"),
        "intermediate_size": ("intermediate_size", "text_config.intermediate_size"),
        "num_hidden_layers": ("num_hidden_layers", "text_config.num_hidden_layers"),
        "num_attention_heads": ("num_attention_heads", "text_config.num_attention_heads"),
        "num_key_value_heads": (
            "num_key_value_heads",
            "text_config.num_key_value_heads",
        ),
        "vocab_size": ("vocab_size", "text_config.vocab_size"),
        "max_position_embeddings": (
            "max_position_embeddings",
            "text_config.max_position_embeddings",
        ),
        "sliding_window": ("sliding_window", "text_config.sliding_window"),
        "tie_word_embeddings": ("tie_word_embeddings",),
        "head_dim": ("head_dim", "text_config.head_dim"),
    },
    "minicpm": {
        "hidden_size": ("hidden_size",),
        "intermediate_size": ("intermediate_size",),
        "num_hidden_layers": ("num_hidden_layers",),
        "num_attention_heads": ("num_attention_heads",),
        "num_key_value_heads": ("num_key_value_heads",),
        "vocab_size": ("vocab_size",),
        "max_position_embeddings": ("max_position_embeddings",),
        "sliding_window": ("sliding_window",),
        "tie_word_embeddings": ("tie_word_embeddings",),
    },
    # Observed live 2026-10-05 with standard decoder key names; rules added
    # from that evidence so these families are not generic-map guesses.
    "gemma4_unified": {
        "hidden_size": ("hidden_size",),
        "intermediate_size": ("intermediate_size",),
        "num_hidden_layers": ("num_hidden_layers",),
        "num_attention_heads": ("num_attention_heads",),
        "num_key_value_heads": ("num_key_value_heads",),
        "vocab_size": ("vocab_size",),
        "max_position_embeddings": ("max_position_embeddings",),
        "sliding_window": ("sliding_window",),
        "tie_word_embeddings": ("tie_word_embeddings",),
        "head_dim": ("head_dim",),
    },
    "mistral3": {
        "hidden_size": ("hidden_size",),
        "intermediate_size": ("intermediate_size",),
        "num_hidden_layers": ("num_hidden_layers",),
        "num_attention_heads": ("num_attention_heads",),
        "num_key_value_heads": ("num_key_value_heads",),
        "vocab_size": ("vocab_size",),
        "max_position_embeddings": ("max_position_embeddings",),
        "sliding_window": ("sliding_window",),
        "tie_word_embeddings": ("tie_word_embeddings",),
        "head_dim": ("head_dim",),
    },
    "qwen3_5": {
        "hidden_size": ("hidden_size",),
        "intermediate_size": ("intermediate_size",),
        "num_hidden_layers": ("num_hidden_layers",),
        "num_attention_heads": ("num_attention_heads",),
        "num_key_value_heads": ("num_key_value_heads",),
        "vocab_size": ("vocab_size",),
        "max_position_embeddings": ("max_position_embeddings",),
        "sliding_window": ("sliding_window",),
        "tie_word_embeddings": ("tie_word_embeddings",),
        "head_dim": ("head_dim",),
    },
    "mamba": {
        "hidden_size": ("d_model",),
        "intermediate_size": ("intermediate_size",),
        "num_hidden_layers": ("n_layer", "num_hidden_layers"),
        "vocab_size": ("vocab_size",),
        "state_size": ("state_size", "d_state"),
        "conv_kernel": ("conv_kernel", "d_conv"),
        "expand_factor": ("expand",),
    },
    "deepseek_v3": {
        "hidden_size": ("hidden_size",),
        "intermediate_size": ("intermediate_size",),
        "num_hidden_layers": ("num_hidden_layers",),
        "num_attention_heads": ("num_attention_heads",),
        "num_key_value_heads": ("num_key_value_heads",),
        "vocab_size": ("vocab_size",),
        "max_position_embeddings": ("max_position_embeddings",),
        "num_experts": ("n_routed_experts",),
        "num_experts_per_token": ("num_experts_per_tok",),
        "num_shared_experts": ("n_shared_experts",),
        "moe_intermediate_size": ("moe_intermediate_size",),
    },
}

# Generic fallback for families without a dedicated rule: only keys whose
# meaning is stable across standard decoder-only Transformers configs.
# Legacy spellings (n_layer/n_head/...) are accepted but always flagged via
# the generic-map warning so they never gain family-specific authority.
GENERIC_KEY_MAP: dict[str, tuple[str, ...]] = {
    "hidden_size": ("hidden_size",),
    "intermediate_size": ("intermediate_size",),
    "num_hidden_layers": ("num_hidden_layers", "num_layers", "n_layer"),
    "num_attention_heads": ("num_attention_heads", "n_head"),
    "num_key_value_heads": ("num_key_value_heads", "n_head_kv"),
    "vocab_size": ("vocab_size",),
    "max_position_embeddings": ("max_position_embeddings", "max_seq_len", "n_positions"),
    "num_experts": ("num_experts", "num_local_experts"),
    "num_experts_per_token": (
        "num_experts_per_tok",
        "num_experts_per_token",
        "router_topk",
    ),
}


def _positive_int(value: object) -> int | None:
    """Accept positive integers only; booleans and floats-that-are-int excluded."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    return None


def _positive_number(value: object) -> float | None:
    """Accept positive numbers (expand factors may be fractional)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    return None


def extract_lm_component(config: dict) -> tuple[dict, str | None]:
    """Resolve the language-model component boundary of a possibly nested config.

    Returns the mapping holding LM fields and a note when a nested component
    (text_config/language_config/decoder_config) was used. Vision/audio/
    encoder components are never merged into LM values.
    """
    if not isinstance(config, dict):
        return {}, None
    top_hits = sum(1 for key in ("hidden_size", "num_hidden_layers", "d_model") if key in config)
    for comp_key in TEXT_COMPONENT_KEYS:
        nested = config.get(comp_key)
        if isinstance(nested, dict) and nested:
            nested_hits = sum(
                1 for key in ("hidden_size", "num_hidden_layers", "d_model") if key in nested
            )
            if nested_hits and not top_hits:
                return nested, f"nested_component_used:{comp_key}"
    return config, None


def key_map_for(model_type: str | None) -> tuple[dict[str, tuple[str, ...]], bool]:
    """Return the key map for a model type and whether it is family-specific."""
    normalized = (model_type or "").strip().lower()
    if normalized in ARCH_KEY_MAPS:
        return ARCH_KEY_MAPS[normalized], True
    return GENERIC_KEY_MAP, False


def _lookup_dotted(payload: dict, dotted: str) -> object:
    """Read a dotted path (e.g. text_config.hidden_size) without code execution."""
    if not isinstance(payload, dict) or not dotted:
        return None
    if "." not in dotted:
        return payload.get(dotted)
    current: object = payload
    for part in dotted.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def normalize_config_values(
    config: dict, *, model_type: str | None = None
) -> tuple[dict[str, object], str | None, bool]:
    """Normalize one config mapping with the family-specific key map.

    Returns (values, component_note, used_generic_map). Only source-present
    keys are read; absent keys stay absent (never framework defaults).
    Dotted aliases (e.g. text_config.hidden_size) resolve against the root.
    """
    lm_config, note = extract_lm_component(config)
    key_map, specific = key_map_for(model_type or lm_config.get("model_type"))
    values: dict[str, object] = {}
    for canonical, keys in key_map.items():
        for key in keys:
            raw = lm_config.get(key) if "." not in key else _lookup_dotted(config, key)
            if raw is not None:
                if canonical == "expand_factor":
                    parsed = _positive_number(raw)
                elif canonical in ("tie_word_embeddings",):
                    parsed = raw if isinstance(raw, bool) else None
                elif canonical == "attention_type":
                    parsed = raw.strip() if isinstance(raw, str) and raw.strip() else None
                else:
                    parsed = _positive_int(raw)
                if parsed is not None:
                    values[canonical] = parsed
                    break
    # head_dim is family-specific where documented; otherwise explicit key only.
    if "head_dim" not in values:
        explicit = _positive_int(lm_config.get("head_dim"))
        if explicit is not None:
            values["head_dim"] = explicit
    # Sliding-window spellings that differ by family (documented variants).
    if "sliding_window" not in values:
        for variant in ("sliding_window_size",):
            parsed = _positive_int(lm_config.get(variant))
            if parsed is not None:
                values["sliding_window"] = parsed
                break
    return values, note, not specific


def classify_attention(num_attention_heads: int | None, num_key_value_heads: int | None) -> str:
    """Classify MHA/GQA/MQA from head counts only when semantics are known."""
    if not isinstance(num_attention_heads, int) or not isinstance(num_key_value_heads, int):
        return "unknown"
    if num_attention_heads <= 0 or num_key_value_heads <= 0:
        return "unknown"
    if num_key_value_heads == num_attention_heads:
        return "mha"
    if num_key_value_heads == 1:
        return "mqa"
    if 1 < num_key_value_heads < num_attention_heads:
        return "gqa"
    return "unknown"


def derive_head_dim(
    hidden_size: int | None,
    num_attention_heads: int | None,
    explicit_head_dim: int | None,
) -> tuple[int | None, str | None]:
    """Prefer explicit head_dim; calculate only when exact and unambiguous."""
    if isinstance(explicit_head_dim, int) and explicit_head_dim > 0:
        return explicit_head_dim, "explicit"
    if (
        isinstance(hidden_size, int)
        and isinstance(num_attention_heads, int)
        and hidden_size > 0
        and num_attention_heads > 0
        and hidden_size % num_attention_heads == 0
    ):
        return hidden_size // num_attention_heads, "calculated"
    return None, None


def detect_custom_code(config: dict) -> bool:
    """Detect configs requiring remote code loading (auto_map) without executing."""
    if not isinstance(config, dict):
        return False
    return any(key in config and config[key] for key in CUSTOM_CODE_KEYS)


def detect_mla_signals(config: dict, model_type: str | None = None) -> bool:
    """Detect Multi-head Latent Attention from family or config key indicators."""
    from atlas.archinfo.capabilities import MLA_FAMILIES

    if isinstance(model_type, str) and model_type.strip().lower() in MLA_FAMILIES:
        return True
    if not isinstance(config, dict):
        return False
    return any(key in config and config[key] is not None for key in MLA_CONFIG_KEYS)


def detect_ssm_signals(config: dict, model_type: str | None = None) -> bool:
    """Detect state-space layers from family or config key indicators."""
    from atlas.archinfo.capabilities import SSM_FAMILIES

    if isinstance(model_type, str) and model_type.strip().lower() in SSM_FAMILIES:
        return True
    if not isinstance(config, dict):
        return False
    return any(key in config and config[key] is not None for key in SSM_CONFIG_KEYS)


def detect_encoder_decoder(config: dict, model_type: str | None) -> bool | None:
    """Detect encoder-decoder architectures; None when evidence is absent."""
    normalized = (model_type or "").strip().lower()
    if normalized in ENCODER_DECODER_TYPES:
        return True
    if isinstance(config, dict):
        flag = config.get("is_encoder_decoder")
        if isinstance(flag, bool):
            return flag
        archs = config.get("architectures")
        if isinstance(archs, (list, tuple)):
            joined = " ".join(str(item) for item in archs).lower()
            if "encoderdecoder" in joined or "encoder_decoder" in joined:
                return True
    return None

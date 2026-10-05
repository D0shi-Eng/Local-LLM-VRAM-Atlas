"""GGUF metadata mapping: Hub-exposed tensor facts only, never file bytes.

Uses the official GGUF specification key meanings. Key spellings differ per
architecture ({arch} prefix); this module matches documented suffixes and
records which architecture prefix supplied each value. No GGUF file is ever
downloaded; only metadata already exposed by the trusted provider API.
"""

from __future__ import annotations

# Documented GGUF metadata suffixes and their canonical meaning.
# Source: official GGUF specification (see runtime-knowledge report).
# Suffixes strip the <arch> prefix (llama.attention.head_count -> suffix).
GGUF_SUFFIX_MAP: dict[str, str] = {
    "embedding_length": "hidden_size",
    "feed_forward_length": "intermediate_size",
    "block_count": "num_hidden_layers",
    "attention.head_count": "num_attention_heads",
    "attention.head_count_kv": "num_key_value_heads",
    "attention.key_length": "head_dim",
    "attention.value_length": "head_dim",
    "attention.sliding_window": "sliding_window",
    "context_length": "max_position_embeddings",
    "vocab_size": "vocab_size",
    "expert_count": "num_experts",
    "expert_used_count": "num_experts_per_token",
    "expert_shared_count": "num_shared_experts",
    "ssm.state_size": "state_size",
    "ssm.conv_kernel": "conv_kernel",
    "ssm.expansion_factor": "expand_factor",
}

# GGUF general keys.
GGUF_GENERAL_ARCHITECTURE_KEYS = ("general.architecture", "general.type")

# Bare keys of the Hub GGUF summary object (model_info.gguf), observed live
# 2026-10-05: {"total", "architecture", "context_length", ...}. "total" is a
# parameter count handled by the intake extractor, never architecture here.
GGUF_HUB_SUMMARY_ARCHITECTURE_KEYS = ("architecture",)


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, float) and value.is_integer() and value > 0:
        return int(value)
    return None


def normalize_gguf_metadata(
    gguf_metadata: dict,
) -> tuple[dict[str, object], dict[str, str], list[str]]:
    """Map Hub-exposed GGUF metadata to canonical fields.

    Returns (values, key_origins, warnings). The architecture prefix (e.g.
    'llama.embedding_length') is preserved in key_origins for audit.
    Unknown keys are ignored, never guessed.
    """
    values: dict[str, object] = {}
    origins: dict[str, str] = {}
    warnings: list[str] = []
    if not isinstance(gguf_metadata, dict):
        return values, origins, warnings
    for raw_key, raw_value in gguf_metadata.items():
        if not isinstance(raw_key, str):
            continue
        lowered = raw_key.strip().lower()
        for general_key in GGUF_GENERAL_ARCHITECTURE_KEYS:
            if lowered == general_key and isinstance(raw_value, str) and raw_value.strip():
                if "architecture_family" not in values:
                    values["architecture_family"] = raw_value.strip()
                    origins["architecture_family"] = raw_key
                break
        if lowered in GGUF_HUB_SUMMARY_ARCHITECTURE_KEYS and isinstance(raw_value, str):
            if raw_value.strip() and "architecture_family" not in values:
                values["architecture_family"] = raw_value.strip()
                origins["architecture_family"] = raw_key + " (hub summary)"
            continue
        for suffix, canonical in GGUF_SUFFIX_MAP.items():
            if lowered.endswith(suffix) and (lowered == suffix or lowered.endswith("." + suffix)):
                parsed = _positive_int(raw_value)
                if parsed is not None and canonical not in values:
                    values[canonical] = parsed
                    origins[canonical] = raw_key
                break
    if values and "architecture_family" not in values:
        warnings.append("gguf_prefix_without_general_architecture: family stays unknown")
    return values, origins, warnings

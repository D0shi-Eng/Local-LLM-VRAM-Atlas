"""Capability assessment: what can be modeled, what must be refused.

No fake percentage is produced; each axis reports one of supported,
partially_supported, experimental, unsupported, unknown.
"""

from __future__ import annotations

from dataclasses import dataclass

SUPPORT_STATES = (
    "supported",
    "partially_supported",
    "experimental",
    "unsupported",
    "unknown",
)

# Families whose KV cache follows the standard Transformer equation.
STANDARD_KV_FAMILIES = frozenset(
    {
        "llama",
        "mistral",
        "qwen2",
        "qwen3",
        "gemma",
        "gemma2",
        "phi",
        "falcon",
        "gpt_neox",
        "opt",
        "standard_transformer",
        "transformer_gqa",
        "transformer_mqa",
        "moe",
        "mixtral",
        "qwen3_moe",
        "gpt_oss",
        "minicpm",
        "gemma3",
        # Observed live 2026-10-05 with standard GQA decoder configs.
        "gemma4_unified",
        "mistral3",
        "qwen3_5",
    }
)

# Sliding-window families: cache is partial until layer pattern + runtime known.
SLIDING_WINDOW_FAMILIES = frozenset(
    {
        "mistral",
        "mixtral",
        "gemma2",
        "gemma3",
        "minicpm",
        "sliding_window_transformer",
    }
)

# Multi-head Latent Attention: never the standard KV equation.
# DeepSeek-V2/V3 and Kimi K2 use MLA per their official architecture specs,
# so they refuse the standard KV formula even though MoE keys may be present.
MLA_FAMILIES = frozenset(
    {"deepseek_mla", "mla", "kimi_k2_mla", "deepseek_v2", "deepseek_v3", "kimi_k2"}
)

# State-space families: never Transformer KV formulas.
SSM_FAMILIES = frozenset({"mamba", "mamba_ssm", "mamba2", "rwkv", "falcon_mamba", "jamba_ssm"})

# Hybrid families: component-wise accounting or refusal.
HYBRID_FAMILIES = frozenset({"jamba", "hybrid", "gemma_hybrid"})


@dataclass(frozen=True)
class ArchitectureCapabilities:
    """Per-axis capability states for one resolved architecture."""

    weight_static_model: str = "unknown"
    standard_kv_model: str = "unknown"
    sliding_window_model: str = "unknown"
    mla_cache_model: str = "unknown"
    state_cache_model: str = "unknown"
    notes: tuple[str, ...] = ()


def assess_capabilities(
    *,
    architecture_family: str | None,
    is_encoder_decoder: bool | None = None,
    has_sliding_window: bool = False,
    custom_remote_architecture: bool = False,
) -> ArchitectureCapabilities:
    """Assess modeling capability without inventing confidence numbers."""
    family = (architecture_family or "unknown").strip().lower()
    if custom_remote_architecture:
        return ArchitectureCapabilities(
            weight_static_model="partially_supported",
            standard_kv_model="unsupported",
            sliding_window_model="unknown",
            mla_cache_model="unsupported",
            state_cache_model="unsupported",
            notes=("custom_remote_architecture: untrusted code never executed",),
        )
    if is_encoder_decoder is True:
        return ArchitectureCapabilities(
            weight_static_model="supported",
            standard_kv_model="unsupported",
            sliding_window_model="unsupported",
            mla_cache_model="unsupported",
            state_cache_model="unsupported",
            notes=("encoder_decoder: decoder-only KV formulas do not apply",),
        )
    if family in MLA_FAMILIES:
        return ArchitectureCapabilities(
            weight_static_model="supported",
            standard_kv_model="unsupported",
            sliding_window_model="unsupported",
            mla_cache_model="unsupported",
            state_cache_model="unsupported",
            notes=("mla: needs an architecture-specific cache model",),
        )
    if family in SSM_FAMILIES:
        return ArchitectureCapabilities(
            weight_static_model="supported",
            standard_kv_model="unsupported",
            sliding_window_model="unsupported",
            mla_cache_model="unsupported",
            state_cache_model="unsupported",
            notes=("ssm: recurrent/state cache needs state dimensions, not KV",),
        )
    if family in HYBRID_FAMILIES:
        sliding: str = "unknown"
        if has_sliding_window:
            sliding = "partially_supported"
        return ArchitectureCapabilities(
            weight_static_model="supported",
            standard_kv_model="unsupported",
            sliding_window_model=sliding,
            mla_cache_model="unsupported",
            state_cache_model="unsupported",
            notes=("hybrid: component-specific models required; never reduced",),
        )
    if family in STANDARD_KV_FAMILIES:
        sliding_state = "partially_supported" if has_sliding_window else "unknown"
        if family in SLIDING_WINDOW_FAMILIES:
            sliding_state = "partially_supported"
        return ArchitectureCapabilities(
            weight_static_model="supported",
            standard_kv_model="supported",
            sliding_window_model=sliding_state,
            mla_cache_model="unsupported",
            state_cache_model="unsupported",
            notes=("standard attention path with mandatory KV-head evidence",),
        )
    if not family or family == "unknown":
        return ArchitectureCapabilities(
            notes=("unknown family: calculation refused, not guessed",),
        )
    return ArchitectureCapabilities(
        weight_static_model="supported",
        standard_kv_model="unknown",
        sliding_window_model="unknown",
        mla_cache_model="unknown",
        state_cache_model="unknown",
        notes=(f"unlisted family {family!r}: standard KV not assumed",),
    )

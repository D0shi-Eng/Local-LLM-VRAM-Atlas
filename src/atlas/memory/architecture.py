"""مصفوفة دعم المعماريات: ما يحسب وما يرفض بصراحة موثقة."""

from __future__ import annotations

# الحالات المسموحة لكل محور تقدير.
_SUPPORT_STATES = ("supported", "partially_supported", "experimental", "unsupported", "unknown")

ARCHITECTURE_SUPPORT: dict[str, dict] = {
    "standard_transformer": {
        "architecture_family": "standard_transformer",
        "weight_estimation": "supported",
        "cache_estimation": "supported",
        "runtime_overhead_estimation": "unknown",
        "classification_support": "partially_supported",
        "status": "supported",
        "limitations": "runtime overhead stays unknown without a measured profile",
    },
    "transformer_gqa": {
        "architecture_family": "transformer_gqa",
        "weight_estimation": "supported",
        "cache_estimation": "supported",
        "runtime_overhead_estimation": "unknown",
        "classification_support": "partially_supported",
        "status": "supported",
        "limitations": "num_key_value_heads is mandatory; "
        "num_attention_heads is never a substitute",
    },
    "transformer_mqa": {
        "architecture_family": "transformer_mqa",
        "weight_estimation": "supported",
        "cache_estimation": "supported",
        "runtime_overhead_estimation": "unknown",
        "classification_support": "partially_supported",
        "status": "supported",
        "limitations": "single kv head shared across query heads; verify per runtime",
    },
    "moe": {
        "architecture_family": "moe",
        "weight_estimation": "supported",
        "cache_estimation": "supported",
        "runtime_overhead_estimation": "unknown",
        "classification_support": "partially_supported",
        "status": "partially_supported",
        "limitations": "weight residency uses total resident tensors; active parameters "
        "never measure residency without runtime-specific proof",
    },
    "sliding_window_transformer": {
        "architecture_family": "sliding_window_transformer",
        "weight_estimation": "supported",
        "cache_estimation": "partially_supported",
        "runtime_overhead_estimation": "unknown",
        "classification_support": "partially_supported",
        "status": "partially_supported",
        "limitations": "window sizes, layer pattern, and runtime behavior must all be known",
    },
    "mla": {
        "architecture_family": "mla",
        "weight_estimation": "supported",
        "cache_estimation": "unsupported",
        "runtime_overhead_estimation": "unknown",
        "classification_support": "unsupported",
        "status": "unsupported",
        "limitations": "multi-head latent attention needs an architecture-specific cache model",
    },
    "mamba_ssm": {
        "architecture_family": "mamba_ssm",
        "weight_estimation": "supported",
        "cache_estimation": "unsupported",
        "runtime_overhead_estimation": "unknown",
        "classification_support": "unsupported",
        "status": "unsupported",
        "limitations": "recurrent/state cache needs SSM state dimensions, not a KV formula",
    },
    "hybrid": {
        "architecture_family": "hybrid",
        "weight_estimation": "supported",
        "cache_estimation": "unsupported",
        "runtime_overhead_estimation": "unknown",
        "classification_support": "unsupported",
        "status": "unsupported",
        "limitations": "correct accounting sums component-specific models; "
        "never reduce to the nearest transformer",
    },
    "unknown": {
        "architecture_family": "unknown",
        "weight_estimation": "unknown",
        "cache_estimation": "unknown",
        "runtime_overhead_estimation": "unknown",
        "classification_support": "unsupported",
        "status": "unknown",
        "limitations": "absent architecture metadata refuses calculation",
    },
}


def architecture_status(architecture_family: str | None) -> dict:
    """إرجاع صف الدعم لمعمارية ما أو صف المجهول دون تخمين."""
    if not isinstance(architecture_family, str):
        return ARCHITECTURE_SUPPORT["unknown"]
    return ARCHITECTURE_SUPPORT.get(architecture_family.lower(), ARCHITECTURE_SUPPORT["unknown"])


def cache_supported(architecture_family: str | None) -> bool:
    """التحقق من دعم تقدير الكاش قبل تطبيق أي معادلة KV."""
    return architecture_status(architecture_family).get("cache_estimation") == "supported"

"""تقدير كاش KV والحالة: المعادلة القياسية فقط للمعماريات المطابقة."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atlas.archinfo.layer_plan import LayerPlan


class UnsupportedArchitectureError(ValueError):
    """رفع صريح عند طلب كاش لمعمارية غير مدعومة بدل الرقم المزيف."""


class InsufficientCacheEvidenceError(ValueError):
    """رفع صريح عند غياب حقل حرج للكاش بدل الصفر المضلل."""


# المعماريات التي تقبل المعادلة القياسية حصرًا (مسميات المرحلة الثانية).
_STANDARD_CACHE_FAMILIES = frozenset(
    {
        "standard_transformer",
        "transformer_gqa",
        "transformer_mqa",
        "moe",
    }
)


def _standard_family_eligible(family: str) -> bool:
    """Phase 2 estimator names plus Phase 3 canonical standard-attention families.

    MLA/SSM/hybrid families are disjoint from both sets and always refuse.
    """
    if family in _STANDARD_CACHE_FAMILIES:
        return True
    from atlas.archinfo.capabilities import STANDARD_KV_FAMILIES

    return family in STANDARD_KV_FAMILIES


def _require_standard_family(architecture_family: str | None) -> str:
    """Gate the standard KV equation to eligible families or refuse explicitly."""
    family = (architecture_family or "unknown").lower()
    if not _standard_family_eligible(family):
        raise UnsupportedArchitectureError(
            f"unsupported_architecture_for_estimation: {architecture_family!r}"
        )
    return family


def _require_positive_int(name: str, value: int | None) -> int:
    """التحقق من عدد صحيح موجب أو الرفض الصريح."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise InsufficientCacheEvidenceError(f"missing or invalid {name}: {value!r}")
    return value


def estimate_kv_cache_bytes(
    *,
    architecture_family: str | None,
    num_layers: int | None,
    num_kv_heads: int | None,
    head_dim: int | None,
    context_tokens: int | None,
    bytes_per_element: float | None,
    sequence_count: int = 1,
    num_attention_heads: int | None = None,
    sliding_window: int | None = None,
    kv_block_size: int | None = None,
    kv_scale_bytes_per_block: int | None = None,
) -> int:
    """تقدير كاش KV بالبايت للمعماريات القياسية فقط.

    تستخدم رؤوس القيمة-المفتاح لا رؤوس الاستعلام، وترفض MLA/SSM/الهجين.
    """
    _require_standard_family(architecture_family)
    layers = _require_positive_int("num_layers", num_layers)
    # قاعدة GQA/MQA الإلزامية: رؤوس KV هي المستخدمة أبدًا.
    kv_heads = _require_positive_int("num_key_value_heads", num_kv_heads)
    if num_attention_heads is not None and num_kv_heads is None:
        raise InsufficientCacheEvidenceError(
            "num_attention_heads cannot substitute num_key_value_heads"
        )
    dim = _require_positive_int("head_dim", head_dim)
    tokens = _require_positive_int("context_tokens", context_tokens)
    sequences = _require_positive_int("sequence_count", sequence_count)
    if (
        bytes_per_element is None
        or isinstance(bytes_per_element, bool)
        or not isinstance(bytes_per_element, (int, float))
        or bytes_per_element <= 0
    ):
        raise InsufficientCacheEvidenceError(
            f"missing or invalid bytes_per_element: {bytes_per_element!r}"
        )
    effective_tokens = tokens
    if sliding_window is not None:
        window = _require_positive_int("sliding_window", sliding_window)
        effective_tokens = min(tokens, window)
    if kv_block_size is not None or kv_scale_bytes_per_block is not None:
        # كاش مكمم قائم على الكتل: لا تستخدم bits/8 المثالية وحدها.
        block = _require_positive_int("kv_block_size", kv_block_size)
        scale = _require_positive_int("kv_scale_bytes_per_block", kv_scale_bytes_per_block)
        bits = float(bytes_per_element) * 8.0
        quant_bytes = bits / 8.0 * block + scale
        per_token = 2 * layers * kv_heads * dim * (quant_bytes / block)
    else:
        per_token = 2 * layers * kv_heads * dim * float(bytes_per_element)
    return int(sequences * effective_tokens * per_token)


def estimate_kv_cache_layer_plan(
    plan: LayerPlan,
    *,
    architecture_family: str | None,
    context_tokens: int | None,
    bytes_per_element: float | None,
    sequence_count: int = 1,
) -> int:
    """Sum per-layer KV bytes from a Layer Plan without flattening globals.

    Layers without attention contribute zero only when attention_present is
    explicitly False; layers with unknown attention presence refuse instead
    of silently becoming zero. Formula: standard-kv-layer-plan-v1.
    """
    from atlas.archinfo.layer_plan import attention_layer_count

    _require_standard_family(architecture_family)
    tokens = _require_positive_int("context_tokens", context_tokens)
    sequences = _require_positive_int("sequence_count", sequence_count)
    if (
        bytes_per_element is None
        or isinstance(bytes_per_element, bool)
        or not isinstance(bytes_per_element, (int, float))
        or bytes_per_element <= 0
    ):
        raise InsufficientCacheEvidenceError(
            f"missing or invalid bytes_per_element: {bytes_per_element!r}"
        )
    if plan.layer_count <= 0 or not plan.entries:
        raise InsufficientCacheEvidenceError("empty layer plan: refusing calculation")
    if attention_layer_count(plan) == 0 and any(e.attention_present is None for e in plan.entries):
        raise InsufficientCacheEvidenceError(
            "unknown attention presence in layer plan: refusing, not zero"
        )
    total = 0
    for entry in plan.entries:
        if entry.attention_present is False:
            continue
        if entry.attention_present is None:
            raise InsufficientCacheEvidenceError(
                f"layer {entry.layer_index}: unknown attention presence"
            )
        kv_heads = _require_positive_int(
            f"num_key_value_heads[layer {entry.layer_index}]", entry.num_key_value_heads
        )
        dim = _require_positive_int(f"head_dim[layer {entry.layer_index}]", entry.head_dim)
        effective = tokens
        if entry.sliding_window is not None:
            window = _require_positive_int(
                f"sliding_window[layer {entry.layer_index}]", entry.sliding_window
            )
            effective = min(tokens, window)
        total += int(2 * sequences * effective * kv_heads * dim * float(bytes_per_element))
    return total

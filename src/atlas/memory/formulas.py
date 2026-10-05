"""سجل الصيغ: كل معادلة تحمل هويتها وافتراضاتها ومصادرها."""

from __future__ import annotations

FORMULA_REGISTRY: dict[str, dict] = {
    "weight-bpw-v1": {
        "formula_id": "weight-bpw-v1",
        "formula_version": "1",
        "architecture_family": "any",
        "runtime_constraints": "none; device-resident fp/quant weight bytes only",
        "assumptions": "total resident parameter count and documented bits-per-weight "
        "apply uniformly; MoE uses total resident tensors, never active parameters",
        "source_refs": ["atlas-memory-model-v1"],
    },
    "standard-kv-v1": {
        "formula_id": "standard-kv-v1",
        "formula_version": "1",
        "architecture_family": "standard_transformer",
        "runtime_constraints": "unquantized K/V with equal bytes per element; "
        "no sliding window; no MLA; no SSM layers",
        "assumptions": "2 * sequences * tokens * layers * kv_heads * head_dim * bytes_per_element",
        "source_refs": ["atlas-memory-model-v1"],
    },
    "quantized-kv-block-v1": {
        "formula_id": "quantized-kv-block-v1",
        "formula_version": "1",
        "architecture_family": "standard_transformer",
        "runtime_constraints": "runtime block definition (block size, scale bytes) must be known",
        "assumptions": "block storage = quant bytes + scale/metadata bytes per block; "
        "ideal bit-packing alone is never storage truth",
        "source_refs": ["atlas-memory-model-v1"],
    },
    "sliding-window-kv-v1": {
        "formula_id": "sliding-window-kv-v1",
        "formula_version": "1",
        "architecture_family": "sliding_window_transformer",
        "runtime_constraints": "per-layer window sizes, layer pattern, and runtime behavior known",
        "assumptions": "each windowed layer caches at most window tokens; "
        "non-windowed layers use full calculation context",
        "source_refs": ["atlas-memory-model-v1"],
    },
    "standard-kv-layer-plan-v1": {
        "formula_id": "standard-kv-layer-plan-v1",
        "formula_version": "1",
        "architecture_family": "standard_transformer",
        "runtime_constraints": "unquantized K/V with equal bytes per element; "
        "layer plan with per-layer kv heads, head dim, and attention presence",
        "assumptions": "sum over attention layers of "
        "2 * sequences * effective_tokens(layer) * kv_heads(layer) * "
        "head_dim(layer) * bytes_per_element; layers without attention "
        "contribute zero only when explicitly marked; unknown stays unknown",
        "source_refs": ["atlas-phase-03-layer-plan"],
    },
}


def formula_ref(formula_id: str) -> dict:
    """إرجاع مرجع الصيغة الموثقة أو رفع خطأ عند غيابها."""
    try:
        return FORMULA_REGISTRY[formula_id]
    except KeyError as exc:
        raise KeyError(f"unknown memory formula: {formula_id!r}") from exc

"""ملفات runtime للذاكرة: السلوك الموثق دون overhead مخترع."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeMemoryProfile:
    """ملف ذاكرة runtime؛ المجهول يبقى None ولا يتحول إلى رقم عشوائي."""

    runtime_name: str
    runtime_version: str | None = None
    backend: str | None = None
    device_family: str | None = None
    weight_loading_behavior: str | None = None
    kv_cache_type: str | None = None
    kv_cache_quantization: str | None = None
    workspace_behavior: str | None = None
    graph_behavior: str | None = None
    known_static_overhead_bytes: int | None = None
    known_dynamic_overhead_bytes: int | None = None
    measurement_source: str | None = None
    source_revision: str | None = None
    verification_status: str = "unknown"


# عائلات runtime التي يستطيع النظام تمثيلها دون ادعاء دعم شامل.
RUNTIME_FAMILIES: tuple[str, ...] = (
    "llama.cpp",
    "exllamav2",
    "tensorrt-llm",
    "transformers",
    "mlx-lm",
    "ollama",
    "lm-studio",
    "unknown",
)

# ملفات هندسية صريحة بلا overhead مخترع؛ القيم العددية غائبة عمدًا.
_KNOWN_PROFILES: dict[str, RuntimeMemoryProfile] = {
    "llama.cpp-cuda-full-offload": RuntimeMemoryProfile(
        runtime_name="llama.cpp",
        backend="CUDA",
        weight_loading_behavior="full GPU offload maps device tensors; partial offload "
        "needs a real layer placement map",
        kv_cache_type="standard KV with optional KV-cache quantization modes",
        verification_status="source_reported",
    ),
    "exllamav2-cuda-full-offload": RuntimeMemoryProfile(
        runtime_name="exllamav2",
        backend="CUDA",
        weight_loading_behavior="EXL2 mixed-precision weights load per measured plan",
        kv_cache_type="standard KV",
        verification_status="source_reported",
    ),
    "mlx-lm-unified-memory": RuntimeMemoryProfile(
        runtime_name="mlx-lm",
        backend="unified memory",
        weight_loading_behavior="unified memory model; device/host split differs "
        "from discrete GPUs",
        kv_cache_type="KV with runtime quantization options",
        verification_status="source_reported",
    ),
    "tensorrt-llm-cuda-engine": RuntimeMemoryProfile(
        runtime_name="tensorrt-llm",
        backend="CUDA",
        weight_loading_behavior="engine-dependent recipes; NVFP4/MXFP4 support varies "
        "by model, runtime version, and hardware generation",
        kv_cache_type="paged KV with recipe-dependent quantization",
        verification_status="source_reported",
    ),
}


def find_runtime_profile(profile_id: str | None) -> RuntimeMemoryProfile | None:
    """البحث عن ملف runtime معروف أو None دون اختراع ملف افتراضي صامت."""
    if not profile_id or not isinstance(profile_id, str):
        return None
    return _KNOWN_PROFILES.get(profile_id.strip())


def list_runtime_profiles() -> list[RuntimeMemoryProfile]:
    """سرد الملفات الهندسية الصريحة المعروفة فقط."""
    return list(_KNOWN_PROFILES.values())

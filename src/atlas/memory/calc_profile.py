"""ملف الحساب: سياق التقدير الصريح دون runtime افتراضي صامت."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CalculationProfile:
    """شروط التقدير الكاملة؛ لا VRAM estimate بلا ملف حساب."""

    profile_id: str
    profile_version: str
    context_tokens: int
    sequence_count: int
    kv_dtype: str | None = None
    kv_quantization: str | None = None
    runtime: str | None = None
    backend: str | None = None
    offload_mode: str = "full"
    multimodal_mode: str = "text_only"


# خط الأساس النصي التفاعلي الصريح من المرحلة الثانية.
ATLAS_TEXT_8K_BASELINE_V1 = CalculationProfile(
    profile_id="atlas-text-8k-baseline-v1",
    profile_version="1",
    context_tokens=8192,
    sequence_count=1,
    kv_dtype="fp16",
    kv_quantization=None,
    runtime=None,
    backend=None,
    offload_mode="full",
    multimodal_mode="text_only",
)


def validate_profile(profile: CalculationProfile | None) -> list[str]:
    """التحقق من صراحة الملف وإرجاع الأخطاء دون استثناءات."""
    errors: list[str] = []
    if profile is None:
        return ["calculation profile is required; no silent runtime default"]
    if not profile.profile_id:
        errors.append("profile_id is required and must be explicit")
    if profile.context_tokens <= 0:
        errors.append("context_tokens must be positive")
    if profile.sequence_count <= 0:
        errors.append("sequence_count must be positive")
    if profile.offload_mode not in ("full", "partial", "unknown"):
        errors.append(f"unknown offload_mode: {profile.offload_mode!r}")
    return errors


# خريطة الدقة المعلنة إلى بايت العنصر دون تخمين لغير المدرج.
_KV_DTYPE_BYTES = {"fp32": 4.0, "fp16": 2.0, "bf16": 2.0, "fp8": 1.0, "int8": 1.0}


def kv_bytes_per_element(kv_dtype: str | None) -> float | None:
    """بايت عنصر الكاش من الدقة المعلنة أو None للمجهول."""
    if not isinstance(kv_dtype, str) or not kv_dtype.strip():
        return None
    return _KV_DTYPE_BYTES.get(kv_dtype.strip().lower())

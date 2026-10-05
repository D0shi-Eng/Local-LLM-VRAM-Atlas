"""التطبيع الحتمي: تحويل البيانات الخام إلى سجل أطلس معياري."""

from __future__ import annotations

import re

from atlas.intake.format import bytes_to_gib, round_gib
from atlas.intake.licenses import resolve_license
from atlas.intake.lineage import resolve_lineage
from atlas.intake.models import RawModelMetadata

# تعبير المطابقة لرمز الكم من اسم الملف دون ادعاء التحقق.
_QUANT_TOKEN = re.compile(
    r"(BF16|FP16|FP32|MXFP4(?:_[A-Z0-9]+)?|NVFP4(?:_[A-Z0-9]+)?|"
    r"Q2(?:_K(?:_[A-Z]+)?)?|IQ2(?:_[A-Z]+)?|Q3(?:_K(?:_[A-Z]+)?)?|IQ3(?:_[A-Z]+)?|"
    r"Q4(?:_[A-Z0-9]+)+|IQ4(?:_[A-Z0-9]+)+|Q5(?:_K(?:_[A-Z]+)?)?|IQ5(?:_[A-Z]+)?|"
    r"Q6(?:_K(?:_[A-Z]+)?)?|Q8(?:_0)?|IQ1(?:_[A-Z]+)?|TQ\d+[A-Z_]*)",
    re.IGNORECASE,
)

# خريطة مختصرة من رمز الملف إلى عائلة الكم المعيارية.
_QUANT_FAMILY_MAP = {
    "BF16": "bf16",
    "FP16": "fp16",
    "FP32": "fp32",
    "MXFP4": "mxfp4",
    "NVFP4": "nvfp4",
    "Q2": "q2",
    "IQ2": "iq2",
    "Q3": "q3",
    "IQ3": "iq3",
    "Q4": "q4",
    "IQ4": "iq4",
    "Q5": "q5",
    "Q6": "q6",
    "Q8": "q8",
    "IQ1": "iq1",
    "TQ": "tq",
}


def model_id_from_repo(repo_id: str) -> str:
    """اشتقاق معرف آلة حتمي من معرف المستودع دون إتلاف الأصل."""
    lowered = repo_id.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if len(slug) < 2:
        slug = (slug + "-model").strip("-")
    return slug[:121]


def quant_family_from_token(token: str | None) -> str:
    """تصنيف رمز الكم المستخرج من اسم الملف إلى عائلة معلومة."""
    if not token:
        return "unknown"
    head = re.split(r"[_-]", token.upper(), maxsplit=1)[0]
    return _QUANT_FAMILY_MAP.get(head, "unknown")


def extract_quant_token(filename: str) -> str | None:
    """استخراج مرشح رمز الكم من اسم الملف كإشارة غير متحقق منها."""
    match = _QUANT_TOKEN.search(filename.upper())
    return match.group(1).upper() if match else None


def infer_modalities(pipeline_tag: str | None, tags: tuple[str, ...]) -> list[str]:
    """استنتاج الوسائط من الوسوم المعلنة فقط دون تخمين القدرات."""
    joined = " ".join([*(tags or ()), pipeline_tag or ""]).lower()
    modalities = ["text"]
    if any(key in joined for key in ("image", "vision", "multimodal", "vlm")):
        modalities.append("vision")
    if "audio" in joined:
        modalities.append("audio")
    if "video" in joined:
        modalities.append("video")
    return sorted(set(modalities))


def _detect_quantization(raw: RawModelMetadata) -> tuple[dict | None, list[str]]:
    """بناء كتلة التكميم من مخزون الملفات المبلغ عنه دون تنزيل."""
    warnings: list[str] = []
    gguf_files = [a for a in raw.siblings if a.extension == ".gguf"]
    st_files = [a for a in raw.siblings if a.extension == ".safetensors"]
    if gguf_files:
        # اختيار أكبر ملف كممثل للحجم دون ادعاء أنه كل الأوزان.
        biggest = max(gguf_files, key=lambda a: a.source_reported_size_bytes or -1)
        token = extract_quant_token(biggest.filename)
        family = quant_family_from_token(token)
        size_bytes = biggest.source_reported_size_bytes
        block: dict = {
            "format": "GGUF",
            "quant_family": family,
            "quant_name": token,
            "bits_per_weight": None,
            # الدقة الكاملة المبلغ عنها بالاسم ليست تكميمًا لاحقًا.
            "native_quantization": None if family in ("bf16", "fp16", "fp32") else False,
            "compression_category": None,
            "quantizer": None,
            "quantizer_repo": None,
            "file_size_bytes": size_bytes,
            "file_size_gib": round_gib(bytes_to_gib(size_bytes))
            if isinstance(size_bytes, int)
            else None,
            "split_files": len(gguf_files) > 1,
            "source_revision": raw.resolved_revision,
            "checksum": None,
        }
        if len(gguf_files) > 1:
            warnings.append(
                "multi_quant_repository: record reflects the largest reported artifact only"
            )
        if token is None:
            warnings.append("quant_token_not_found_in_filename: recorded as unknown")
        else:
            warnings.append("quantization_from_filename_inference_only: not independently verified")
        return block, warnings
    if st_files:
        sizes = [
            a.source_reported_size_bytes
            for a in st_files
            if isinstance(a.source_reported_size_bytes, int)
        ]
        total = sum(sizes) if sizes else None
        return {
            "format": "safetensors",
            "quant_family": "unknown",
            "quant_name": None,
            "bits_per_weight": None,
            "native_quantization": None,
            "compression_category": None,
            "quantizer": None,
            "quantizer_repo": None,
            "file_size_bytes": total,
            "file_size_gib": round_gib(bytes_to_gib(total)) if isinstance(total, int) else None,
            "split_files": len(st_files) > 1,
            "source_revision": raw.resolved_revision,
            "checksum": None,
        }, warnings
    return None, warnings


def _detect_alignment(raw: RawModelMetadata) -> tuple[dict, list[str]]:
    """تسجيل ادعاءات المحاذاة كما أعلنها الناشر دون اختبار رفض."""
    warnings: list[str] = []
    joined = " ".join([raw.repo_id, *(raw.tags or ())]).lower()
    variant = "unknown"
    claimed: bool | None = None
    method: str | None = None
    for keyword, label in (
        ("heretic", "heretic"),
        ("abliterat", "abliterated"),
        ("uncensor", "uncensored"),
    ):
        if keyword in joined:
            variant = label
            claimed = True
            method = "publisher_or_variant_author_claim"
            warnings.append(f"alignment_claim_recorded_as_publisher_claim: {label}")
            break
    base = raw.base_models_raw[0].strip() if raw.base_models_raw else None
    return {
        "alignment_variant": variant,
        "uncensored_claimed": claimed,
        "uncensoring_method": method,
        "method_documented": None,
        "base_model": base,
        "variant_author": raw.namespace,
        "variant_source": raw.source_url,
        "capability_retention_evidence": None,
        "refusal_evaluation": None,
        "verification_status": "publisher_claim" if claimed else "unknown",
    }, warnings


def normalize(raw: RawModelMetadata) -> tuple[dict, list[str]]:
    """بناء السجل المعياري المرشح من اللقطة الخام مع حفظ عدم اليقين."""
    warnings: list[str] = list(raw.warnings)
    model_id = model_id_from_repo(raw.repo_id)
    edges = resolve_lineage(raw.base_models_raw)
    license_info = resolve_license(raw.license_raw, license_source="model_card_metadata")

    # النوع المعماري المعلن فقط وإلا مجهول مع الحفاظ على صلاحية المخطط.
    arch_type = (raw.architecture_type_raw or "unknown").strip().lower()
    if arch_type not in ("dense", "moe", "hybrid", "unknown"):
        warnings.append(f"architecture_type_unrecognized: {raw.architecture_type_raw!r} -> unknown")
        arch_type = "unknown"
    experts_total = raw.experts_total
    experts_active = raw.experts_active
    if arch_type == "moe" and (experts_total is None or experts_active is None):
        # المخطط يشترط أعداد الخبراء لنماذج MoE فلا يجوز ادعاؤها دون دليل.
        warnings.append("moe_claim_without_expert_counts: downgraded to unknown")
        arch_type = "unknown"

    total_params = raw.total_parameters_b
    if total_params is not None and not (
        isinstance(total_params, (int, float)) and total_params > 0
    ):
        warnings.append("invalid_total_parameters: recorded as unknown")
        total_params = None

    quantization, quant_warnings = _detect_quantization(raw)
    warnings.extend(quant_warnings)
    alignment, align_warnings = _detect_alignment(raw)
    warnings.extend(align_warnings)

    if raw.conflicts:
        warnings.extend(f"conflict_detected: {item}" for item in raw.conflicts)

    # حالة الكتالوج الأقرب لمعنى الاستقبال دون استخدام حالات محظورة.
    if raw.gated or raw.private:
        catalog_status = "discovered"
    elif license_info.verification_status == "unknown":
        catalog_status = "pending_license"
    elif arch_type == "unknown" and total_params is None:
        catalog_status = "pending_metadata"
    elif edges and raw.base_models_raw:
        catalog_status = "experimental"
    else:
        catalog_status = "experimental"

    record: dict = {
        "schema_version": "0.1.0",
        "model_id": model_id,
        "display_name": raw.repo_id,
        "slug": model_id,
        "creator": raw.author or raw.namespace or "unknown",
        "organization": None,
        "model_family": None,
        "base_models": [edge.target for edge in edges],
        "release_date": None,
        "last_verified_at": None,
        "architecture": raw.architecture_raw or "unknown",
        "architecture_type": arch_type,
        "total_parameters_b": total_params,
        "active_parameters_b": raw.active_parameters_b,
        "experts_total": experts_total if arch_type == "moe" else None,
        "experts_active": experts_active if arch_type == "moe" else None,
        "context_length": {
            "advertised_max": raw.context_advertised,
            "tested": None,
            "vram_measurement_context": None,
        },
        "modalities": infer_modalities(raw.pipeline_tag, raw.tags),
        "multimodal_components": None,
        "openness": license_info.openness,
        "open_source_ai_reference": None,
        "license": {
            "license_id": license_info.normalized_id,
            "license_name": None,
            "license_url": None,
            "license_source": license_info.license_source,
            "commercial_use_status": "unclear",
            "redistribution_status": "unclear",
            "derivative_use_status": "unclear",
            "license_notes": (
                f"raw_license_value={license_info.raw_value!r}; spdx={license_info.is_spdx}"
            ),
            "verification_status": license_info.verification_status,
        },
        "alignment": alignment,
        "verification": {
            "status": "publisher_claim",
            "evidence_ids": [],
        },
        "catalog_status": catalog_status,
        "lifecycle_status": "unavailable"
        if (raw.disabled or (raw.gated and raw.resolved_revision is None))
        else "active",
        "lifecycle_reason": None,
        "popularity": {
            "downloads": raw.downloads,
            "likes": raw.likes,
            "trending": None,
            "captured_at": raw.retrieved_at,
        },
    }
    if quantization is not None:
        record["quantization"] = quantization
    # لا تُسند أي طبقة VRAM في المرحلة الأولى: حقل vram يُحذف عمدًا.
    record.pop("vram", None)
    return record, warnings

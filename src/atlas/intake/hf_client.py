"""عميل مصدر Hugging Face: قراءة عامة مجهولة للبيانات الوصفية فقط."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from atlas.intake.errors import (
    AuthenticationRequiredError,
    GatedResourceError,
    IntakeError,
    InvalidMetadataError,
    NetworkTimeoutError,
    NotFoundError,
    RateLimitedError,
    RevisionNotFoundError,
    SourceUnavailableError,
)
from atlas.intake.models import RawArtifact, RawModelMetadata
from atlas.intake.url_safety import assert_safe_url

# مهلة افتراضية محدودة لكل طلب شبكي.
DEFAULT_TIMEOUT = 15.0
# عدد محدود من المحاولات للأخطاء المؤقتة فقط دون حلقات لا نهائية.
MAX_ATTEMPTS = 2


def utc_now_iso() -> str:
    """طابع زمني بصيغة ISO 8601 مع منطقة زمنية صريحة."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_repo_id(repo_id: str) -> tuple[str, str]:
    """التحقق من شكل معرف المستودع وإرجاع النطاق والاسم."""
    if not isinstance(repo_id, str) or "/" not in repo_id:
        raise InvalidMetadataError(f"invalid repo_id (expected namespace/name): {repo_id!r}")
    namespace, name = repo_id.split("/", 1)
    namespace = namespace.strip()
    name = name.strip()
    if not namespace or not name or " " in repo_id or "\\" in repo_id:
        raise InvalidMetadataError(f"invalid repo_id: {repo_id!r}")
    return namespace, name


def _string_or_none(value: Any) -> str | None:
    """تحويل القيم النصية المحتملة إلى نص أو لا شيء دون تخمين."""
    if value is None:
        return None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _int_or_none(value: Any) -> int | None:
    """تحويل القيم العددية المحتملة إلى عدد صحيح أو لا شيء."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, float) and value.is_integer() and value >= 0:
        return int(value)
    return None


def _float_or_none(value: Any) -> float | None:
    """تحويل القيم العددية المحتملة إلى عدد عشري أو لا شيء."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    return None


def _card_value(card_data: Any, *names: str) -> Any:
    """قراءة قيمة من بيانات البطاقة سواء كانت قاموسًا أو كائنًا."""
    if card_data is None:
        return None
    for name in names:
        if isinstance(card_data, dict) and card_data.get(name) is not None:
            return card_data.get(name)
        candidate = getattr(card_data, name, None)
        if candidate is not None:
            return candidate
    return None


def _as_str_tuple(value: Any) -> tuple[str, ...]:
    """تحويل قيمة مفردة أو قائمة إلى صف نصي نظيف."""
    if value is None:
        return ()
    items = value if isinstance(value, (list, tuple)) else [value]
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    return tuple(cleaned)


def extract_license_raw(card_data: Any, tags: list[str]) -> str | list[str] | None:
    """استخراج قيمة الترخيص الخام من البطاقة أو الوسوم دون تطبيع."""
    direct = _card_value(card_data, "license", "licenses")
    if isinstance(direct, (list, tuple)) and direct:
        cleaned = [str(item).strip() for item in direct if str(item).strip()]
        if cleaned:
            return cleaned if len(cleaned) > 1 else cleaned[0]
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    licensed = [
        tag.split("license:", 1)[1].strip() for tag in tags if tag.lower().startswith("license:")
    ]
    licensed = [item for item in licensed if item]
    if not licensed:
        return None
    return licensed[0] if len(licensed) == 1 else licensed


def extract_base_models_raw(card_data: Any, info_bases: Any) -> tuple[str, ...]:
    """استخراج إعلانات النموذج الأساس من البطاقة أو الحقول المباشرة."""
    from_card = _as_str_tuple(
        _card_value(card_data, "base_model", "base_models", "base_model_relation")
    )
    if from_card:
        return from_card
    return _as_str_tuple(info_bases)


def extract_architecture_raw(config: Any, card_data: Any, transformers_info: Any) -> str | None:
    """استخراج اسم البنية المعلنة فقط دون استنتاج من الاسم."""
    for source in (config, transformers_info):
        for key in ("architectures", "architecture", "model_type"):
            value = source.get(key) if isinstance(source, dict) else getattr(source, key, None)
            if isinstance(value, (list, tuple)) and value:
                first = str(value[0]).strip()
                if first:
                    return first
            elif isinstance(value, str) and value.strip():
                return value.strip()
    direct = _card_value(card_data, "architecture", "model_type")
    return _string_or_none(direct)


def extract_context_raw(config: Any, card_data: Any) -> int | None:
    """استخراج السياق المعلن من الحقول البنيوية فقط."""
    candidates: list[Any] = []
    for source in (config, card_data):
        for key in (
            "max_position_embeddings",
            "max_sequence_length",
            "context_length",
            "max_context",
            "sliding_window",
        ):
            value = source.get(key) if isinstance(source, dict) else getattr(source, key, None)
            candidates.append(value)
    for candidate in candidates:
        parsed = _int_or_none(candidate)
        if parsed:
            return parsed
    return None


def extract_total_params_b(safetensors: Any, gguf_info: Any) -> float | None:
    """استخراج عدد المعاملات الإجمالي بالمليارات من الحقول البنيوية فقط."""
    for source in (safetensors, gguf_info):
        if source is None:
            continue
        total = source.get("total") if isinstance(source, dict) else getattr(source, "total", None)
        params = _float_or_none(total)
        if params and params >= 1_000_000:
            return params / 1_000_000_000
        for key in ("total_params", "total_parameters", "parameters"):
            value = source.get(key) if isinstance(source, dict) else getattr(source, key, None)
            params = _float_or_none(value)
            if params and params >= 1_000_000:
                return params / 1_000_000_000
            if params and 0 < params < 10_000:
                # قيمة تبدو بالمليارات أصلًا في بعض الاستجابات.
                return params
    return None


def extract_artifacts(siblings: Any) -> tuple[RawArtifact, ...]:
    """بناء مخزون الملفات من قائمة الإخوة دون تنزيل أي محتوى."""
    items: list[RawArtifact] = []
    for sibling in siblings or []:
        if isinstance(sibling, dict):
            filename = str(sibling.get("rfilename") or sibling.get("filename") or "").strip()
            size = sibling.get("size")
            lfs = sibling.get("lfs")
            blob_id = sibling.get("sha256") or sibling.get("blob_id") or sibling.get("sha")
        else:
            filename = str(getattr(sibling, "rfilename", "") or "").strip()
            size = getattr(sibling, "size", None)
            lfs = getattr(sibling, "lfs", None)
            blob_id = getattr(sibling, "sha256", None) or getattr(sibling, "blob_id", None)
        if not filename:
            continue
        # الدفاع الاستباقي: مجرد ذكر اسم وزن لا يعني تنزيله أبدًا.
        assert_not_weight_path_allowed_for_inventory(filename)
        lowered = filename.lower()
        extension = ""
        if "." in lowered.rsplit("/", 1)[-1]:
            extension = "." + lowered.rsplit(".", 1)[-1]
        storage = None
        if isinstance(lfs, dict):
            storage = "lfs" if lfs else None
        elif lfs:
            storage = "lfs"
        items.append(
            RawArtifact(
                filename=filename,
                path=filename,
                extension=extension,
                source_reported_size_bytes=_int_or_none(size),
                source_reported_storage=storage,
                source_reported_hash=str(blob_id)[:128] if blob_id else None,
            )
        )
    return tuple(items)


def assert_not_weight_path_allowed_for_inventory(filename: str) -> None:
    """السماح بذكر اسم الوزن في المخزون مع منع تنزيله في أي مسار آخر."""
    # هذه الدالة توثق أن المخزون يسجل الأسماء فقط ولا ينزل المحتوى.
    if not isinstance(filename, str) or not filename.strip():
        raise InvalidMetadataError("empty sibling filename from source")


def build_raw_from_model_info(
    info: Any,
    *,
    repo_id: str,
    requested_revision: str,
    retrieved_at: str,
) -> RawModelMetadata:
    """تحويل كائن معلومات النموذج إلى DTO خام مستقل عن SDK."""
    namespace, _ = validate_repo_id(repo_id)
    tags = [str(tag) for tag in (getattr(info, "tags", None) or [])]
    card_data = getattr(info, "card_data", None)
    config = getattr(info, "config", None)
    transformers_info = getattr(info, "transformers_info", None)
    siblings = getattr(info, "siblings", None)
    gated = getattr(info, "gated", None)
    private = bool(getattr(info, "private", False))
    disabled = bool(getattr(info, "disabled", False))
    resolved = getattr(info, "sha", None)
    author = getattr(info, "author", None)
    conflicts: list[str] = []
    license_raw = extract_license_raw(card_data, tags)
    base_raw = extract_base_models_raw(card_data, getattr(info, "base_models", None))
    architecture = extract_architecture_raw(config, card_data, transformers_info)
    total_b = extract_total_params_b(
        getattr(info, "safetensors", None), getattr(info, "gguf", None)
    )
    context = extract_context_raw(config, card_data)
    languages = _as_str_tuple(_card_value(card_data, "language", "languages"))
    datasets = _as_str_tuple(_card_value(card_data, "datasets", "dataset"))
    warnings: list[str] = []
    gated_flag = (
        bool(gated) if isinstance(gated, bool) else str(gated).lower() == "true" if gated else False
    )
    if gated_flag:
        warnings.append("repository_reports_gated_status: anonymous metadata may be incomplete")
    source_url = f"https://huggingface.co/{repo_id}"
    assert_safe_url(source_url)
    card_text: str | None = None
    card_obj = getattr(info, "card_data", None)
    if isinstance(card_obj, dict):
        maybe_text = card_obj.get("model_card_text")
        card_text = maybe_text[:4000] if isinstance(maybe_text, str) else None
    return RawModelMetadata(
        platform="hugging-face",
        repo_id=repo_id,
        namespace=namespace,
        repo_name=repo_id.split("/", 1)[1],
        source_url=source_url,
        requested_revision=requested_revision,
        resolved_revision=str(resolved).strip() if resolved else None,
        retrieved_at=retrieved_at,
        author=_string_or_none(author),
        tags=tuple(tags),
        pipeline_tag=_string_or_none(getattr(info, "pipeline_tag", None)),
        library_name=_string_or_none(getattr(info, "library_name", None)),
        license_raw=license_raw,
        base_models_raw=base_raw,
        languages=languages,
        datasets_raw=datasets,
        architecture_raw=architecture,
        architecture_type_raw=None,
        total_parameters_b=total_b,
        active_parameters_b=None,
        experts_total=None,
        experts_active=None,
        context_advertised=context,
        gated=gated_flag,
        private=private,
        disabled=disabled,
        downloads=_int_or_none(getattr(info, "downloads", None)),
        likes=_int_or_none(getattr(info, "likes", None)),
        trending_score=None,
        card_text=card_text,
        siblings=extract_artifacts(siblings),
        conflicts=tuple(conflicts),
        warnings=tuple(warnings),
    )


def map_hub_exception(exc: Exception, repo_id: str) -> IntakeError:
    """ترجمة استثناءات المكتبة الرسمية إلى دلالات فشل المشروع."""
    name = type(exc).__name__
    message = str(exc)
    lowered = message.lower()
    if (
        name in ("RepositoryNotFoundError", "RepoNotFoundError")
        or "repository not found" in lowered
    ):
        if "gated" in lowered:
            return GatedResourceError(f"gated repository (anonymous access): {repo_id}")
        if "private" in lowered or "401" in lowered or "403" in lowered:
            return AuthenticationRequiredError(f"authentication required or private: {repo_id}")
        return NotFoundError(f"repository not found: {repo_id}")
    if name == "RevisionNotFoundError" or "revision not found" in lowered:
        return RevisionNotFoundError(f"revision not found: {repo_id}")
    if name == "GatedRepoError" or "gated" in lowered:
        return GatedResourceError(f"gated repository (anonymous access): {repo_id}")
    if "429" in lowered or "rate limit" in lowered or name == "TooManyRequestsError":
        return RateLimitedError(f"rate limited by source: {repo_id}")
    if (
        "timeout" in lowered
        or "timed out" in lowered
        or name in ("TimeoutError", "ConnectTimeout", "ReadTimeout")
    ):
        return NetworkTimeoutError(f"network timeout from source: {repo_id}")
    if "401" in lowered or "403" in lowered or "unauthorized" in lowered or "forbidden" in lowered:
        return AuthenticationRequiredError(f"authentication required or forbidden: {repo_id}")
    if "offline" in lowered or "connection" in lowered or "unreachable" in lowered:
        return SourceUnavailableError(f"source unavailable: {repo_id}: {message[:200]}")
    return SourceUnavailableError(f"source unavailable: {repo_id}: {message[:200]}")


class HuggingFaceSourceClient:
    """عميل قراءة عامة مجهولة لبيانات Hugging Face الوصفية فقط."""

    def __init__(self, api: Any | None = None, *, timeout: float = DEFAULT_TIMEOUT) -> None:
        """حقن واجهة API لاختبار الحالات دون شبكة حقيقية."""
        if api is not None:
            self._api = api
        else:
            # الاستيراد المتأخر حتى تبقى الوحدة قابلة للاختبار دون تثبيت.
            from huggingface_hub import HfApi

            self._api = HfApi()
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("timeout must be a positive number")
        self._timeout = float(timeout)

    @property
    def timeout(self) -> float:
        """المهلة المطبقة على كل طلب شبكي."""
        return self._timeout

    def fetch(self, repo_id: str, *, revision: str = "main") -> RawModelMetadata:
        """جلب البيانات الوصفية العامة فقط بوصول مجهول صريح."""
        namespace, _ = validate_repo_id(repo_id)
        del namespace
        requested = revision.strip() or "main"
        retrieved_at = utc_now_iso()
        last_error: IntakeError | None = None
        for _ in range(MAX_ATTEMPTS):
            try:
                # الوصول المجهول الصريح: تعطيل الاعتماد المخزن على الجهاز.
                info = self._api.model_info(
                    repo_id,
                    revision=requested,
                    timeout=self._timeout,
                    files_metadata=True,
                    token=False,
                )
            except TypeError as exc:
                # نسخة مكتبة لا تدعم معاملًا متوقعًا: خطأ بيئي موثق.
                raise SourceUnavailableError(
                    f"incompatible huggingface_hub version: {exc}"
                ) from exc
            except Exception as exc:  # noqa: BLE001 - الترجمة المتعمدة لكل خطأ شبكي
                mapped = map_hub_exception(exc, repo_id)
                # إعادة المحاولة محدودة للأخطاء المؤقتة فقط دون حلقات مفتوحة.
                if (
                    mapped.status in ("network_timeout", "rate_limited", "source_unavailable")
                    and _ == 0
                ):
                    last_error = mapped
                    continue
                raise mapped from exc
            raw = build_raw_from_model_info(
                info,
                repo_id=repo_id,
                requested_revision=requested,
                retrieved_at=retrieved_at,
            )
            return raw
        raise last_error or SourceUnavailableError(f"source unavailable: {repo_id}")

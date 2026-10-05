"""نماذج الحدود الخام: فصل بيانات المصدر الخارجية عن سجلات أطلس."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RawArtifact:
    """ملف واحد مبلغ عنه من المصدر دون تنزيل محتواه."""

    filename: str
    path: str
    extension: str
    source_reported_size_bytes: int | None = None
    source_reported_storage: str | None = None
    source_reported_hash: str | None = None


@dataclass(frozen=True)
class RawModelMetadata:
    """لقطة بيانات وصفية خام من مصدر عام مع provenance الطلب."""

    platform: str
    repo_id: str
    namespace: str | None
    repo_name: str | None
    source_url: str
    requested_revision: str
    resolved_revision: str | None
    retrieved_at: str
    author: str | None = None
    tags: tuple[str, ...] = ()
    pipeline_tag: str | None = None
    library_name: str | None = None
    license_raw: str | list[str] | None = None
    base_models_raw: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    datasets_raw: tuple[str, ...] = ()
    architecture_raw: str | None = None
    architecture_type_raw: str | None = None
    total_parameters_b: float | None = None
    active_parameters_b: float | None = None
    experts_total: int | None = None
    experts_active: int | None = None
    context_advertised: int | None = None
    gated: bool = False
    private: bool = False
    disabled: bool = False
    downloads: int | None = None
    likes: int | None = None
    trending_score: float | None = None
    card_text: str | None = None
    siblings: tuple[RawArtifact, ...] = ()
    conflicts: tuple[str, ...] = ()
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class IntakeOutcome:
    """نتيجة خط أنابيب الاستقبال قبل الكتابة الدائمة."""

    model_record: dict
    source_records: tuple[dict, ...]
    evidence_records: tuple[dict, ...]
    intake_state: str
    warnings: tuple[str, ...] = ()

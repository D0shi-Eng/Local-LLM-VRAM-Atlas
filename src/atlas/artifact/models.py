"""نماذج الـartifacts: الملف والمجموعة والتحقق دون منطق تجميع."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ArtifactFile:
    """ملف واحد مبلغ عنه من المصدر مع حجمه المبلغ عنه فقط."""

    filename: str
    path: str
    extension: str
    source_reported_size_bytes: int | None = None


@dataclass(frozen=True)
class ArtifactSet:
    """مجموعة ملفات تشكل variant واحدًا من نموذج مكمم."""

    artifact_set_id: str
    model_id: str
    revision: str | None
    variant: str | None
    format: str
    kind: str
    files: tuple[ArtifactFile, ...] = ()
    shard_count: int = 1
    shard_total: int | None = None
    shards_complete: bool | None = None
    total_source_reported_bytes: int | None = None
    primary_weight_bytes: int | None = None
    auxiliary_bytes: int | None = None
    companion_components: tuple[str, ...] = ()
    verification_status: str = "unknown"
    warnings: tuple[str, ...] = field(default_factory=tuple)

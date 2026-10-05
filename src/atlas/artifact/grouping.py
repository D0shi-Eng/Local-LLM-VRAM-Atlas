"""تجميع الإخوة: الشظايا معًا والمتغيرات منفصلة والمرافق خارج الأوزان."""

from __future__ import annotations

import re

from atlas.artifact.companion import classify_auxiliary, is_main_weight_candidate
from atlas.artifact.models import ArtifactFile, ArtifactSet
from atlas.quant.detection import detect_from_filename

# نمط الشظايا مثل model-00001-of-00005 مع أي عدد أرقام.
_SHARD_PATTERN = re.compile(r"^(?P<stem>.*?)(?P<index>\d+)-of-(?P<total>\d+)(?P<tail>\..*)?$")


def _parse_shard(filename: str) -> tuple[str, int, int] | None:
    """استخراج الجذع ورقم الشظية والمجموع أو None عند غياب النمط."""
    match = _SHARD_PATTERN.search(filename)
    if not match:
        return None
    try:
        index = int(match.group("index"))
        total = int(match.group("total"))
    except ValueError:
        return None
    if total <= 0 or index < 0 or index > total:
        return None
    stem = (match.group("stem") or "").rstrip("-_.") + (match.group("tail") or "")
    return stem, index, total


def _variant_key(filename: str) -> tuple[str, str]:
    """مفتاح المتغير: المسار المحايد مع رمز الكم كجزء منفصل من المفتاح."""
    detection = detect_from_filename(filename.rsplit("/", 1)[-1])
    token = detection.get("quant_name") or ""
    stem = filename
    shard = _parse_shard(filename)
    if shard:
        stem = shard[0]
    if token:
        stem = re.sub(re.escape(token), "", stem, flags=re.IGNORECASE)
        stem = re.sub(re.escape(token.replace("_", "-")), "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"[-_.]{2,}", "-", stem).strip("-_.")
    return (stem.lower() or filename.lower()), token.upper()


def _expected_indices(members: list[tuple[str, int, int]]) -> list[int]:
    """الفهارس المتوقعة: تدعم الترقيم الصفري والواحدي دون تخمين."""
    indices = sorted(info[1] for info in members)
    total = members[0][2]
    if len(members) == 1 and total == 1:
        return indices
    if 0 in indices:
        return list(range(0, total + 1))
    return list(range(1, total + 1))


def _container_format(extension: str, filename: str) -> str:
    """اشتقاق صيغة الحاوية من اللاحقة دون خلطها بالتكميم."""
    lowered = (extension or "").lower()
    if lowered == ".gguf":
        return "GGUF"
    if lowered == ".safetensors":
        return "safetensors"
    if lowered in (".bin", ".pt", ".pth", ".ckpt", ".onnx"):
        return lowered.lstrip(".")
    if "mmproj" in filename.lower():
        return "GGUF"
    return "unknown"


def group_siblings(
    siblings: list[dict] | tuple,
    *,
    model_id: str = "unknown",
    revision: str | None = None,
) -> tuple[list[ArtifactSet], list[ArtifactFile], list[str]]:
    """تجميع الإخوة المبلغ عنهم إلى مجموعات variants مع فصل المرافق.

    تعيد المجموعات والملفات المساعدة والتحذيرات دون تنزيل أي محتوى.
    """
    warnings: list[str] = []
    weight_files: list[ArtifactFile] = []
    auxiliary_files: list[ArtifactFile] = []
    for item in siblings or []:
        if isinstance(item, dict):
            filename = str(item.get("filename") or item.get("path") or "")
            extension = str(item.get("extension") or "")
            size = item.get("source_reported_size_bytes")
        else:
            filename = str(getattr(item, "filename", "") or "")
            extension = str(getattr(item, "extension", "") or "")
            size = getattr(item, "source_reported_size_bytes", None)
        if not filename:
            continue
        record = ArtifactFile(
            filename=filename,
            path=filename,
            extension=extension.lower(),
            source_reported_size_bytes=size if isinstance(size, int) else None,
        )
        if is_main_weight_candidate(filename, extension):
            # ملف mmproj مرافق بصري لا وزن لغوي رئيسي.
            if classify_auxiliary(filename) == "projector":
                auxiliary_files.append(record)
            else:
                weight_files.append(record)
        else:
            auxiliary_files.append(record)

    # التجميع حسب الحاوية ثم الجذع ثم رمز الكم: متغيرات مختلفة لا تندمج أبدًا.
    buckets: dict[tuple[str, str, str], list[ArtifactFile]] = {}
    for record in weight_files:
        container = _container_format(record.extension, record.filename)
        stem_key, token = _variant_key(record.filename)
        buckets.setdefault((container, stem_key, token), []).append(record)

    artifact_sets: list[ArtifactSet] = []
    set_warnings: list[str] = []
    for (container, stem_key, token), members in sorted(buckets.items()):
        key = f"{stem_key}--{token.lower()}" if token else stem_key
        shard_info = [_parse_shard(member.filename) for member in members]
        shard_members = [info for info in shard_info if info is not None]
        if shard_members and len(shard_members) == len(members):
            totals = {info[2] for info in shard_members}
            indices = sorted(info[1] for info in shard_members)
            expected = shard_members[0][2]
            wanted = _expected_indices(shard_members)
            complete = len(totals) == 1 and indices == wanted
            if len(totals) > 1:
                set_warnings.append(
                    f"shard_total_mismatch: variant {key!r} reports totals {sorted(totals)}"
                )
            missing = sorted(set(wanted) - set(indices))
            if missing:
                set_warnings.append(f"missing_shard: variant {key!r} missing {missing}")
            duplicates = len(indices) != len(set(indices))
            if duplicates:
                set_warnings.append(f"duplicate_shard: variant {key!r} has repeated indices")
            kind = "sharded"
            shard_count = len(members)
            shard_total: int | None = expected
            shards_complete: bool | None = bool(complete and not duplicates)
        else:
            if shard_members:
                set_warnings.append(
                    f"mixed_shard_pattern: variant {key!r} mixes sharded and single files"
                )
            kind = "single"
            shard_count = len(members)
            shard_total = None
            shards_complete = None
        sizes = [
            member.source_reported_size_bytes
            for member in members
            if isinstance(member.source_reported_size_bytes, int)
        ]
        total_bytes = sum(sizes) if sizes and len(sizes) == len(members) else None
        if total_bytes is None:
            set_warnings.append(f"incomplete_sizes: variant {key!r} lacks reported sizes")
        first_detection = detect_from_filename(members[0].filename)
        variant = first_detection.get("quant_name")
        artifact_sets.append(
            ArtifactSet(
                artifact_set_id=f"{model_id}--{container.lower()}--{key or 'base'}",
                model_id=model_id,
                revision=revision,
                variant=variant,
                format=container,
                kind=kind,
                files=tuple(members),
                shard_count=shard_count,
                shard_total=shard_total,
                shards_complete=shards_complete,
                total_source_reported_bytes=total_bytes,
                primary_weight_bytes=total_bytes,
                auxiliary_bytes=None,
                companion_components=tuple(
                    sorted({classify_auxiliary(item.filename) for item in auxiliary_files})
                ),
                verification_status="source_reported",
                warnings=tuple(),
            )
        )
    if len(artifact_sets) > 1:
        warnings.append(
            "multi_variant_repository: each quant file is a separate variant, not shards"
        )
    warnings.extend(set_warnings)
    return artifact_sets, auxiliary_files, warnings

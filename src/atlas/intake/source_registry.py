"""سجل المصادر: هوية ومعنى لكل مصدر يعرفه الأطلس."""

from __future__ import annotations

import json
from pathlib import Path

from atlas.intake.url_safety import is_safe_url
from atlas.validation.validator import validate_record

# جذر المشروع محسوب من موقع الوحدة دون الاعتماد على مجلد العمل.
REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = REPO_ROOT / "catalog" / "sources" / "registry.json"


def load_registry(path: Path | None = None) -> dict:
    """تحميل سجل المصادر من القرص مع رسائل خطأ واضحة."""
    target = Path(path) if path is not None else REGISTRY_PATH
    if not target.is_file():
        raise FileNotFoundError(f"source registry not found: {target}")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in source registry: {exc}") from exc
    if not isinstance(data, dict) or "sources" not in data:
        raise ValueError("source registry must be an object with a 'sources' array")
    return data


def validate_registry(data: dict) -> list[str]:
    """التحقق من السجل: فرادة المعرفات وسلامة الروابط وتوافق المخطط."""
    errors: list[str] = []
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        return ["registry 'sources' must be a non-empty array"]
    seen: set[str] = set()
    for index, entry in enumerate(sources):
        where = f"sources[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{where}: must be an object")
            continue
        source_id = entry.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            errors.append(f"{where}: missing source_id")
        elif source_id in seen:
            errors.append(f"{where}: duplicate source_id '{source_id}'")
        else:
            seen.add(source_id)
        url = entry.get("url")
        if not isinstance(url, str) or not is_safe_url(url):
            errors.append(f"{where}: malformed or unsafe url {url!r}")
        if "authority_level" not in entry:
            errors.append(f"{where}: missing authority_level classification")
        record_errors = validate_record(entry, "source")
        errors.extend(f"{where}: {err.path}: {err.message}" for err in record_errors)
    return errors

"""التحقق الأساسي من السجلات مقابل مخططات JSON Schema.

تقتصر مسؤولية هذه الوحدة على التحقق فقط: تحميل السجل، واختيار المخطط
الصحيح، وإرجاع الأخطاء بصيغة مقروءة. لا تعدّل السجل أثناء التحقق أبدًا.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

# جذر المستودع محسوب من موقع هذه الوحدة، ولا يعتمد على مجلد العمل الحالي.
REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMAS_DIR = REPO_ROOT / "schemas"

SCHEMA_FILES = {
    "model": "model.schema.json",
    "evidence": "evidence.schema.json",
    "source": "source.schema.json",
    "runtime": "runtime.schema.json",
    "benchmark": "benchmark.schema.json",
    "quantization": "quantization.schema.json",
    "artifact": "artifact.schema.json",
    "memory-estimate": "memory-estimate.schema.json",
    "architecture": "architecture.schema.json",
    "measurement": "measurement.schema.json",
    "change-event": "change-event.schema.json",
    "refresh-plan": "refresh-plan.schema.json",
    "discovery-checkpoint": "discovery-checkpoint.schema.json",
    "evaluation-result": "evaluation-result.schema.json",
    "quality-profile": "quality-profile.schema.json",
    "quant-retention": "quant-retention.schema.json",
    "quality-policy": "quality-policy.schema.json",
    "recommendation-result": "recommendation-result.schema.json",
}

SUPPORTED_KINDS = tuple(SCHEMA_FILES)


@dataclass(frozen=True)
class ValidationError:
    """خطأ تحقق واحد بصيغة مفهومة للبشر."""

    path: str
    message: str


class ValidatorUsageError(Exception):
    """خطأ استخدام يمنع التحقق أصلًا (نوع مخطط مجهول أو ملف مفقود أو JSON مشوه)."""

    def __init__(self, path: str, message: str) -> None:
        """بناء الخطأ مع المسار والرسالة."""
        super().__init__(f"{path}: {message}")
        self.path = path
        self.message = message


def load_schema(kind: str) -> dict:
    """تحميل مخطط من النوع المطلوب، أو رفع خطأ عند النوع غير المدعوم."""
    if kind not in SCHEMA_FILES:
        supported = ", ".join(SUPPORTED_KINDS)
        raise ValidatorUsageError(
            path="$", message=f"unknown schema kind '{kind}'. Supported: {supported}"
        )
    schema_path = SCHEMAS_DIR / SCHEMA_FILES[kind]
    if not schema_path.is_file():
        raise ValidatorUsageError(path="$", message=f"schema file not found: {schema_path}")
    return json.loads(schema_path.read_text(encoding="utf-8"))


def load_record(record_path: str | Path) -> dict:
    """تحميل سجل JSON من القرص مع رسائل خطأ واضحة."""
    path = Path(record_path)
    if not path.is_file():
        raise ValidatorUsageError(path="$", message=f"record file not found: {path}")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidatorUsageError(path="$", message=f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(record, dict):
        raise ValidatorUsageError(path="$", message=f"record must be a JSON object: {path}")
    return record


def format_error(path: str, message: str) -> ValidationError:
    """بناء خطأ تحقق من مسار ورسالة."""
    return ValidationError(path=path or "$", message=message)


def validate_record(record: dict, kind: str) -> list[ValidationError]:
    """التحقق من نسخة عميقة للسجل حتى يبقى الأصل دون أي تعديل."""
    snapshot = copy.deepcopy(record)
    schema = load_schema(kind)
    # تفعيل مدقق الصيغ حتى تُرفض الطوابع الزمنية المشوهة فعليًا.
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    errors = [
        format_error("$." + ".".join(str(part) for part in error.absolute_path), error.message)
        for error in sorted(validator.iter_errors(snapshot), key=lambda e: list(e.absolute_path))
    ]
    if snapshot != record:
        errors.append(format_error("$", "internal error: record was modified during validation"))
    return errors


def validate_file(record_path: str | Path, kind: str) -> list[ValidationError]:
    """تحميل ملف سجل والتحقق منه مقابل المخطط المطلوب."""
    record = load_record(record_path)
    return validate_record(record, kind)

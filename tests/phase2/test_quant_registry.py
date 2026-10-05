"""اختبارات السجل النسخي للتكميم: العائلات والأسماء المستعارة والحالات."""

from atlas.quant.registry import (
    REGISTRY_VERSION,
    SUPPORTED_FAMILIES,
    find_entry,
    get_alias_target,
    list_entries,
    resolve_alias,
)
from atlas.validation.validator import validate_record


def _as_record(entry: dict) -> dict:
    """تحويل مدخل السجل إلى سجل قابل للتحقق مع حقول السجل."""
    record = dict(entry)
    record.setdefault("schema_version", "0.2.0")
    record.setdefault("registry_version", REGISTRY_VERSION)
    return record


def test_registry_version_is_documented():
    """نسخة السجل موثقة وليست حقيقة أبدية غير مؤرخة."""
    assert REGISTRY_VERSION == "0.2.0"
    assert len(list_entries()) > 20


def test_registry_covers_required_families():
    """العائلات المطلوبة ممثلة دون ادعاء تكافؤ."""
    for wanted in (
        "f32",
        "f16",
        "bf16",
        "fp8",
        "int8",
        "q8",
        "q6",
        "q5",
        "q4",
        "iq4",
        "q3",
        "iq3",
        "q2",
        "iq2",
        "iq1",
        "q1",
        "tq",
        "ternary",
        "mxfp4",
        "nvfp4",
        "awq",
        "gptq",
        "exl2",
        "mlx",
        "bitsandbytes",
        "other",
        "unknown",
    ):
        assert wanted in SUPPORTED_FAMILIES, f"missing family: {wanted}"
        assert list_entries(family=wanted), f"no entries for family: {wanted}"


def test_alias_does_not_duplicate_entry():
    """الاسم المستعار يُحل لنفس المدخل دون تكرار."""
    first = find_entry("Q4_K_M")
    second = find_entry("q4_k_m")
    assert first is not None and second is not None
    assert first["quantization_id"] == second["quantization_id"]
    assert resolve_alias("q4_k_m") == first["canonical_name"]
    assert get_alias_target("Q4_K_M") == first


def test_mxfp4_nvfp4_are_distinct():
    """MXFP4 وNVFP4 صيغتان مختلفتان لا مترادفان."""
    mxfp4 = find_entry("MXFP4")
    nvfp4 = find_entry("NVFP4")
    assert mxfp4 is not None and nvfp4 is not None
    assert mxfp4["quantization_id"] != nvfp4["quantization_id"]
    assert mxfp4["family"] != nvfp4["family"]


def test_container_is_not_quantization():
    """الحاوية منفصلة عن المنهجية (GGUF حاوية لا تكميم)."""
    entry = find_entry("Q4_K_M")
    assert entry is not None
    assert entry["container_format"] == "GGUF"
    assert entry["family"] == "q4"


def test_lifecycle_values_cover_deprecation():
    """حالات دورة الحياة تشمل القديم والنشط دون حذف التاريخ."""
    lifecycles = {e.get("lifecycle") for e in list_entries()}
    assert "active" in lifecycles
    assert "legacy" in lifecycles
    assert list_entries(lifecycle="legacy"), "legacy entries must stay queryable"


def test_registry_entries_validate_against_schema():
    """كل مدخل سجل صالح مقابل مخطط التكميم."""
    for entry in list_entries():
        errors = validate_record(_as_record(entry), "quantization")
        assert errors == [], f"{entry.get('quantization_id')}: {[e.message for e in errors]}"

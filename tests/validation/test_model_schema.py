"""اختبارات مخطط النموذج: الصالح يجتاز، وغير الصالح يفشل للسبب الصحيح."""

import copy

from conftest import load_fixture

from atlas.validation.validator import validate_record


def test_valid_model_passes():
    """السجل التركيبي الصالح يجب أن يجتاز مخطط النموذج دون أخطاء."""
    assert validate_record(load_fixture("fixture-valid-model.json"), "model") == []


def test_valid_verified_model_passes():
    """السجل الموثق بالأدلة يجب أن يجتاز عند توفر النسب المطلوب."""
    assert validate_record(load_fixture("fixture-valid-verified-model.json"), "model") == []


def test_missing_required_field_fails():
    """غياب حقل إلزامي (display_name) يجب أن يفشل التحقق."""
    errors = validate_record(
        load_fixture("fixture-invalid-model-missing-field.json", valid=False), "model"
    )
    assert errors, "expected validation errors for missing required field"
    assert any("display_name" in e.message for e in errors)


def test_invalid_enum_fails():
    """قيمة خارج التعداد (architecture_type) يجب أن تفشل."""
    errors = validate_record(load_fixture("fixture-invalid-model-enum.json", valid=False), "model")
    assert errors, "expected validation errors for invalid enum value"
    assert any("super-dense" in e.message for e in errors)


def test_invalid_vram_tier_fails():
    """مستوى VRAM خارج [4, 8, 12, 16] يجب أن يفشل."""
    errors = validate_record(
        load_fixture("fixture-invalid-model-vram-tier.json", valid=False), "model"
    )
    assert errors, "expected validation errors for invalid VRAM tier"


def test_measured_vram_requires_figures_and_conditions():
    """دليل القياس (measured) دون أرقام وظروف يجب أن يفشل."""
    record = load_fixture("fixture-valid-model.json")
    record["vram"] = {"vram_tier_gb": 8, "evidence": "measured"}
    errors = validate_record(record, "model")
    assert errors, "measured evidence without figures/conditions must fail"


def test_file_size_never_implies_fit():
    """المخطط لا يستنتج الملاءمة من حجم الملف: ملف صغير مع tier كبير مقبول بنيويًا."""
    record = load_fixture("fixture-valid-model.json")
    record["vram"] = {"weight_file_size_gib": 1.0, "vram_tier_gb": 16, "evidence": "unknown"}
    assert validate_record(record, "model") == []


def test_moe_requires_expert_counts():
    """نموذج MoE دون أعداد الخبراء يجب أن يفشل."""
    record = load_fixture("fixture-valid-model.json")
    modified = copy.deepcopy(record)
    modified["architecture_type"] = "moe"
    modified.pop("experts_total", None)
    modified.pop("experts_active", None)
    errors = validate_record(modified, "model")
    assert errors, "MoE without expert counts must fail"


def test_open_source_ai_requires_reference():
    """تصنيف open_source_ai دون مرجع المعيار يجب أن يفشل."""
    record = copy.deepcopy(load_fixture("fixture-valid-model.json"))
    record["openness"] = "open_source_ai"
    record.pop("open_source_ai_reference", None)
    errors = validate_record(record, "model")
    assert errors, "open_source_ai without definition reference must fail"

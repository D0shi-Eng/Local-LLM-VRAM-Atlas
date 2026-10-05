"""اختبارات نموذج الأدلة: لا توثيق دون نسب، ولا اختراع للمجهول."""

from conftest import load_fixture

from atlas.validation.validator import validate_record


def test_valid_evidence_passes():
    """سجل الدليل التركيبي الصالح يجب أن يجتاز."""
    assert validate_record(load_fixture("fixture-valid-evidence.json"), "evidence") == []


def test_verified_claim_without_provenance_fails():
    """ادعاء موثق دون evidence_ids يجب أن يفشل."""
    errors = validate_record(
        load_fixture("fixture-invalid-model-verified-without-evidence.json", valid=False),
        "model",
    )
    assert errors, "verified status without evidence_ids must fail"
    assert any("evidence_ids" in e.message for e in errors)


def test_unknown_data_needs_no_invented_value():
    """البيانات المجهولة تُمثَّل بـnull/unknown دون اختراع قيم."""
    record = load_fixture("fixture-valid-model.json")
    assert record["organization"] is None
    assert record["release_date"] is None
    assert record["license"]["license_id"] is None
    assert validate_record(record, "model") == []


def test_evidence_level_stays_distinct():
    """مستويات الدليل متميزة: ادعاء الناشر ليس قياسًا مستقلًا."""
    record = load_fixture("fixture-valid-evidence.json")
    assert record["evidence_level"] == "independent_measurement"
    record["evidence_level"] = "publisher_claim"
    assert validate_record(record, "evidence") == []
    record["evidence_level"] = "vendor_press_release"
    assert validate_record(record, "evidence"), "unknown evidence level must fail"

"""اختبارات مخطط بيئة التشغيل: التوافق مقيد بالإصدار والواجهة الخلفية."""

import copy

from conftest import load_fixture

from atlas.validation.validator import validate_record


def test_valid_runtime_passes():
    """سجل بيئة التشغيل الصالح يجب أن يجتاز."""
    assert validate_record(load_fixture("fixture-valid-runtime.json"), "runtime") == []


def test_unknown_support_status_fails():
    """حالة دعم خارج التعداد يجب أن تفشل."""
    errors = validate_record(
        load_fixture("fixture-invalid-runtime-status.json", valid=False), "runtime"
    )
    assert errors, "unknown support status must fail"


def test_official_status_requires_version_and_source():
    """الحالة الرسمية/الموثقة دون إصدار ومصدر يجب أن تفشل."""
    record = copy.deepcopy(load_fixture("fixture-valid-runtime.json"))
    record["support_status"] = "official"
    record.pop("runtime_version", None)
    record.pop("support_source", None)
    errors = validate_record(record, "runtime")
    assert errors, "official status without version and source must fail"


def test_runtime_name_is_mandatory():
    """لا يوجد توافق دون تسمية بيئة التشغيل صراحة."""
    record = copy.deepcopy(load_fixture("fixture-valid-runtime.json"))
    record.pop("runtime", None)
    errors = validate_record(record, "runtime")
    assert errors, "missing runtime name must fail"


def test_custom_fork_requires_url():
    """طلب fork مخصص دون رابطه يجب أن يفشل."""
    record = copy.deepcopy(load_fixture("fixture-valid-runtime.json"))
    record["requires_custom_fork"] = True
    record["fork_url"] = None
    errors = validate_record(record, "runtime")
    assert errors, "custom fork without URL must fail"

"""اختبارات مخططي المصدر والقياس: الروابط والمنشأ والإعدادات."""

import copy

from conftest import load_fixture

from atlas.validation.validator import validate_record


def test_valid_source_passes():
    """سجل المصدر الصالح يجب أن يجتاز."""
    assert validate_record(load_fixture("fixture-valid-source.json"), "source") == []


def test_malformed_source_url_fails():
    """الرابط المشوه يجب أن يفشل عند تطبيق قيد الصيغة."""
    errors = validate_record(load_fixture("fixture-invalid-source-url.json", valid=False), "source")
    assert errors, "malformed URL must fail"
    assert any("url" in e.path for e in errors)


def test_source_missing_required_fails():
    """غياب الناشر من المصدر يجب أن يفشل."""
    record = copy.deepcopy(load_fixture("fixture-valid-source.json"))
    record.pop("publisher", None)
    errors = validate_record(record, "source")
    assert errors, "missing publisher must fail"


def test_valid_benchmark_passes():
    """سجل القياس الصالح يجب أن يجتاز."""
    assert validate_record(load_fixture("fixture-valid-benchmark.json"), "benchmark") == []


def test_benchmark_origin_enum_is_closed():
    """منشأ القياس خارج التعداد الرباعي يجب أن يفشل."""
    record = copy.deepcopy(load_fixture("fixture-valid-benchmark.json"))
    record["benchmark_origin"] = "vendor_award"
    assert validate_record(record, "benchmark"), "unknown benchmark origin must fail"


def test_atlas_benchmark_requires_hardware_context():
    """قياس الأطلس دون سياق العتاد يجب أن يفشل."""
    record = copy.deepcopy(load_fixture("fixture-valid-benchmark.json"))
    record["benchmark_origin"] = "atlas"
    record["hardware"] = None
    assert validate_record(record, "benchmark"), "atlas benchmark without hardware must fail"


def test_publisher_and_independent_stay_separate():
    """منشآ الناشر والمستقل قيمتان متميزتان في التعداد."""
    record = load_fixture("fixture-valid-benchmark.json")
    assert record["benchmark_origin"] == "independent"
    record["benchmark_origin"] = "publisher"
    assert validate_record(record, "benchmark") == []

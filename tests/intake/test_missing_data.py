"""اختبارات سلامة البيانات المفقودة: المجهول يبقى مجهولًا."""

from support import FakeHfApi, minimal_info

from atlas.intake.hf_client import HuggingFaceSourceClient
from atlas.intake.pipeline import IntakePipeline
from atlas.validation.validator import validate_record


def _outcome(**overrides):
    """بناء نتيجة استقبال من معلومات فقيرة تركيبية."""
    client = HuggingFaceSourceClient(api=FakeHfApi(info=minimal_info(**overrides)))
    return IntakePipeline(client).build("org/empty-model")


def test_missing_parameter_count_remains_unknown():
    """غياب عدد المعاملات يبقى null ولا يتحول إلى صفر."""
    outcome = _outcome()
    assert outcome.model_record["total_parameters_b"] is None
    assert outcome.model_record["total_parameters_b"] != 0
    assert validate_record(outcome.model_record, "model") == []


def test_missing_license_remains_unknown_with_pending_state():
    """غياب الترخيص يبقى unknown مع حالة انتظار صريحة."""
    outcome = _outcome()
    license_block = outcome.model_record["license"]
    assert license_block["license_id"] is None
    assert license_block["verification_status"] == "unknown"
    assert outcome.model_record["openness"] == "unclear"
    assert outcome.intake_state == "pending_license"


def test_missing_base_model_remains_unknown():
    """غياب النموذج الأساس يبقى فارغًا دون اختراع نسب."""
    outcome = _outcome()
    assert outcome.model_record["base_models"] == []


def test_null_never_becomes_zero_or_false():
    """القيم الفارغة لا تتحول إلى أصفار أو ادعاءات زائفة."""
    outcome = _outcome()
    record = outcome.model_record
    assert record["total_parameters_b"] is None
    assert record["active_parameters_b"] is None
    assert record["experts_total"] is None
    assert record["context_length"]["advertised_max"] is None
    assert "vram" not in record


def test_model_name_alone_never_sets_parameter_count():
    """اسم المستودع وحده لا يحدد عدد المعاملات أبدًا."""
    client = HuggingFaceSourceClient(api=FakeHfApi(info=minimal_info()))
    outcome = IntakePipeline(client).build("someone/SomeModel-27B-Q4")
    assert outcome.model_record["total_parameters_b"] is None

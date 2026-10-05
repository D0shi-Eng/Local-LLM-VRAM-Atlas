"""اختبارات الترخيص: SPDX معتمد والمخصص لا يُجبر والمتساهل لا يعني open_source_ai."""

from support import FakeHfApi, make_info

from atlas.intake.hf_client import HuggingFaceSourceClient
from atlas.intake.licenses import resolve_license
from atlas.intake.pipeline import IntakePipeline


def test_recognized_spdx_id_normalized_correctly():
    """معرف SPDX المعروف يطبع بصيغته المعيارية الصغرى."""
    resolved = resolve_license("Apache 2.0", license_source="model_card_metadata")
    assert resolved.normalized_id == "apache-2.0"
    assert resolved.is_spdx is True
    assert resolved.verification_status == "publisher_claim"


def test_custom_license_is_not_force_mapped():
    """الترخيص المخصص يبقى بهويته ولا يُجبر على MIT أو Apache."""
    resolved = resolve_license("gemma", license_source="model_card_metadata")
    assert resolved.is_spdx is False
    assert resolved.normalized_id == "gemma"
    assert resolved.openness == "unclear"


def test_permissive_weight_license_never_creates_open_source_ai():
    """رخصة الأوزان المتساهلة لا تنشئ تصنيف open_source_ai تلقائيًا."""
    resolved = resolve_license("apache-2.0", license_source="model_card_metadata")
    assert resolved.openness == "open_weights_permissive"
    assert resolved.openness != "open_source_ai"


def test_multiple_licenses_record_conflict_without_silent_choice():
    """القيم المتعددة تسجل كتضارب مع حالة غير متحقق منها."""
    resolved = resolve_license(["apache-2.0", "mit"], license_source="model_card_metadata")
    assert resolved.verification_status == "unverified"
    assert resolved.openness == "unclear"


def test_end_to_end_license_flows_into_record():
    """قيمة البطاقة الخام تصل إلى السجل المعياري مع provenance."""
    info = make_info(card_data={"license": "mit"}, tags=["license:mit"])
    outcome = IntakePipeline(HuggingFaceSourceClient(api=FakeHfApi(info=info))).build("org/m")
    assert outcome.model_record["license"]["license_id"] == "mit"
    assert outcome.model_record["openness"] == "open_weights_permissive"

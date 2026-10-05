"""اختبارات محول المصدر: تطبيع عام مجهول بدلائل فشل مميزة."""

import pytest
from support import FakeHfApi, make_info, minimal_info

from atlas.intake.errors import (
    AuthenticationRequiredError,
    GatedResourceError,
    NetworkTimeoutError,
    NotFoundError,
)
from atlas.intake.errors import (
    RevisionNotFoundError as IntakeRevisionNotFound,
)
from atlas.intake.hf_client import HuggingFaceSourceClient


def _hub_error(name: str, message: str) -> Exception:
    """بناء خطأ يحمل اسم صنف المكتبة الرسمية دون الحاجة لبنية الاستجابة."""
    return type(name, (Exception,), {})(message)


def test_public_model_metadata_normalized_to_raw_dto():
    """البيانات العامة تتحول إلى DTO خام مستقل عن SDK."""
    client = HuggingFaceSourceClient(api=FakeHfApi(info=make_info()))
    raw = client.fetch("fixture-org/fixture-model")
    assert raw.platform == "hugging-face"
    assert raw.repo_id == "fixture-org/fixture-model"
    assert raw.namespace == "fixture-org"
    assert raw.requested_revision == "main"
    assert raw.resolved_revision == "a" * 40
    assert raw.source_url == "https://huggingface.co/fixture-org/fixture-model"
    assert raw.retrieved_at.endswith("Z")
    assert any(a.extension == ".gguf" for a in raw.siblings)


def test_anonymous_access_token_explicitly_disabled():
    """كل طلب يمرر token=False صراحة دون الاعتماد على المخزن المحلي."""
    fake = FakeHfApi(info=make_info())
    HuggingFaceSourceClient(api=fake).fetch("fixture-org/fixture-model")
    assert fake.calls, "expected exactly one metadata call"
    assert fake.calls[0]["token"] is False


def test_every_call_carries_bounded_timeout():
    """كل طلب شبكي يحمل مهلة محدودة قابلة للضبط."""
    fake = FakeHfApi(info=make_info())
    HuggingFaceSourceClient(api=fake, timeout=7.5).fetch("org/model")
    assert fake.calls[0]["timeout"] == 7.5


def test_not_found_maps_to_not_found_status():
    """المستودع المفقود يبقى not_found ولا يتحول إلى خطأ شبكي عام."""
    fake = FakeHfApi(error=_hub_error("RepositoryNotFoundError", "Repository Not Found"))
    with pytest.raises(NotFoundError) as exc:
        HuggingFaceSourceClient(api=fake).fetch("ghost-org/ghost-model")
    assert exc.value.status == "not_found"


def test_revision_not_found_maps_distinctly():
    """المراجعة المفقودة حالة مميزة عن المستودع المفقود."""
    fake = FakeHfApi(error=_hub_error("RevisionNotFoundError", "Revision Not Found"))
    with pytest.raises(IntakeRevisionNotFound) as exc:
        HuggingFaceSourceClient(api=fake).fetch("org/model", revision="nope")
    assert exc.value.status == "not_found"


def test_gated_response_maps_to_gated_status():
    """المورد المقيد يصنف gated ولا يحاول تجاوزه بالاعتماد."""
    fake = FakeHfApi(error=_hub_error("GatedRepoError", "Gated repo"))
    with pytest.raises(GatedResourceError) as exc:
        HuggingFaceSourceClient(api=fake).fetch("org/gated-model")
    assert exc.value.status == "gated"


def test_private_repository_maps_to_authentication_required():
    """المستودع الخاص يصنف authentication_required دون قراءة أي توكن."""
    fake = FakeHfApi(
        error=_hub_error("RepositoryNotFoundError", "Private repository (401 Unauthorized)")
    )
    with pytest.raises(AuthenticationRequiredError):
        HuggingFaceSourceClient(api=fake).fetch("org/private-model")


def test_timeout_maps_to_network_timeout_status():
    """مهلة الشبكة لا تتحول أبدًا إلى model_not_found."""
    fake = FakeHfApi(error=TimeoutError("timed out"))
    with pytest.raises(NetworkTimeoutError) as exc:
        HuggingFaceSourceClient(api=fake).fetch("org/model")
    assert exc.value.status == "network_timeout"


def test_client_exposes_no_write_or_download_methods():
    """المحول قراءة فقط: لا تنزيل لقطات ولا نسخ ولا تحميل أوزان."""
    forbidden = (
        "snapshot_download",
        "hf_hub_download",
        "snapshot_upload",
        "upload_file",
        "create_commit",
        "create_repo",
        "from_pretrained",
        "login",
    )
    for name in forbidden:
        assert not hasattr(HuggingFaceSourceClient, name), (
            f"write/download surface forbidden: {name}"
        )


def test_minimal_metadata_yields_unknowns_not_guesses():
    """البيانات الفقيرة تنتج null وunknown دون اختراع قيم."""
    client = HuggingFaceSourceClient(api=FakeHfApi(info=minimal_info()))
    raw = client.fetch("org/empty-model")
    assert raw.license_raw is None
    assert raw.base_models_raw == ()
    assert raw.architecture_raw is None
    assert raw.total_parameters_b is None
    assert raw.context_advertised is None

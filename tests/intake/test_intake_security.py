"""اختبارات أمن الشبكة: لا جلب تلقائي ولا عناوين محلية ولا أسرار."""

from pathlib import Path

from atlas.intake.errors import UnsafeUrlError
from atlas.intake.url_safety import assert_safe_url, is_safe_url

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_error_status_taxonomy():
    """خطأ العنوان غير الآمن يحمل حالة الحظر الموثقة."""
    try:
        raise UnsafeUrlError("probe")
    except UnsafeUrlError as exc:
        assert exc.status == "blocked"


def test_public_https_url_allowed():
    """عنوان HTTPS العام مسموح للمراجع الصريحة فقط."""
    assert is_safe_url("https://huggingface.co/org/model") is True


def test_localhost_and_loopback_rejected():
    """عناوين الحلقة الراجعة مرفوضة ولا يمكن أن يفرضها model card."""
    for url in (
        "http://localhost/org/model",
        "http://127.0.0.1/org/model",
        "http://[::1]/org/model",
        "http://2130706433/org/model",
    ):
        assert is_safe_url(url) is False, url


def test_private_and_link_local_rejected():
    """النطاقات الخاصة والمحلية وخدمات البيانات السحابية مرفوضة."""
    for url in (
        "http://10.0.0.5/model",
        "http://192.168.1.10/model",
        "http://172.16.4.2/model",
        "http://169.254.169.254/latest/meta-data/",
        "http://metadata.google.internal/model",
    ):
        assert is_safe_url(url) is False, url


def test_non_http_schemes_rejected():
    """بروتوكولات الملفات والتحويل ومسارات UNC مرفوضة."""
    for url in (
        "file:///C:/Windows/win.ini",
        "file://server/share/model.gguf",
        "ftp://example.com/model.gguf",
        "\\\\server\\share\\model.gguf",
        "C:\\models\\model.gguf",
    ):
        assert is_safe_url(url) is False, url


def test_embedded_credentials_rejected():
    """العناوين ذات بيانات الاعتماد المضمنة مرفوضة."""
    assert is_safe_url("https://user:pass@huggingface.co/org/model") is False


def test_assert_safe_url_raises_domain_error():
    """الدالة الحارسة ترفع خطأ نطاق بدل إرجاع قيمة مضللة."""
    try:
        assert_safe_url("http://127.0.0.1/evil")
    except UnsafeUrlError as exc:
        assert exc.status == "blocked"
    else:
        raise AssertionError("expected UnsafeUrlError for loopback url")


def test_no_token_read_or_persisted_in_client_source():
    """شيفرة العميل لا تقرأ توكن ولا تطبعه ولا تحفظه."""
    source = (REPO_ROOT / "src" / "atlas" / "intake" / "hf_client.py").read_text(encoding="utf-8")
    for forbidden in (
        "HF_TOKEN",
        "os.environ",
        "getpass",
        "keyring",
        "credential",
        "Authorization",
    ):
        assert forbidden not in source, f"secret-adjacent pattern forbidden in client: {forbidden}"
    assert "token=False" in source


def test_no_remote_code_execution_patterns_in_intake():
    """حزمة الاستقبال لا تنفذ كودًا عن بُعد ولا تحمل Pickle."""
    import re

    offenders = []
    for path in (REPO_ROOT / "src" / "atlas" / "intake").rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        for pattern in (
            r"trust_remote_code\s*=\s*True",
            r"pickle\.loads?\s*\(",
            r"torch\.load\s*\(",
            r"from_pretrained\s*\(",
        ):
            if re.search(pattern, content):
                offenders.append(f"{path}: {pattern}")
    assert offenders == []


def test_model_card_links_are_recorded_not_fetched():
    """روابط البطاقة تسجل كمراجع ولا يجلبها خط الأنابيب تلقائيًا."""
    import inspect

    import atlas.intake.hf_client as client_module
    import atlas.intake.pipeline as pipeline_module

    combined = inspect.getsource(client_module) + inspect.getsource(pipeline_module)
    assert "urlopen" not in combined
    assert "requests.get" not in combined

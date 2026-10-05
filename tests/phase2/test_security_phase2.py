"""اختبارات أمن المرحلة الثانية: SSRF والallowlist وغياب الأوزان والأسرار."""

import re
from pathlib import Path

from atlas.intake.url_safety import is_safe_url
from atlas.security.metadata_fetch import MAX_METADATA_BYTES, MetadataBudget, allowed_metadata_url

REPO_ROOT = Path(__file__).resolve().parents[2]

# امتدادات الأوزان الكاملة الممنوعة من التنزيل.
_WEIGHT_SUFFIXES = (".gguf", ".safetensors", ".bin", ".pt", ".pth", ".ckpt", ".onnx")
# أنماط تشبه الأسرار (مفاتيح وتوكنز) للفحص الاستباقي.
_SECRET_PATTERNS = (
    re.compile(r"hf_[A-Za-z0-9]{10,}"),
    re.compile(r"ghp_[A-Za-z0-9]{10,}"),
    re.compile(r"sk-ant-[A-Za-z0-9-]{10,}"),
    re.compile(r"xox[bap]-", re.IGNORECASE),
)


def test_numeric_ip_ssrf_still_blocked():
    """الانحدار الأمني: 2130706433 (127.0.0.1) وأشكالها المموهة محظورة."""
    assert is_safe_url("http://2130706433/") is False
    assert is_safe_url("http://0x7f000001/") is False
    assert is_safe_url("http://0177.0.0.01/") is False
    assert is_safe_url("http://127.0.0.1/") is False
    assert is_safe_url("http://[::1]/") is False


def test_metadata_allowlist_rejects_weights():
    """allowlist البيانات الوصفية ترفض ملفات الأوزان."""
    assert allowed_metadata_url("https://huggingface.co/org/model/resolve/main/model.gguf") is False
    assert (
        allowed_metadata_url("https://huggingface.co/org/model/resolve/main/model.safetensors")
        is False
    )


def test_metadata_allowlist_accepts_config_only():
    """config/index الصغير مسموح من المضيف الموثوق فقط."""
    assert allowed_metadata_url("https://huggingface.co/org/model/resolve/main/config.json") is True
    assert allowed_metadata_url("https://evil.example/config.json") is False


def test_metadata_budget_is_bounded():
    """ميزانية الطلبات التراكمية تمنع الزحف."""
    budget = MetadataBudget(limit=2)
    budget.consume()
    budget.consume()
    try:
        budget.consume()
    except Exception as exc:
        assert "budget exhausted" in str(exc)
    else:
        raise AssertionError("budget must refuse the third request")
    assert MAX_METADATA_BYTES <= 256 * 1024


def test_no_weight_artifacts_in_repo():
    """تدقيق الأوزان: صفر ملفات أوزان في المشروع."""
    hits = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        lowered = path.name.lower()
        if lowered.endswith(_WEIGHT_SUFFIXES) and path.stat().st_size > 1024 * 1024:
            hits.append(str(path))
    assert hits == [], f"weight artifacts found: {hits[:5]}"


def test_no_secrets_in_repo():
    """تدقيق الأسرار: لا توكنز ولا .env ولا اعتماد."""
    hits = []
    skip_dirs = {".git", "__pycache__", ".pytest_cache", ".ruff_cache"}
    # تركيبة المرحلة صفر المقصودة لاختبار كشف الأسرار (موثقة في تقريرها).
    allowlisted = {"tests/fixtures/invalid/fixture-secret-like.txt"}
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or any(part in skip_dirs for part in path.parts):
            continue
        try:
            relative = path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            continue
        if relative in allowlisted:
            continue
        if path.suffix.lower() in (".pyc", ".pyo"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        if path.name == ".env" or path.suffix == ".pem":
            hits.append(str(path))
            continue
        for pattern in _SECRET_PATTERNS:
            if pattern.search(text):
                hits.append(f"{path}:{pattern.pattern[:12]}")
                break
    assert hits == [], f"possible secrets: {hits[:5]}"


def test_no_remote_code_execution_markers():
    """لا تنفيذ شيفرة عن بُعد، ولا أتمتة مستمرة دون موافقة المالك."""
    dangerous = ("trust_remote_code", "pickle.load", "torch.load")
    hits = []
    for path in (REPO_ROOT / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in dangerous:
            if token in text:
                hits.append(f"{path.name}:{token}")
    assert hits == [], f"remote code execution markers in source: {hits}"
    assert not (REPO_ROOT / ".github" / "workflows").exists(), (
        "no continuous integration workflow is published without owner approval"
    )

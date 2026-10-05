"""اختبارات الأمن: لا أوزان نماذج، ولا أسرار خارج بيانات الاختبار."""

import re
from pathlib import Path

from conftest import FIXTURES_DIR, REPO_ROOT

WEIGHT_EXTENSIONS = {".gguf", ".safetensors", ".ckpt", ".pth", ".pt", ".bin", ".onnx"}

SECRET_PATTERNS = [
    re.compile(r"hf_[A-Za-z0-9]{10,}"),
    re.compile(r"sk-[A-Za-z0-9]{8,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{8,}"),
    re.compile(r"xox[bpas]-[A-Za-z0-9-]+"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]

ALLOWLISTED_SECRET_FIXTURE = FIXTURES_DIR / "invalid" / "fixture-secret-like.txt"

TEXT_SUFFIXES = {
    ".py",
    ".json",
    ".md",
    ".toml",
    ".txt",
    ".example",
    ".cfg",
    ".ini",
    ".yaml",
    ".yml",
}

DANGEROUS_CODE_PATTERNS = [
    re.compile(r"trust_remote_code\s*=\s*True"),
    re.compile(r"pickle\.loads?\s*\("),
]


def _all_files() -> list[Path]:
    """جميع الملفات تحت جذر المستودع."""
    return [p for p in REPO_ROOT.rglob("*") if p.is_file()]


def test_no_model_weight_files_in_tree():
    """يُمنع وجود ملفات أوزان النماذج داخل شجرة المشروع."""
    offenders = [str(p) for p in _all_files() if p.suffix.lower() in WEIGHT_EXTENSIONS]
    assert offenders == [], f"model weight files forbidden in repo: {offenders}"


def test_allowlisted_secret_fixture_exists():
    """بيانات الاختبار الشبيهة بالأسرار موجودة في مكانها المسموح فقط."""
    assert ALLOWLISTED_SECRET_FIXTURE.is_file()
    content = ALLOWLISTED_SECRET_FIXTURE.read_text(encoding="utf-8")
    assert SECRET_PATTERNS[0].search(content), "fixture must match a secret pattern"


def test_no_secrets_outside_fixtures():
    """لا أنماط أسرار خارج مجلد بيانات الاختبار المسموح."""
    offenders = []
    for path in _all_files():
        if FIXTURES_DIR in path.parents or path == ALLOWLISTED_SECRET_FIXTURE:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                offenders.append(f"{path}: {pattern.pattern}")
    assert offenders == [], f"secret-like content outside tests/fixtures: {offenders}"


def test_no_dotenv_with_secrets():
    """لا ملف .env داخل المشروع في المرحلة صفر."""
    env_files = [str(p) for p in _all_files() if p.name == ".env"]
    assert env_files == [], f".env files forbidden in Phase 0: {env_files}"


def test_no_dangerous_execution_patterns_in_src():
    """شيفرة المشروع لا تنفذ كودًا عن بُعد ولا تحمّل Pickle."""
    offenders = []
    for path in (REPO_ROOT / "src").rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        for pattern in DANGEROUS_CODE_PATTERNS:
            if pattern.search(content):
                offenders.append(f"{path}: {pattern.pattern}")
    assert offenders == [], f"dangerous patterns in src: {offenders}"

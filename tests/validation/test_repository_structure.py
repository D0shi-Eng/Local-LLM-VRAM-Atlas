"""اختبارات بنية المستودع: المجلدات والمخططات وسلوك أداة التحقق."""

import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import INVALID_DIR, REPO_ROOT, SRC_DIR, VALID_DIR

REQUIRED_DIRS = [
    "catalog/models",
    "catalog/sources",
    "catalog/runtimes",
    "catalog/benchmarks",
    "schemas",
    "src/atlas/validation",
    "tests/fixtures/valid",
    "tests/fixtures/invalid",
    "tests/validation",
    "docs/en/architecture",
    "docs/en/catalog",
    "docs/en/governance",
    "docs/en/methodology",
    "docs/en/terminology",
    "docs/en/workflows",
    "docs/ar/architecture",
    "docs/ar/catalog",
    "docs/ar/governance",
    "docs/ar/methodology",
    "docs/ar/terminology",
    "docs/ar/workflows",
    "docs/diagrams",
    "assets/branding",
]

# Root files that define the published repository surface.
REQUIRED_ROOT_FILES = [
    "README.md",
    "README_AR.md",
    "CHANGELOG.md",
    "LICENSE",
    "NOTICE",
    "pyproject.toml",
    ".gitignore",
]

# Internal engineering history and machine-local state that must never be
# published. Absence is part of the repository contract.
FORBIDDEN_PATHS = [
    "docs/phases",
    "catalog/refresh",
    "catalog/checkpoints",
    "catalog/changes",
    "catalog/release-candidate-data-manifest.json",
    "catalog/closure/external/bonsai-existing-server.json",
]

REQUIRED_SCHEMAS = [
    "model.schema.json",
    "evidence.schema.json",
    "source.schema.json",
    "runtime.schema.json",
    "benchmark.schema.json",
]

DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"


def test_required_directories_exist():
    """البنية الأساسية للمستودع موجودة ونظيفة."""
    missing = [d for d in REQUIRED_DIRS if not (REPO_ROOT / d).is_dir()]
    assert missing == [], f"missing directories: {missing}"


def test_required_files_exist():
    """Root files defining the published surface are present."""
    for relative in REQUIRED_ROOT_FILES:
        assert (REPO_ROOT / relative).is_file(), f"missing required file: {relative}"


def test_license_is_apache_2_0():
    """The project licence is Apache-2.0 and metadata agrees."""
    license_text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "Apache License" in license_text
    assert "Version 2.0, January 2004" in license_text
    assert "END OF TERMS AND CONDITIONS" in license_text

    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'license = "Apache-2.0"' in pyproject
    assert "PENDING" not in pyproject.upper()

    for readme in ("README.md", "README_AR.md"):
        text = (REPO_ROOT / readme).read_text(encoding="utf-8")
        assert "Apache" in text, f"{readme} must state the licence"


def test_internal_history_is_not_version_controlled():
    """Build-phase history and machine-local state are excluded from git.

    These paths may exist in a local working tree; what the repository contract
    forbids is committing them. When git metadata is present, the check is
    exact; otherwise the ``.gitignore`` declaration is the enforceable contract.
    """
    import subprocess

    git_dir = REPO_ROOT / ".git"
    if not git_dir.is_dir():
        return

    tracked = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch", *FORBIDDEN_PATHS],
        capture_output=True,
        text=True,
    )
    assert tracked.returncode != 0, (
        "internal-only paths must not be tracked by git: "
        f"{sorted(FORBIDDEN_PATHS)}"
    )


def test_internal_paths_are_gitignored():
    """Excluded paths are also declared in .gitignore."""
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    excluded = (
        "docs/phases/",
        "catalog/refresh/",
        "catalog/checkpoints/",
        "catalog/changes/",
    )
    for relative in excluded:
        assert relative in gitignore, f".gitignore must exclude {relative}"


def test_no_continuous_integration_or_pages():
    """No CI workflow and no published site in the curated repository."""
    assert not (REPO_ROOT / ".github" / "workflows").exists(), (
        "no CI workflow is published without explicit owner approval"
    )
    assert not (REPO_ROOT / "CNAME").exists(), "no custom domain for a site that is not published"


def test_no_model_weights_in_tree():
    """Atlas is metadata-only: no weight payload may enter the repository."""
    forbidden_suffixes = (".gguf", ".ggml", ".safetensors", ".bin", ".pt", ".onnx")
    offenders = [
        p.relative_to(REPO_ROOT).as_posix()
        for p in REPO_ROOT.rglob("*")
        if p.is_file()
        and not any(part in {".git", ".venv", "__pycache__"} for part in p.parts)
        and p.suffix.lower() in forbidden_suffixes
    ]
    assert offenders == [], f"weight payloads must never be committed: {offenders}"


def test_branding_assets_exist_and_are_valid_svg():
    """The visual identity exists and every asset parses as SVG."""
    import xml.etree.ElementTree as ET

    required = [
        "assets/branding/icon.svg",
        "assets/branding/icon-dark.svg",
        "assets/branding/banner.svg",
        "assets/branding/brand-guidelines.md",
        "assets/branding/brand-guidelines_AR.md",
    ]
    for relative in required:
        path = REPO_ROOT / relative
        assert path.is_file(), f"missing branding asset: {relative}"
        if relative.endswith(".svg"):
            root = ET.parse(path).getroot()
            assert root.tag.endswith("svg"), f"{relative} is not an SVG document"
            assert root.get("viewBox"), f"{relative} must declare a viewBox"


def test_schemas_are_valid_draft_2020_12():
    """كل مخطط JSON صالح ويحمل البيانات الوصفية المطلوبة."""
    for name in REQUIRED_SCHEMAS:
        path = REPO_ROOT / "schemas" / name
        assert path.is_file(), f"missing schema: {name}"
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema.get("$schema") == DRAFT_2020_12, f"{name} must declare Draft 2020-12"
        for key in ("$id", "title", "description", "type"):
            assert schema.get(key), f"{name} missing metadata key: {key}"


def test_no_embedded_build_phase_chronology():
    """No document links to an internal build-phase report.

    Naming the excluded directory at directory level is allowed, because the
    published documentation states what is deliberately withheld. Linking to a
    specific internal phase report is not.
    """
    import re

    marker = re.compile(r"docs/phases/phase-\d", re.IGNORECASE)
    offenders = []
    for path in sorted(REPO_ROOT.rglob("*.md")):
        parts = set(path.parts)
        if parts & {".git", ".venv", "__pycache__", "phases"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if marker.search(text):
            offenders.append(path.relative_to(REPO_ROOT).as_posix())
    assert offenders == [], f"documents must not reference internal build phases: {offenders}"


def _run_cli(schema: str, record: Path) -> subprocess.CompletedProcess:
    """تشغيل أداة التحقق كعملية فرعية لاختبار رموز الخروج."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "atlas.validation.cli", "--schema", schema, "--record", str(record)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
        timeout=60,
    )


def test_cli_exit_zero_on_valid():
    """السجل الصالح يعطي رمز خروج صفريًا."""
    result = _run_cli("model", VALID_DIR / "fixture-valid-model.json")
    assert result.returncode == 0, f"stdout={result.stdout} stderr={result.stderr}"
    assert "valid" in result.stdout


def test_cli_exit_nonzero_on_invalid():
    """السجل غير الصالح يعطي رمز خروج غير صفري مع رسالة مفهومة."""
    result = _run_cli("model", INVALID_DIR / "fixture-invalid-model-enum.json")
    assert result.returncode == 1, f"stdout={result.stdout} stderr={result.stderr}"
    assert "FAIL" in result.stdout


def test_cli_exit_usage_error_on_missing_file():
    """الملف المفقود خطأ استخدام برمز 2 لا بصمة نجاح."""
    result = _run_cli("model", INVALID_DIR / "does-not-exist.json")
    assert result.returncode == 2, f"stdout={result.stdout} stderr={result.stderr}"

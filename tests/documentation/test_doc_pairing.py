"""اختبارات الثنائية اللغوية: كل وثيقة أساسية لها مقابل دلالي."""

import re

from conftest import REPO_ROOT

ARABIC_SCRIPT = re.compile(r"[\u0600-\u06FF]")

REQUIRED_DOC_PAIRS = [
    (
        "docs/en/architecture/repository-architecture.md",
        "docs/ar/architecture/repository-architecture.md",
    ),
    ("docs/en/architecture/data-flow.md", "docs/ar/architecture/data-flow.md"),
    ("docs/en/governance/evidence-policy.md", "docs/ar/governance/evidence-policy.md"),
    ("docs/en/governance/licensing-policy.md", "docs/ar/governance/licensing-policy.md"),
    ("docs/en/governance/security-policy.md", "docs/ar/governance/security-policy.md"),
    (
        "docs/en/governance/contribution-policy.md",
        "docs/ar/governance/contribution-policy.md",
    ),
    ("docs/en/methodology/vram-methodology.md", "docs/ar/methodology/vram-methodology.md"),
    (
        "docs/en/methodology/quantization-methodology.md",
        "docs/ar/methodology/quantization-methodology.md",
    ),
    (
        "docs/en/methodology/benchmark-methodology.md",
        "docs/ar/methodology/benchmark-methodology.md",
    ),
    (
        "docs/en/methodology/ranking-methodology.md",
        "docs/ar/methodology/ranking-methodology.md",
    ),
    (
        "docs/en/methodology/provenance-methodology.md",
        "docs/ar/methodology/provenance-methodology.md",
    ),
    (
        "docs/en/methodology/uncensored-classification.md",
        "docs/ar/methodology/uncensored-classification.md",
    ),
    ("docs/en/terminology/glossary.md", "docs/ar/terminology/glossary.md"),
]

REQUIRED_README_PAIR = ("README.md", "README_AR.md")
REQUIRED_CATALOG_PAIR = ("catalog/README.md", "catalog/README_AR.md")


def _read(relative: str) -> str:
    path = REPO_ROOT / relative
    assert path.is_file(), f"missing required file: {relative}"
    content = path.read_text(encoding="utf-8")
    assert content.strip(), f"required file is empty: {relative}"
    return content


def test_readme_pair_exists_with_language_switch():
    """README الإنجليزي والعربي موجودان ويحيل كل منهما إلى الآخر."""
    en = _read(REQUIRED_README_PAIR[0])
    ar = _read(REQUIRED_README_PAIR[1])
    assert "README_AR.md" in en, "English README must link to the Arabic README"
    assert "README.md" in ar, "Arabic README must link to the English README"
    assert ARABIC_SCRIPT.search(ar), "Arabic README must contain Arabic script"


def test_catalog_readme_pair_exists():
    """README الفهرس بنسختيه موجود ومحتواه غير فارغ."""
    _read(REQUIRED_CATALOG_PAIR[0])
    ar = _read(REQUIRED_CATALOG_PAIR[1])
    assert ARABIC_SCRIPT.search(ar), "Arabic catalog README must contain Arabic script"


def test_every_english_doc_has_arabic_counterpart():
    """كل وثيقة إنجليزية أساسية لها مقابل عربي دلالي."""
    missing = [ar for en, ar in REQUIRED_DOC_PAIRS if not (REPO_ROOT / ar).is_file()]
    assert missing == [], f"missing Arabic counterparts: {missing}"
    for en, ar in REQUIRED_DOC_PAIRS:
        _read(en)
        _read(ar)


def test_arabic_docs_contain_arabic_script():
    """الوثائق العربية يجب أن تحوي نصًا عربيًا فعليًا لا عناوين إنجليزية فقط."""
    for _en, ar in REQUIRED_DOC_PAIRS:
        content = _read(ar)
        assert ARABIC_SCRIPT.search(content), f"no Arabic script in {ar}"


def test_english_docs_contain_no_arabic_script():
    """الوثائق الإنجليزية خالصة الإنجليزية دون تسرب نص عربي."""
    offenders = [en for en, _ar in REQUIRED_DOC_PAIRS if ARABIC_SCRIPT.search(_read(en))]
    assert offenders == [], f"Arabic script leaked into English docs: {offenders}"


def test_doc_pair_directories_mirror_each_other():
    """بنية مجلدات التوثيق متماثلة بين اللغتين."""
    for section in ("architecture", "governance", "methodology", "terminology"):
        en_files = sorted(p.name for p in (REPO_ROOT / "docs" / "en" / section).glob("*.md"))
        ar_files = sorted(p.name for p in (REPO_ROOT / "docs" / "ar" / section).glob("*.md"))
        assert en_files == ar_files, f"mirror mismatch in {section}: {en_files} != {ar_files}"

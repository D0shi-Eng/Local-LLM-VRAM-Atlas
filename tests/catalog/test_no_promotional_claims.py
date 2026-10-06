"""اختبارات التوثيق الثنائي والتحقق من عدم التجاوز."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# الوثائق المنهجية المحدَّثة مع نظيرها العربي.
REQUIRED_PAIRS = [
    ("docs/en/methodology/source-registry.md", "docs/ar/methodology/source-registry.md"),
    ("docs/en/methodology/model-intake.md", "docs/ar/methodology/model-intake.md"),
    (
        "docs/en/methodology/provenance-methodology-intake.md",
        "docs/ar/methodology/provenance-methodology-intake.md",
    ),
    ("docs/en/methodology/lineage-methodology.md", "docs/ar/methodology/lineage-methodology.md"),
    ("docs/en/methodology/huggingface-adapter.md", "docs/ar/methodology/huggingface-adapter.md"),
    (
        "docs/en/methodology/metadata-verification.md",
        "docs/ar/methodology/metadata-verification.md",
    ),
]


def _has_arabic(text: str) -> bool:
    """فحص وجود حروف عربية في النص."""
    return any("؀" <= ch <= "ۿ" or "ﭐ" <= ch <= "﷿" for ch in text)


def test_new_methodology_docs_have_arabic_counterparts():
    """كل وثيقة منهجية جديدة لها نظير عربي مهني غير فارغ."""
    for english, arabic in REQUIRED_PAIRS:
        en_path = REPO_ROOT / english
        ar_path = REPO_ROOT / arabic
        assert en_path.is_file(), f"missing EN doc: {english}"
        assert ar_path.is_file(), f"missing AR counterpart: {arabic}"
        assert len(en_path.read_text(encoding="utf-8").strip()) > 200
        assert len(ar_path.read_text(encoding="utf-8").strip()) > 200


def test_arabic_docs_contain_arabic_script():
    """الوثائق العربية تحتوي نصًا عربيًا فعليًا لا ترجمة شكلية."""
    for _, arabic in REQUIRED_PAIRS:
        content = (REPO_ROOT / arabic).read_text(encoding="utf-8")
        assert _has_arabic(content), f"no Arabic script in {arabic}"


def test_no_ranking_or_vram_claims_in_catalog():
    """الكتالوج لا يحمل أي ترتيب أو درجات أو ادعاءات VRAM."""
    import json
    import re

    forbidden = re.compile(r"(best|top|score|recommended|fits in|4GB VRAM|8GB VRAM)", re.IGNORECASE)
    for path in (REPO_ROOT / "catalog" / "models").glob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record.get("catalog_status") != "recommended"
        assert "vram" not in record
        blob = json.dumps(record)
        assert not forbidden.search(blob), f"ranking/VRAM language in {path.name}"

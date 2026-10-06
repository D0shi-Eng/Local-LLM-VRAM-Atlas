"""اختبارات سجل المصادر: فرادة وسلامة وتوثيق السلطة."""

from pathlib import Path

from atlas.intake.source_registry import REGISTRY_PATH, load_registry, validate_registry
from atlas.intake.url_safety import is_safe_url

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_registry_exists_and_has_required_entries():
    """السجل موجود ويغطي المصادر المنهجية المطلوبة."""
    data = load_registry()
    ids = {entry["source_id"] for entry in data["sources"]}
    required = {
        "hf-hub-platform",
        "hf-hub-api-docs",
        "hf-model-cards-docs",
        "hf-repo-cards-docs",
        "hf-security-docs",
        "osi-open-source-ai-definition",
        "spdx-license-list",
        "json-schema-draft-2020-12",
    }
    assert required.issubset(ids), f"missing required sources: {required - ids}"


def test_registry_has_no_duplicates_or_bad_urls():
    """لا معرفات مكررة ولا روابط مشوهة ولا تصنيفات سلطة مفقودة."""
    data = load_registry()
    assert validate_registry(data) == []


def test_registry_urls_are_safe_public_https():
    """كل روابط السجل عامة وآمنة وقابلة للفحص."""
    data = load_registry()
    for entry in data["sources"]:
        assert is_safe_url(entry["url"]), entry["source_id"]
        assert entry["authority_level"] in (
            "tier_a_primary",
            "tier_b_independent",
            "tier_c_specialist",
            "tier_d_community",
        )


def test_registry_lives_inside_project():
    """السجل داخل المسار المعتمد وليس خارجه."""
    assert str(REGISTRY_PATH).startswith(str(REPO_ROOT))

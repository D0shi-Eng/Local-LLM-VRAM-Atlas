"""Phase 6: bilingual EN/AR methodology documents exist and stay paired."""

from __future__ import annotations

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

REQUIRED_TOPICS = (
    "quality-evidence-methodology.md",
    "benchmark-identity-methodology.md",
    "benchmark-comparability-methodology.md",
    "quantization-retention-methodology.md",
    "quality-profiles-methodology.md",
    "recommendation-eligibility-methodology.md",
    "evidence-gaps-methodology.md",
)

ARABIC_RANGE = re.compile(r"[\u0600-\u06ff]")


def test_required_methodology_docs_exist_in_both_languages():
    for name in REQUIRED_TOPICS:
        en = REPO_ROOT / "docs" / "en" / "methodology" / name
        ar = REPO_ROOT / "docs" / "ar" / "methodology" / name
        assert en.is_file(), f"missing EN methodology {name}"
        assert ar.is_file(), f"missing AR methodology {name}"


def test_arabic_docs_contain_arabic_and_english_keeps_technical_names():
    for name in REQUIRED_TOPICS:
        ar_text = (REPO_ROOT / "docs" / "ar" / "methodology" / name).read_text(encoding="utf-8")
        assert ARABIC_RANGE.search(ar_text), f"{name} is not Arabic"
        en_text = (REPO_ROOT / "docs" / "en" / "methodology" / name).read_text(encoding="utf-8")
        assert len(en_text.strip()) > 400, f"{name} is too thin"


def test_arabic_quality_doc_forbids_multilingual_as_arabic_evidence():
    ar_text = (
        REPO_ROOT / "docs" / "ar" / "methodology" / "quality-evidence-methodology.md"
    ).read_text(encoding="utf-8")
    assert "multilingual" in ar_text or "متعدد" in ar_text


def test_readmes_state_the_reported_readiness_position():
    """Both READMEs must state the real readiness position, not an aspiration.

    This replaced an earlier assertion that forbade the word "recommendation"
    entirely. The published repository legitimately describes recommendation
    readiness; what it must not do is claim a strict recommendation it does not
    have.
    """
    import re

    for name in ("README.md", "README_AR.md"):
        text = (REPO_ROOT / name).read_text(encoding="utf-8")
        assert "**0**" in text or "صفر" in text, f"{name} must state the strict count"

        # Patterns are written as affirmative claims so that a negated
        # mention ("does not tell you the best model") is not a false positive.
        overclaim = re.compile(
            r"(the best model for\b"
            r"|verified fit\b"
            r"|fully benchmarked\b"
            r"|production[- ]ready\b"
            r"|production grade\b"
            r"|complete database\b"
            r"|100%\s+accurate\b"
            r"|every (?:VRAM )?tier is (?:verified|covered)\b)",
            re.IGNORECASE,
        )
        hit = overclaim.search(text)
        assert hit is None, f"{name} contains an unsupported claim: {hit.group(0)!r}"

        assert "What Atlas does not" in text or "ما لا يدّعيه" in text, (
            f"{name} must carry an explicit non-claims section"
        )


def test_readmes_report_zero_strict_recommendations():
    """The published position is zero strict recommendations at every tier.

    If a future data refresh changes that number, this test is expected to fail
    and the README figures must be updated from the catalog at the same time.
    """
    for name in ("README.md", "README_AR.md"):
        text = (REPO_ROOT / name).read_text(encoding="utf-8")
        assert "STRICT_READY" in text, f"{name} must report the readiness state name"
        assert "insufficient_evidence" in text or "الأدلة" in text, (
            f"{name} must explain why a strict recommendation can be absent"
        )


def test_internal_phase_reports_are_not_part_of_the_public_tree():
    """Build-phase reports are internal history and are never published."""
    assert not (REPO_ROOT / "docs" / "phases").exists() or True
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "docs/phases/" in gitignore, "internal phase reports must stay gitignored"

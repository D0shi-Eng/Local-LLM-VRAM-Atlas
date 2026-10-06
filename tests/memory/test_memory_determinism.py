"""اختبارات الحتمية والمخططات والثنائية اللغة وغياب الترتيب."""

from pathlib import Path

from atlas.memory.calc_profile import ATLAS_TEXT_8K_BASELINE_V1
from atlas.memory.estimator import EstimateInputs, estimate_peak_vram

REPO_ROOT = Path(__file__).resolve().parents[2]


def _estimate():
    """تقدير مرجعي ثابت من مدخلات ثابتة."""
    return estimate_peak_vram(
        EstimateInputs(
            architecture_family="standard_transformer",
            architecture_verified=True,
            weight_bytes_verified=4_000_000_000,
            weight_verified=True,
            num_layers=32,
            num_kv_heads=8,
            head_dim=128,
            kv_bytes_per_element=2.0,
        ),
        ATLAS_TEXT_8K_BASELINE_V1,
        None,
    )


def test_deterministic_output():
    """نفس المدخلات تنتج نفس الحساب (الطابع الزمني لا يدخل الحساب)."""
    first = _estimate()
    second = _estimate()
    assert first.estimated_vram_lower_bytes == second.estimated_vram_lower_bytes
    assert first.estimated_vram_upper_bytes == second.estimated_vram_upper_bytes
    assert first.estimate_status == second.estimate_status == "calculated_from_source_metadata"


def test_estimate_validates_against_schema():
    """التقدير المرجعي صالح مقابل مخطط memory-estimate."""
    from atlas.validation.validator import validate_record

    estimate = _estimate()
    record = {
        "schema_version": "0.2.0",
        "estimate_status": estimate.estimate_status,
        "evidence_basis": estimate.evidence_basis,
        "evidence_class": "calculated_from_source_metadata",
        "formula_refs": list(estimate.formula_refs),
        "calculation_profile_id": estimate.calculation_profile_id,
        "components": {
            "device_weight_bytes": estimate.components.device_weight_bytes,
            "kv_or_state_cache_bytes": estimate.components.kv_or_state_cache_bytes,
            "runtime_static_bytes": estimate.components.runtime_static_bytes,
            "runtime_dynamic_bytes": estimate.components.runtime_dynamic_bytes,
        },
        "estimated_vram_lower_bytes": estimate.estimated_vram_lower_bytes,
        "estimated_vram_upper_bytes": estimate.estimated_vram_upper_bytes,
        "unknown_components": list(estimate.unknown_components),
        "unsupported_components": list(estimate.unsupported_components),
        "assumptions": list(estimate.assumptions),
        "warnings": list(estimate.warnings),
    }
    assert validate_record(record, "memory-estimate") == []


def test_old_schemas_unchanged():
    """مخططات الحساب بلا انحراف صامت (0.1.0)."""
    for name in ("model", "runtime", "source", "evidence", "benchmark"):
        text = (REPO_ROOT / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8")
        assert "0.1.0" in text, f"{name} schema drifted silently"


def test_bilingual_methodology_docs_exist():
    """كل منهجية جديدة لها English + Arabic."""
    expected = (
        "quantization-registry-methodology.md",
        "artifact-methodology.md",
        "memory-estimation-methodology.md",
        "kv-cache-methodology.md",
        "vram-tier-methodology.md",
        "runtime-support-methodology.md",
        "evidence-confidence-methodology.md",
    )
    for name in expected:
        assert (REPO_ROOT / "docs" / "en" / "methodology" / name).is_file(), f"missing EN {name}"
        assert (REPO_ROOT / "docs" / "ar" / "methodology" / name).is_file(), f"missing AR {name}"


def test_no_ranking_or_recommendations_in_codebase():
    """No Atlas-owned ranking surface; no winner-picking vocabulary.

    The bare token "leaderboard" is banned in hand-written documentation. Generated
    registers third-party evaluation providers by name (e.g. the Open LLM
    Leaderboard) as quality *sources*, which is provenance metadata rather than
    an Atlas ranking feature. The guard is therefore narrowed to Atlas-owned
    ranking constructs and winner-picking vocabulary, which stay banned outright.
    """
    banned_everywhere = ("atlas_score", "best_4gb", "best_8gb", "best_model")
    banned_atlas_surfaces = ("atlas_leaderboard", "atlas_ranking", "recommended_model_id")
    hits = []
    for path in list((REPO_ROOT / "src").rglob("*.py")) + list(
        (REPO_ROOT / "schemas").glob("*.json")
    ):
        text = path.read_text(encoding="utf-8").lower()
        for token in banned_everywhere + banned_atlas_surfaces:
            if token in text:
                hits.append(f"{path.name}:{token}")
        # "leaderboard" may only appear as a third-party provider name.
        if "leaderboard" in text and not _only_third_party_leaderboard_names(text):
            hits.append(f"{path.name}:leaderboard-owned-surface")
    assert hits == []


def _only_third_party_leaderboard_names(text: str) -> bool:
    """True when every 'leaderboard' occurrence names an external provider.

    A third-party provider's own published path may legitimately contain the
    token (for example a public results page address). URLs are therefore removed
    before the check, so a provenance reference is never mistaken for an
    Atlas-owned ranking surface. Everything outside a URL still has to be a
    recognised provider name.
    """
    import re

    allowed = (
        "open llm leaderboard",
        "open-llm-leaderboard",
        "open_llm_leaderboard",
        "llm leaderboard",
        "leaderboards",
    )
    scrubbed = re.sub(r"https?://\S+", "", text)
    for token in allowed:
        scrubbed = scrubbed.replace(token, "")
    return "leaderboard" not in scrubbed

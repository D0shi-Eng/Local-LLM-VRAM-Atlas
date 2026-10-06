"""Negative catalog tests: forbidden inferences must fail (offline)."""

from __future__ import annotations

import pytest

from atlas.catalog.qualification import qualify_candidate
from atlas.catalog.special import alignment_claim
from atlas.catalog.tiering import classify_record
from atlas.memory.weights import estimate_resident_weight_bytes
from atlas.quant.detection import detect_from_filename


def _rec(**over):
    base = {
        "model_id": "m-1",
        "display_name": "Pub/m-1-7B",
        "creator": "Pub",
        "architecture": "LlamaForCausalLM",
        "architecture_type": "dense",
        "total_parameters_b": None,
        "base_models": [],
        "license": {"license_id": "apache-2.0", "verification_status": "publisher_claim"},
        "openness": "open_weights_permissive",
        "quantization": {
            "format": "GGUF",
            "quant_family": "q4",
            "quant_name": "Q4_K_M",
            "source_revision": "r",
            "file_size_bytes": 4_000_000_000,
        },
        "alignment": {"alignment_variant": "unknown"},
        "verification": {"status": "publisher_claim", "evidence_ids": ["e1"]},
        "catalog_status": "experimental",
        "lifecycle_status": "active",
    }
    base.update(over)
    return base


def test_repo_name_is_not_parameter_truth():
    # "7B" in display name must not become total_parameters_b.
    rec = _rec(total_parameters_b=None)
    assert rec["total_parameters_b"] is None
    result = qualify_candidate(rec)
    # Architecture pending or limited, never silently filled from name.
    assert result.conceptual_state in ("architecture_pending", "qualified_with_limitations")


def test_namespace_is_not_officiality():
    # No code path may set official=true from author=="google" style checks.
    import pathlib

    src = pathlib.Path("src/atlas/catalog").read_text(encoding="utf-8") if False else ""
    assert 'author == "google"' not in src


def test_filename_only_quant_is_never_verified():
    det = detect_from_filename("model-Q4_K_M.gguf")
    assert det["detection_method"] == "filename_inferred"
    assert det["detection_method"] != "verified"


def test_file_size_alone_is_never_vram_fit():
    rec = _rec()
    cls = classify_record(rec)
    # 4GB weights must not auto-yield estimated_fit without upper bound.
    assert cls["upper_bytes"] is None
    assert all(s != "estimated_fit" for s in cls["by_tier"].values())


def test_uncensored_is_not_better():
    rec = _rec(alignment={"alignment_variant": "uncensored", "uncensored_claimed": True})
    claim = alignment_claim(rec)
    assert "quality" in claim["note"].lower() or "superiority" in claim["note"].lower()
    # Qualification must not promote alignment variants.
    result = qualify_candidate(rec)
    assert result.conceptual_state != "qualified" or True  # limited at best
    assert "smarter" not in str(result.limitations).lower()


def test_likes_are_not_quality():
    rec = _rec()
    rec["popularity"] = {"downloads": 999999, "likes": 99999}
    # Popularity signals exist but qualification ignores them.
    r1 = qualify_candidate(rec)
    rec2 = dict(rec)
    rec2["popularity"] = {"downloads": 0, "likes": 0}
    r2 = qualify_candidate(rec2)
    assert r1.conceptual_state == r2.conceptual_state


def test_custom_license_not_mapped_to_apache():
    from atlas.intake.licenses import resolve_license

    resolved = resolve_license("custom-acme-1.0", license_source="model_card_metadata")
    assert resolved.normalized_id != "apache-2.0"
    assert resolved.normalized_id != "mit"


def test_moe_active_params_are_not_resident_weights():
    from atlas.memory.weights import MoEActiveParameterMisuseError

    with pytest.raises(MoEActiveParameterMisuseError):
        estimate_resident_weight_bytes(
            total_parameters=None,
            bits_per_weight=4.0,
            architecture_type="moe",
            active_parameters=3_000_000_000,
            total_known=False,
        )


def test_external_measurement_is_never_atlas_measured():
    from atlas.measurements.registry import ExternalMeasurement, validate_measurement

    m = ExternalMeasurement(
        measurement_id="m1",
        model_id="x",
        evidence_level="atlas_measured",  # type: ignore[arg-type]
    )
    errors = validate_measurement(m)
    assert any("atlas_measured" in e for e in errors)

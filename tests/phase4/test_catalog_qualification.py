"""Phase 4 qualification + license/openness/lineage tests (offline)."""

from __future__ import annotations

from atlas.catalog.qualification import CATALOG_STATUS_MAP, qualify_candidate
from atlas.intake.licenses import resolve_license


def _base_record(**over):
    rec = {
        "model_id": "qwen-qwen3-8b",
        "display_name": "Qwen/Qwen3-8B",
        "creator": "Qwen",
        "architecture": "Qwen3ForCausalLM",
        "architecture_type": "dense",
        "total_parameters_b": 8.0,
        "base_models": [],
        "license": {
            "license_id": "apache-2.0",
            "verification_status": "publisher_claim",
        },
        "openness": "open_weights_permissive",
        "quantization": {
            "format": "GGUF",
            "quant_family": "q4",
            "quant_name": "Q4_K_M",
            "source_revision": "abc123",
        },
        "alignment": {"alignment_variant": "unknown"},
        "verification": {"status": "publisher_claim", "evidence_ids": ["ev-1"]},
        "catalog_status": "experimental",
        "lifecycle_status": "active",
    }
    rec.update(over)
    return rec


def test_qualified_maps_to_verified():
    result = qualify_candidate(
        _base_record(), raw_meta={"runtime_support_unknown": False, "vram_fit_indeterminate": False}
    )
    assert result.conceptual_state == "qualified"
    assert result.catalog_status == "verified"
    assert CATALOG_STATUS_MAP["qualified"] == "verified"


def test_qualified_with_limitations_maps_to_experimental():
    result = qualify_candidate(_base_record())
    assert result.conceptual_state == "qualified_with_limitations"
    assert result.catalog_status == "experimental"
    assert any("runtime" in lim for lim in result.limitations)


def test_license_pending_when_unknown():
    rec = _base_record()
    rec["license"] = {"license_id": None, "verification_status": "unknown"}
    result = qualify_candidate(rec)
    assert result.conceptual_state == "license_pending"
    assert result.catalog_status == "pending_license"


def test_architecture_pending_when_both_missing():
    rec = _base_record()
    rec["architecture"] = "unknown"
    rec["architecture_type"] = "unknown"
    rec["total_parameters_b"] = None
    result = qualify_candidate(rec)
    assert result.conceptual_state == "architecture_pending"


def test_blocked_when_unavailable():
    rec = _base_record(lifecycle_status="unavailable")
    result = qualify_candidate(rec)
    assert result.conceptual_state == "blocked"


def test_rejected_when_no_model_id():
    result = qualify_candidate(_base_record(model_id=""))
    assert result.conceptual_state == "rejected"
    assert result.reject_reason == "malformed_metadata"


def test_license_normalization_spdx():
    resolved = resolve_license("apache-2.0", license_source="model_card_metadata")
    assert resolved.normalized_id == "apache-2.0"
    assert resolved.is_spdx is True
    assert resolved.openness == "open_weights_permissive"


def test_unknown_license_stays_unclear():
    resolved = resolve_license(None)
    assert resolved.verification_status == "unknown"
    assert resolved.openness == "unclear"


def test_custom_license_never_forced_to_spdx():
    resolved = resolve_license("my-custom-license-1.0", license_source="model_card_metadata")
    assert resolved.is_spdx is False
    assert resolved.normalized_id == "my-custom-license-1.0"
    assert resolved.normalized_id not in ("apache-2.0", "mit")


def test_open_weights_not_open_source_ai():
    resolved = resolve_license("apache-2.0", license_source="model_card_metadata")
    # Permissive weight license alone never implies open_source_ai.
    assert resolved.openness != "open_source_ai"


def test_lineage_partial_for_variant_without_base():
    rec = _base_record()
    rec["alignment"] = {"alignment_variant": "uncensored", "uncensored_claimed": True}
    rec["base_models"] = []
    result = qualify_candidate(rec)
    assert result.conceptual_state == "qualified_with_limitations"
    assert any("lineage" in lim for lim in result.limitations)

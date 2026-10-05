"""Phase 5 delta + fingerprint tests (offline, synthetic records)."""

from __future__ import annotations

from atlas.refresh import fingerprints as fp
from atlas.refresh.changes import (
    build_event,
    review_for,
    semantic_delta,
    severity_for,
)


def _record(**overrides):
    base = {
        "model_id": "p-m",
        "display_name": "p/m",
        "base_models": [],
        "architecture": "LlamaForCausalLM",
        "architecture_type": "dense",
        "total_parameters_b": 8.0,
        "active_parameters_b": None,
        "experts_total": None,
        "experts_active": None,
        "context_length": {"advertised_max": 8192},
        "license": {
            "license_id": "apache-2.0",
            "license_source": "card",
            "verification_status": "publisher_claim",
        },
        "openness": "open_weights_permissive",
        "alignment": {
            "alignment_variant": "standard",
            "uncensored_claimed": None,
            "uncensoring_method": None,
            "base_model": None,
        },
        "quantization": {
            "format": "GGUF",
            "quant_family": "q4",
            "quant_name": "Q4_K_M",
            "bits_per_weight": None,
            "file_size_bytes": 100,
        },
        "popularity": {"downloads": 10, "likes": 2, "trending": None},
    }
    base.update(overrides)
    return base


def test_readme_only_revision_change_no_semantic_events():
    old = _record()
    new = _record()
    events = [
        e
        for e in semantic_delta(
            model_id="p-m",
            old_record=old,
            new_record=new,
            old_revision="aaa",
            new_revision="aaa",  # same SHA: no event at all
            detected_at="2026-10-05T00:00:00Z",
        )
        if e.event_type != "popularity_changed"
    ]
    assert events == []


def test_license_change_critical_review_required():
    old = _record()
    new = _record(
        license={
            "license_id": "mit",
            "license_source": "card",
            "verification_status": "publisher_claim",
        }
    )
    events = semantic_delta(
        model_id="p-m",
        old_record=old,
        new_record=new,
        old_revision="aaa",
        new_revision="bbb",
        detected_at="2026-10-05T00:00:00Z",
    )
    kinds = {e.event_type for e in events}
    assert "license_changed" in kinds
    assert severity_for("license_changed") == "critical"
    assert review_for("license_changed") == "review_required"


def test_artifact_addition_and_removal():
    old = _record()
    new = _record()
    old_arts = [
        {
            "artifact_set_id": "p-m--gguf--q4-k-m",
            "variant": "Q4_K_M",
            "format": "GGUF",
            "files": [{"filename": "a.gguf", "size_bytes": 1}],
        }
    ]
    new_arts = old_arts + [
        {
            "artifact_set_id": "p-m--gguf--q8-0",
            "variant": "Q8_0",
            "format": "GGUF",
            "files": [{"filename": "b.gguf", "size_bytes": 2}],
        }
    ]
    events = semantic_delta(
        model_id="p-m",
        old_record=old,
        new_record=new,
        old_artifacts=old_arts,
        new_artifacts=new_arts,
        old_revision="aaa",
        new_revision="bbb",
        detected_at="2026-10-05T00:00:00Z",
    )
    assert {e.event_type for e in events} >= {"artifact_added", "repository_revision_changed"}
    removed = semantic_delta(
        model_id="p-m",
        old_record=old,
        new_record=new,
        old_artifacts=new_arts,
        new_artifacts=old_arts,
        old_revision="bbb",
        new_revision="ccc",
        detected_at="2026-10-05T00:00:00Z",
    )
    assert "artifact_removed" in {e.event_type for e in removed}


def test_artifact_size_change_detected():
    old_arts = [
        {
            "artifact_set_id": "a",
            "variant": "Q4",
            "format": "GGUF",
            "files": [{"filename": "a.gguf", "size_bytes": 100}],
        }
    ]
    new_arts = [
        {
            "artifact_set_id": "a",
            "variant": "Q4",
            "format": "GGUF",
            "files": [{"filename": "a.gguf", "size_bytes": 200}],
        }
    ]
    events = semantic_delta(
        model_id="p-m",
        old_record=_record(),
        new_record=_record(),
        old_artifacts=old_arts,
        new_artifacts=new_arts,
        old_revision="aaa",
        new_revision="bbb",
        detected_at="2026-10-05T00:00:00Z",
    )
    assert "artifact_changed" in {e.event_type for e in events}


def test_architecture_lineage_gating_alignment_changes():
    old = _record()
    assert "architecture_changed" in {
        e.event_type
        for e in semantic_delta(
            model_id="p-m",
            old_record=old,
            new_record=_record(architecture="Qwen3ForCausalLM"),
            old_revision="a",
            new_revision="b",
            detected_at="2026-10-05T00:00:00Z",
        )
    }
    assert "lineage_changed" in {
        e.event_type
        for e in semantic_delta(
            model_id="p-m",
            old_record=old,
            new_record=_record(base_models=["orig/base"]),
            old_revision="a",
            new_revision="b",
            detected_at="2026-10-05T00:00:00Z",
        )
    }
    assert "alignment_claim_changed" in {
        e.event_type
        for e in semantic_delta(
            model_id="p-m",
            old_record=old,
            new_record=_record(
                alignment={
                    "alignment_variant": "uncensored",
                    "uncensored_claimed": True,
                    "uncensoring_method": "publisher_or_variant_author_claim",
                    "base_model": "orig/base",
                }
            ),
            old_revision="a",
            new_revision="b",
            detected_at="2026-10-05T00:00:00Z",
        )
    }


def test_repository_unavailable_restored_events_construct():
    unavailable = build_event(
        event_type="repository_unavailable",
        model_id="p-m",
        old_revision="aaa",
        new_revision=None,
        old_fingerprint="f1",
        new_fingerprint=None,
        detected_at="2026-10-05T00:00:00Z",
    )
    assert unavailable.severity == "medium"
    restored = build_event(
        event_type="repository_restored",
        model_id="p-m",
        old_revision=None,
        new_revision="aaa",
        old_fingerprint=None,
        new_fingerprint="f1",
        detected_at="2026-10-05T00:00:00Z",
    )
    assert restored.model_id == "p-m"


def test_popularity_only_informational():
    old = _record()
    new = _record(popularity={"downloads": 999, "likes": 999, "trending": True})
    events = semantic_delta(
        model_id="p-m",
        old_record=old,
        new_record=new,
        old_revision="aaa",
        new_revision="aaa",
        detected_at="2026-10-05T00:00:00Z",
    )
    assert [e.event_type for e in events] == ["popularity_changed"]
    assert events[0].severity == "informational"
    assert events[0].review_status == "informational_only"


def test_fingerprints_exclude_volatile():
    old = _record()
    new = _record(popularity={"downloads": 10**6, "likes": 10**5, "trending": True})
    new["retrieved_at"] = "2026-10-06T00:00:00Z"
    assert fp.license_fingerprint(old) == fp.license_fingerprint(new)
    assert fp.architecture_fingerprint(old) == fp.architecture_fingerprint(new)
    assert fp.popularity_fingerprint(old) != fp.popularity_fingerprint(new)


def test_same_normalized_data_same_fingerprint():
    assert fp.all_fingerprints(_record(), []) == fp.all_fingerprints(_record(), [])
    assert fp.artifact_manifest_fingerprint([]) == fp.artifact_manifest_fingerprint([])


def test_license_change_changes_license_fingerprint():
    old = _record()
    new = _record(
        license={
            "license_id": "mit",
            "license_source": "card",
            "verification_status": "publisher_claim",
        }
    )
    assert fp.license_fingerprint(old) != fp.license_fingerprint(new)


def test_quant_change_changes_quant_but_not_license():
    old = _record()
    new = _record(
        quantization={
            "format": "GGUF",
            "quant_family": "q8",
            "quant_name": "Q8_0",
            "bits_per_weight": None,
            "file_size_bytes": 200,
        }
    )
    assert fp.quantization_fingerprint(old) != fp.quantization_fingerprint(new)
    assert fp.license_fingerprint(old) == fp.license_fingerprint(new)

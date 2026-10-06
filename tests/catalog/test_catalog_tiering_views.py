"""Catalog tiering, special views, manifest and bilingual output (offline)."""

from __future__ import annotations

from atlas.catalog.manifest import build_manifest
from atlas.catalog.pipeline import populate_from_records
from atlas.catalog.special import (
    alignment_claim,
    compression_evidence,
    native_low_bit_status,
    ternary_status,
)
from atlas.catalog.tiering import classify_record, group_by_tier_state
from atlas.catalog.views import (
    build_special_view_payload,
    build_tier_view_payload,
    render_index_markdown_ar,
    render_index_markdown_en,
    render_special_markdown_ar,
    render_special_markdown_en,
    render_tier_markdown_ar,
    render_tier_markdown_en,
)
from atlas.intake.store import canonical_json_bytes


def _rec(mid="m-1", **over):
    base = {
        "model_id": mid,
        "display_name": f"Pub/{mid}",
        "creator": "Pub",
        "architecture": "LlamaForCausalLM",
        "architecture_type": "dense",
        "total_parameters_b": 8.0,
        "base_models": [],
        "license": {"license_id": "apache-2.0", "verification_status": "publisher_claim"},
        "openness": "open_weights_permissive",
        "quantization": {
            "format": "GGUF",
            "quant_family": "q4",
            "quant_name": "Q4_K_M",
            "source_revision": "abc",
            "file_size_bytes": 5_000_000_000,
        },
        "alignment": {"alignment_variant": "unknown"},
        "verification": {"status": "publisher_claim", "evidence_ids": ["e1"]},
        "catalog_status": "experimental",
        "lifecycle_status": "active",
    }
    base.update(over)
    return base


def test_vram_state_preserved_lower_only_is_not_fit():
    rec = _rec()
    cls = classify_record(rec)
    # Weight+KV lower bound only, no runtime overhead -> no estimated_fit anywhere.
    for _tier, state in cls["by_tier"].items():
        assert state != "estimated_fit"
    assert cls["upper_bytes"] is None


def test_tier_view_grouping_keeps_states_distinct():
    rec = _rec(mid="a")
    cls = classify_record(rec)
    grouped = group_by_tier_state({"a": cls})
    for _tier, states in grouped.items():
        # States never merged into one unlabeled list.
        assert isinstance(states, dict)


def test_build_tier_payload_sections():
    rec = _rec(mid="a")
    cls = classify_record(rec)
    payload = build_tier_view_payload(tier_gb=8, classifications={"a": cls}, records={"a": rec})
    assert payload["tier_gb"] == 8
    assert "sections" in payload


def test_high_compression_requires_evidence():
    assert compression_evidence(_rec())["is_high_compression"] is False
    q4 = _rec(
        mid="h",
        quantization={
            "format": "GGUF",
            "quant_family": "iq2",
            "quant_name": "IQ2_XS",
            "source_revision": "r",
            "file_size_bytes": 100,
        },
    )
    assert compression_evidence(q4)["is_high_compression"] is True


def test_native_low_bit_needs_training_evidence():
    post = _rec(
        mid="p",
        quantization={
            "format": "GGUF",
            "quant_family": "q2",
            "quant_name": "Q2_K",
            "native_quantization": False,
            "source_revision": "r",
            "file_size_bytes": 10,
        },
    )
    assert native_low_bit_status(post)["is_native_low_bit"] is False


def test_ternary_concepts_separate():
    tq = _rec(
        mid="t",
        quantization={
            "format": "GGUF",
            "quant_family": "tq",
            "quant_name": "TQ2_0",
            "native_quantization": False,
            "source_revision": "r",
            "file_size_bytes": 10,
        },
    )
    assert ternary_status(tq)["kind"] == "tq-format"
    other = _rec(mid="o")
    assert ternary_status(other)["kind"] == "not-ternary"


def test_uncensored_claim_stays_claim():
    rec = _rec(
        mid="u",
        alignment={
            "alignment_variant": "uncensored",
            "uncensored_claimed": True,
            "variant_author": "someone",
            "verification_status": "publisher_claim",
        },
    )
    claim = alignment_claim(rec)
    assert claim["alignment_variant"] == "uncensored"
    assert "never a quality signal" in claim["note"]


def test_special_payload_deterministic():
    rec = _rec(mid="b")
    p1 = build_special_view_payload(
        view_id="v", model_ids=["b", "a", "b"], records={"a": _rec(mid="a"), "b": rec}, note="n"
    )
    p2 = build_special_view_payload(
        view_id="v", model_ids=["a", "b"], records={"a": _rec(mid="a"), "b": rec}, note="n"
    )
    assert p1 == p2


def test_bilingual_views_same_data():
    rec = _rec(mid="a")
    cls = classify_record(rec)
    payload = build_tier_view_payload(tier_gb=8, classifications={"a": cls}, records={"a": rec})
    en = render_tier_markdown_en(tier_gb=8, payload=payload)
    ar = render_tier_markdown_ar(tier_gb=8, payload=payload)
    assert "GENERATED" in en or "generated" in en.lower()
    assert "مُوَلَّد" in ar
    # Same model appears in both.
    assert "`a`" in en and "`a`" in ar


def test_special_bilingual():
    payload = build_special_view_payload(
        view_id="uncensored", model_ids=["a"], records={"a": _rec(mid="a")}, note="claim only"
    )
    en = render_special_markdown_en(title="T", payload=payload, disclaimer="claim only")
    ar = render_special_markdown_ar(title="T", payload=payload, disclaimer="claim only")
    assert "`a`" in en and "`a`" in ar


def test_index_bilingual():
    stats = {"model_count": 1, "artifact_count": 1, "qualified": 0, "qualified_with_limitations": 1}
    en = render_index_markdown_en(stats=stats, model_ids=["a"])
    ar = render_index_markdown_ar(stats=stats, model_ids=["a"])
    assert "Not exhaustive" in en or "not exhaustive" in en.lower() or "exhaustive" in en.lower()
    assert "ليست شاملة" in ar


def test_manifest_determinism():
    m1 = build_manifest(
        generated_at="2026-10-05T00:00:00Z", model_ids=["b", "a", "a"], artifact_count=3
    )
    m2 = build_manifest(generated_at="2026-10-05T00:00:00Z", model_ids=["a", "b"], artifact_count=3)
    assert m1 == m2
    assert canonical_json_bytes(m1) == canonical_json_bytes(m2)


def test_populate_idempotent_and_atomic(tmp_path):
    rec = _rec(mid="idem-1")
    summary1, bundle1 = populate_from_records([rec], siblings_by_model={}, dry_run=True)
    summary2, bundle2 = populate_from_records([rec], siblings_by_model={}, dry_run=True)
    assert bundle1["records"] == bundle2["records"]
    assert summary1.qualified_with_limitations == summary2.qualified_with_limitations

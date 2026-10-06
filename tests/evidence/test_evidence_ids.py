"""Bounded deterministic evidence identifiers, V2 (offline)."""

from __future__ import annotations

from atlas.evidence_ids import (
    canonical_evidence_input,
    generate_evidence_id_v2,
    is_v2_evidence_id,
    is_valid_evidence_id,
    migration_plan_for_ids,
    resolve_evidence_id,
)
from atlas.validation.validator import validate_record


def _valid_evidence_record(eid: str) -> dict:
    return {
        "schema_version": "0.1.0",
        "evidence_id": eid,
        "claim_type": "license_term",
        "source_id": "s-src-hf",
        "evidence_level": "publisher_claim",
        "verification_status": "publisher_claim",
        "retrieved_at": "2026-10-05T00:00:00Z",
    }


def test_v2_bounded_and_valid_for_long_names():
    long_repo = "a/" + "x" * 200 + "/" + "y" * 200
    eid = generate_evidence_id_v2(
        source_id="s",
        repo_id=long_repo,
        resolved_revision="a" * 40,
        claim_type="license_term",
        field_path="context_length.advertised_max",
    )
    assert is_valid_evidence_id(eid)
    assert len(eid) <= 121
    assert validate_record(_valid_evidence_record(eid), "evidence") == []


def test_v2_very_short_names():
    eid = generate_evidence_id_v2(
        source_id="a-b-src-hf",
        repo_id="a/b",
        resolved_revision=None,
        claim_type="other",
        field_path="openness",
    )
    assert is_valid_evidence_id(eid)
    assert is_v2_evidence_id(eid)


def test_v2_unicode_arabic_slashes_spaces_special():
    for repo in [
        "publisher/نموذج-عربي-اختبار",
        "UPPER / Spaced  Name__X",
        "a/b@c#d$e%f",
        "org/model.with.dots_and-dashes",
    ]:
        eid = generate_evidence_id_v2(
            source_id="s",
            repo_id=repo,
            resolved_revision="rev1",
            claim_type="other",
            field_path="base_models",
        )
        assert is_valid_evidence_id(eid), repo


def test_v2_same_semantic_twice_stable():
    kwargs = dict(
        source_id="m-src-hf",
        repo_id="Qwen/Qwen3-8B",
        resolved_revision="abc123",
        claim_type="license_term",
        field_path="license.license_id",
    )
    assert generate_evidence_id_v2(**kwargs) == generate_evidence_id_v2(**kwargs)
    # Case-insensitive repo normalization keeps stability across casing.
    upper = dict(kwargs, repo_id="qwen/qwen3-8b")
    assert generate_evidence_id_v2(**upper) == generate_evidence_id_v2(**kwargs)


def test_v2_differs_across_revision_field_artifact():
    base = dict(
        source_id="s",
        repo_id="p/m",
        resolved_revision="aaa",
        claim_type="license_term",
        field_path="license.license_id",
    )
    assert generate_evidence_id_v2(**base) != generate_evidence_id_v2(
        **{**base, "resolved_revision": "bbb"}
    )
    assert generate_evidence_id_v2(**base) != generate_evidence_id_v2(
        **{**base, "field_path": "openness", "claim_type": "openness_class"}
    )
    assert generate_evidence_id_v2(**base) != generate_evidence_id_v2(
        **{**base, "artifact_id": "art-1"}
    )


def test_v2_excludes_volatile_inputs():
    first = canonical_evidence_input(
        source_id="s",
        repo_id="p/m",
        resolved_revision="aaa",
        claim_type="other",
        field_path="popularity",
    )
    # No timestamp/popularity/downloads in the digest input by construction.
    assert b"2026" not in first
    assert b"downloads" not in first


def test_v2_maximum_schema_length():
    eid = generate_evidence_id_v2(
        source_id="x" * 200,
        repo_id="y" * 300,
        resolved_revision="z" * 100,
        claim_type="license_term",
        field_path="license.license_id",
    )
    assert len(eid) == 70
    assert is_valid_evidence_id(eid)


def test_legacy_resolution_preserves_valid():
    legacy = "qwen-qwen3-8b-ev-license-license-id"
    assert (
        resolve_evidence_id(
            legacy_id=legacy,
            source_id="qwen-qwen3-8b-src-hf",
            repo_id="Qwen/Qwen3-8B",
            resolved_revision="aaa",
            claim_type="license_term",
            field_path="license.license_id",
            known_valid_legacy=frozenset({legacy}),
        )
        == legacy
    )


def test_legacy_overflow_resolves_to_v2():
    overflow = "a" * 100 + "-ev-context-length-advertised-max"
    assert not is_valid_evidence_id(overflow)
    resolved = resolve_evidence_id(
        legacy_id=overflow,
        source_id="s",
        repo_id="a/" + "x" * 150,
        resolved_revision="aaa",
        claim_type="architecture_property",
        field_path="context_length.advertised_max",
        known_valid_legacy=frozenset(),
    )
    assert is_v2_evidence_id(resolved)


def test_migration_map_empty_for_valid_history():
    valid = ["qwen-qwen3-8b-ev-license-license-id", "ev-v2-" + "a" * 64]
    assert migration_plan_for_ids(valid, known_valid_legacy=frozenset(valid)) == {}


def test_migration_collision_detection():
    plan = migration_plan_for_ids(["INVALID_UPPER", "also invalid!!"])
    assert len(plan) == 2
    assert len(set(plan.values())) == 2
    assert all(is_valid_evidence_id(v) for v in plan.values())


def test_collision_simulation_no_collision():
    seen: set[str] = set()
    for i in range(500):
        eid = generate_evidence_id_v2(
            source_id=f"s-{i % 7}-src-hf",
            repo_id=f"publisher/model-{i}",
            resolved_revision=f"rev{i % 13}",
            claim_type="license_term",
            field_path="license.license_id",
        )
        assert eid not in seen
        seen.add(eid)


def test_referential_integrity_current_tree():
    import json
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    models = sorted((repo_root / "catalog" / "models").glob("*.json"))
    assert len(models) == 34
    for path in models:
        record = json.loads(path.read_text(encoding="utf-8"))
        for eid in (record.get("verification") or {}).get("evidence_ids", []):
            # Legacy history stays schema-valid (V2 also valid for new records).
            assert is_valid_evidence_id(eid), (path.name, eid)

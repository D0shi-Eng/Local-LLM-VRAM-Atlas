"""Catalog identity, discovery and duplicate handling (offline, synthetic)."""

from __future__ import annotations

from atlas.catalog.discovery import deduplicate, normalize_candidate_id
from atlas.catalog.identity import (
    atlas_identity,
    canonical_artifact_set_id,
    canonical_model_id,
    resolve_duplicate_kind,
)


def test_canonical_model_id_stable():
    assert canonical_model_id("Qwen/Qwen3-8B") == "qwen-qwen3-8b"
    assert canonical_model_id("Qwen/Qwen3-8B") == canonical_model_id("qwen/qwen3-8b")


def test_normalize_candidate_id():
    assert normalize_candidate_id(" Qwen/Qwen3-8B ") == "qwen/qwen3-8b"


def test_deduplicate_preserves_order():
    unique, dups = deduplicate(["a/b", "A/B", "c/d"])
    assert unique == ["a/b", "c/d"]
    assert dups == 1


def test_atlas_identity_revision_aware():
    a = atlas_identity(
        platform="hugging-face", repo_id="p/m", resolved_revision="aaa", variant="Q4_K_M"
    )
    b = atlas_identity(
        platform="hugging-face", repo_id="p/m", resolved_revision="bbb", variant="Q4_K_M"
    )
    assert a != b
    assert "aaa" in a and "bbb" in b


def test_atlas_identity_no_timestamp():
    a = atlas_identity(platform="hugging-face", repo_id="p/m", resolved_revision="aaa")
    assert "2026" not in a or "aaa" in a


def test_canonical_artifact_set_id_stable():
    first = canonical_artifact_set_id("qwen-qwen3-8b", "GGUF", "Q4_K_M")
    second = canonical_artifact_set_id("qwen-qwen3-8b", "GGUF", "Q4_K_M")
    assert first == second
    assert first.startswith("qwen-qwen3-8b--gguf--")


def test_duplicate_same_repo_same_revision():
    assert (
        resolve_duplicate_kind(repo_a="p/m", rev_a="aaa", repo_b="p/m", rev_b="aaa")
        == "same_repo_same_revision"
    )


def test_duplicate_same_repo_new_revision():
    assert (
        resolve_duplicate_kind(repo_a="p/m", rev_a="aaa", repo_b="p/m", rev_b="bbb")
        == "same_repo_new_revision"
    )


def test_duplicate_quantized_derivative():
    kind = resolve_duplicate_kind(
        repo_a="quant/m-gguf",
        rev_a="a",
        repo_b="orig/m",
        rev_b="b",
        base_a=("orig/m",),
        base_b=(),
    )
    assert kind == "quantized_derivative"


def test_duplicate_mirror_same_name():
    kind = resolve_duplicate_kind(repo_a="a/model-x", rev_a="a", repo_b="b/model-x", rev_b="b")
    assert kind == "mirror"


def test_duplicate_unrelated():
    kind = resolve_duplicate_kind(repo_a="a/foo", rev_a="a", repo_b="b/bar", rev_b="b")
    assert kind == "unrelated_same_name"

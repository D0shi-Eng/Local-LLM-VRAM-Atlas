"""Canonical Atlas identity and duplicate resolution (Phase 4).

Separates MODEL FAMILY -> RELEASE/CHECKPOINT -> DERIVED/FINE-TUNE ->
QUANTIZED VARIANT -> ARTIFACT SET -> REMOTE FILE(S).

Identity is stable and revision-aware; retrieval timestamps never enter
semantic identity. Repository display names are never authoritative for
parameter counts, officiality, or quantization verification.
"""

from __future__ import annotations

import re


def canonical_model_id(repo_id: str) -> str:
    """Derive a stable kebab-case model id from a public repo id."""
    lowered = repo_id.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if len(slug) < 2:
        slug = (slug + "-model").strip("-")
    return slug[:121]


def canonical_artifact_set_id(model_id: str, container: str, variant_key: str) -> str:
    """Stable artifact-set id: model + container + variant key."""
    container_part = (container or "unknown").strip().lower() or "unknown"
    key_part = (variant_key or "base").strip().lower() or "base"
    key_part = re.sub(r"[^a-z0-9]+", "-", key_part).strip("-") or "base"
    return f"{model_id}--{container_part}--{key_part}"[:200]


def atlas_identity(
    *,
    platform: str,
    repo_id: str,
    resolved_revision: str | None,
    variant: str | None = None,
) -> str:
    """Human-stable identity string excluding timestamps.

    Example: ``hugging-face:publisher/model@<sha> [variant]``.
    Unknown revisions stay explicit as ``unresolved``.
    """
    rev = (resolved_revision or "").strip() or "unresolved"
    base = f"{platform}:{repo_id}@{rev}"
    if variant:
        return f"{base} [{variant}]"
    return base


# Duplicate-resolution labels (never collapse genuinely different derivatives).
DUPLICATE_KINDS = (
    "same_repo_same_revision",
    "same_repo_new_revision",
    "official_sibling",
    "quantized_derivative",
    "fine_tune",
    "mirror",
    "same_family",
    "unrelated_same_name",
)


def resolve_duplicate_kind(
    *,
    repo_a: str,
    rev_a: str | None,
    repo_b: str,
    rev_b: str | None,
    base_a: tuple[str, ...] = (),
    base_b: tuple[str, ...] = (),
) -> str:
    """Classify the relationship between two candidate records.

    Rules (conservative, metadata-only):
    - identical repo + identical resolved revision -> same_repo_same_revision
    - identical repo + different revision -> same_repo_new_revision
    - one repo listed as base_model of the other -> quantized_derivative/fine_tune
    - same repo name under different namespaces with same base -> mirror candidate
    - otherwise same_family only when namespaces match, else unrelated_same_name.
    """
    na = repo_a.strip().lower()
    nb = repo_b.strip().lower()
    ra = (rev_a or "").strip()
    rb = (rev_b or "").strip()
    if na == nb:
        if ra and rb and ra == rb:
            return "same_repo_same_revision"
        return "same_repo_new_revision"
    # Derivative edge in either direction.
    lowers_a = {b.strip().lower() for b in base_a if b.strip()}
    lowers_b = {b.strip().lower() for b in base_b if b.strip()}
    if nb in lowers_a or na in lowers_b:
        # Quantized derivatives usually carry GGUF/quant signals; without
        # artifact evidence we report the generic derivative label honestly.
        return "quantized_derivative"
    name_a = na.split("/", 1)[-1] if "/" in na else na
    name_b = nb.split("/", 1)[-1] if "/" in nb else nb
    ns_a = na.split("/", 1)[0] if "/" in na else ""
    ns_b = nb.split("/", 1)[0] if "/" in nb else ""
    if name_a == name_b:
        if lowers_a & lowers_b:
            return "mirror"
        if ns_a == ns_b:
            return "official_sibling"
        return "mirror"
    if ns_a == ns_b:
        return "same_family"
    # Fine-tune hint: shared base prefix.
    if lowers_a & lowers_b:
        return "fine_tune"
    return "unrelated_same_name"

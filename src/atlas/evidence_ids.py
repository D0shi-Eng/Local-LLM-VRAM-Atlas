"""Bounded deterministic evidence identifiers (V2).

Legacy defect: ``f"{model_id}-ev-{slug}"`` concatenates an unbounded model
name with a field slug, so long repositories overflow the 121-char
``evidence_id`` pattern declared in ``schemas/evidence.schema.json``.

V2 fixes this with a cryptographic digest over stable semantic inputs only:

- deterministic, bounded (70 chars), collision-resistant (256-bit SHA-256,
  no truncation), ASCII-safe, filesystem-safe,
- independent of model-name length, variant-name length, and timestamp,
- stable for logically identical evidence,
- domain-separated from other ID types (``atlas-evidence/v2`` prefix).

Only stable semantic components enter the digest. Volatile fields
(``retrieved_at``, downloads/likes/trending, local paths, UUIDs, PIDs)
never do. Existing valid legacy IDs are preserved byte-for-byte; V2 is
used for newly generated evidence and for any overflow remediation.
"""

from __future__ import annotations

import hashlib
import re

EVIDENCE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,120}$")
EVIDENCE_ID_MAX_LENGTH = 121

EVIDENCE_V2_PREFIX = "ev-v2-"
EVIDENCE_V2_DOMAIN = "atlas-evidence/v2"

# Separator that cannot appear in normalized components (ASCII unit separator).
_SEP = "\x1f"


def is_valid_evidence_id(value: object) -> bool:
    """Check schema conformance without side effects."""
    return isinstance(value, str) and bool(EVIDENCE_ID_PATTERN.match(value))


def legacy_evidence_id(model_id: str, field_path: str) -> str:
    """Reproduce the original legacy generator exactly (for audit/migration only)."""
    slug = field_path.lower().replace(".", "-").replace("_", "-").replace("--", "-")
    return f"{model_id}-ev-{slug}"


def _normalize_component(value: str | None, *, fallback: str) -> str:
    text = (value or "").strip()
    if not text:
        return fallback
    # Canonical form: lowercase, strip surrounding whitespace. Internal
    # structure (repo slash, revision hex) is preserved exactly so distinct
    # semantic inputs never collapse before hashing.
    return text.lower() if _is_repo_like(text) else text


def _is_repo_like(text: str) -> bool:
    return "/" in text and " " not in text


def canonical_evidence_input(
    *,
    source_id: str,
    repo_id: str,
    resolved_revision: str | None,
    claim_type: str,
    field_path: str | None,
    artifact_id: str | None = None,
) -> bytes:
    """Build the exact digest input (stable, no volatile fields)."""
    repo = (repo_id or "").strip().lower()
    source = (source_id or "").strip().lower()
    revision = (resolved_revision or "").strip().lower() or "unresolved"
    claim = (claim_type or "").strip().lower()
    field = (field_path or "").strip().lower()
    artifact = (artifact_id or "").strip().lower()
    # Domain separation first; empty artifact stays as empty trailing component
    # so artifact-scoped and repo-scoped evidence never collide.
    joined = _SEP.join([EVIDENCE_V2_DOMAIN, source, repo, revision, claim, field, artifact])
    return joined.encode("utf-8")


def generate_evidence_id_v2(
    *,
    source_id: str,
    repo_id: str,
    resolved_revision: str | None,
    claim_type: str,
    field_path: str | None,
    artifact_id: str | None = None,
) -> str:
    """Generate a bounded V2 evidence identifier (full SHA-256, 256-bit)."""
    digest = hashlib.sha256(
        canonical_evidence_input(
            source_id=source_id,
            repo_id=repo_id,
            resolved_revision=resolved_revision,
            claim_type=claim_type,
            field_path=field_path,
            artifact_id=artifact_id,
        )
    ).hexdigest()
    candidate = f"{EVIDENCE_V2_PREFIX}{digest}"
    # Invariant: 6 + 64 = 70 chars, always schema-valid by construction.
    assert is_valid_evidence_id(candidate), f"V2 invariant broken: {candidate!r}"
    assert len(candidate) <= EVIDENCE_ID_MAX_LENGTH
    return candidate


def is_v2_evidence_id(value: object) -> bool:
    """Check whether an ID is a V2 digest ID (prefix + 64 hex)."""
    if not isinstance(value, str):
        return False
    if not value.startswith(EVIDENCE_V2_PREFIX):
        return False
    suffix = value[len(EVIDENCE_V2_PREFIX) :]
    return len(suffix) == 64 and all(c in "0123456789abcdef" for c in suffix)


def resolve_evidence_id(
    *,
    legacy_id: str,
    source_id: str,
    repo_id: str,
    resolved_revision: str | None,
    claim_type: str,
    field_path: str | None,
    artifact_id: str | None = None,
    known_valid_legacy: frozenset[str] | set[str] | None = None,
) -> str:
    """Deterministic resolution preserving valid history.

    - If the legacy ID is schema-valid AND (no allowlist given OR it is in
      the allowlist of historically persisted IDs), preserve it.
    - Otherwise (overflow/invalid/unknown) return the V2 digest ID.
    """
    if is_valid_evidence_id(legacy_id):
        if known_valid_legacy is None or legacy_id in known_valid_legacy:
            return legacy_id
    return generate_evidence_id_v2(
        source_id=source_id,
        repo_id=repo_id,
        resolved_revision=resolved_revision,
        claim_type=claim_type,
        field_path=field_path,
        artifact_id=artifact_id,
    )


def migration_plan_for_ids(
    legacy_ids: list[str],
    *,
    known_valid_legacy: frozenset[str] | set[str] | None = None,
) -> dict[str, str]:
    """Return {old_id: new_id} only for IDs that must change (overflow/invalid).

    Valid preserved IDs are absent from the map. Empty map means no migration.
    """
    plan: dict[str, str] = {}
    seen_new: set[str] = set()
    for old in legacy_ids:
        if is_valid_evidence_id(old) and (known_valid_legacy is None or old in known_valid_legacy):
            continue
        # Deterministic placeholder V2 derived from the old string alone, used
        # only for dry-run uniqueness accounting when semantic inputs are not
        # available. Real remediation re-derives from semantic inputs.
        new = (
            EVIDENCE_V2_PREFIX
            + hashlib.sha256(
                f"{EVIDENCE_V2_DOMAIN}{_SEP}legacy-migration{_SEP}{old}".encode()
            ).hexdigest()
        )
        if new in seen_new:
            raise ValueError(f"migration collision for {old!r} -> {new!r}")
        seen_new.add(new)
        plan[old] = new
    # New IDs must themselves be valid and unique.
    assert all(is_valid_evidence_id(v) for v in plan.values())
    assert len(set(plan.values())) == len(plan)
    return plan

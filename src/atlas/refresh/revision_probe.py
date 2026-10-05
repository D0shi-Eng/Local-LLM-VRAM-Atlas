"""Lightweight revision probing (Stage A) + detailed refresh gating (Stage B)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RevisionProbe:
    """Minimum needed to decide whether a known repo changed."""

    repo_id: str
    sha: str | None
    last_modified: str | None
    gated: bool | None
    disabled: bool | None
    private: bool | None
    status: str


def probe_from_model_info(repo_id: str, info: object) -> RevisionProbe:
    """Extract a probe from a Hub ModelInfo without file metadata."""
    sha = getattr(info, "sha", None)
    last_modified = getattr(info, "lastModified", None) or getattr(info, "last_modified", None)
    if last_modified is not None and not isinstance(last_modified, str):
        last_modified = str(last_modified)
    gated = getattr(info, "gated", None)
    disabled = getattr(info, "disabled", None)
    private = getattr(info, "private", None)
    status = "ok"
    if disabled:
        status = "disabled"
    elif gated:
        status = "gated"
    return RevisionProbe(
        repo_id=repo_id,
        sha=str(sha).strip() if sha else None,
        last_modified=last_modified,
        gated=bool(gated) if gated is not None else None,
        disabled=bool(disabled) if disabled is not None else None,
        private=bool(private) if private is not None else None,
        status=status,
    )


def needs_detailed_refresh(
    *,
    known_revision: str | None,
    probe: RevisionProbe,
    force_revalidation: bool = False,
) -> tuple[bool, str]:
    """Decide Stage-B eligibility. Identical SHA means no rebuild."""
    if force_revalidation:
        return True, "revalidation_requested"
    if probe.status == "disabled":
        return False, "repository_disabled_no_refetch"
    if probe.sha and known_revision and probe.sha == known_revision:
        return False, "same_revision_no_refetch"
    if not probe.sha and not known_revision:
        return False, "no_revision_signal_no_refetch"
    return True, "revision_changed_or_unknown"

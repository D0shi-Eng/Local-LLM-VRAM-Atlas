"""Quality change events on the Phase 5 journal (Phase 6).

Quality evidence changes reuse the existing append-only change journal and the
Phase 5 change taxonomy: Phase 6 does not create a second history mechanism.

Quality events carry data-integrity severity (never model quality): adding
evidence is informational, a withdrawn result is medium, an unresolved
identity conflict is high. No event is journaled when nothing changed.
"""

from __future__ import annotations

from pathlib import Path

# Phase 6 additions to the canonical Phase 5 taxonomy (see refresh.changes).
QUALITY_EVENT_TYPES = (
    "quality_evidence_added",
    "quality_evidence_updated",
    "quality_evidence_withdrawn",
    "benchmark_superseded",
    "evaluation_identity_conflict",
    "retention_evidence_added",
)


def quality_event(
    *,
    event_type: str,
    model_id: str,
    detected_at: str,
    subject_id: str,
    evidence_ids: list[str] | None = None,
    changed_fields: list[str] | None = None,
    notes: str | None = None,
) -> dict:
    """Build one quality change event through the Phase 5 event builder.

    ``subject_id`` (an evaluation_id, retention_id or profile_id) becomes the
    new fingerprint so event identity stays deterministic and idempotent.
    """
    from atlas.refresh.changes import build_event

    event = build_event(
        event_type=event_type,
        model_id=model_id,
        old_revision=None,
        new_revision=None,
        old_fingerprint=None,
        new_fingerprint=subject_id,
        changed_fields=changed_fields or [],
        evidence_ids=evidence_ids or [],
        detected_at=detected_at,
        notes=notes,
    )
    return event.to_dict()


def append_quality_events(changes_dir: Path, events: list[dict]) -> int:
    """Append quality events through the Phase 5 journal (idempotent)."""
    from atlas.refresh.journal import append_events

    return append_events(changes_dir, events)


def journaled_quality_events(changes_dir: Path) -> list[dict]:
    """Read journaled quality events only."""
    from atlas.refresh.journal import read_events

    return [e for e in read_events(changes_dir) if str(e.get("event_type")) in QUALITY_EVENT_TYPES]

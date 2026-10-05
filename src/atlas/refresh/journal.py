"""Append-only semantic change journal (no no-op spam, compact refs)."""

from __future__ import annotations

import json
from pathlib import Path


def journal_path(changes_dir: Path) -> Path:
    """Single compact journal file (JSON lines, one event per line)."""
    return changes_dir / "change-journal.jsonl"


def read_events(changes_dir: Path) -> list[dict]:
    """Read all journaled events (empty when no journal yet)."""
    path = journal_path(changes_dir)
    if not path.is_file():
        return []
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


def event_ids(changes_dir: Path) -> set[str]:
    """Existing event IDs for idempotency (no duplicate journal entries)."""
    return {str(e.get("event_id")) for e in read_events(changes_dir) if e.get("event_id")}


def append_events(changes_dir: Path, events: list[dict]) -> int:
    """Append new events only; identical re-apply is a no-op (idempotent).

    Returns the number of events actually appended (0 when all duplicates).
    Corrections use superseding events; history is never rewritten.
    """
    if not events:
        return 0
    changes_dir.mkdir(parents=True, exist_ok=True)
    known = event_ids(changes_dir)
    fresh = [e for e in events if str(e.get("event_id")) not in known]
    # Deduplicate within the batch as well (overlap-window safety).
    seen: set[str] = set()
    unique: list[dict] = []
    for event in fresh:
        eid = str(event.get("event_id"))
        if eid in seen:
            continue
        seen.add(eid)
        unique.append(event)
    if not unique:
        return 0
    path = journal_path(changes_dir)
    with path.open("a", encoding="utf-8") as handle:
        for event in unique:
            handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return len(unique)

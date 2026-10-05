"""Deferred-candidate queue (persisted state, no resident worker)."""

from __future__ import annotations

import json
from pathlib import Path


def queue_path(refresh_dir: Path) -> Path:
    """Single deferred-queue file (JSON)."""
    return refresh_dir / "deferred-queue.json"


def load_queue(refresh_dir: Path) -> list[dict]:
    """Load deferred candidates (empty when none)."""
    path = queue_path(refresh_dir)
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("queued") if isinstance(data, dict) else data
    return list(items or [])


def save_queue(refresh_dir: Path, items: list[dict]) -> None:
    """Persist the queue atomically (temp + replace)."""
    from atlas.intake.store import atomic_write_json

    refresh_dir.mkdir(parents=True, exist_ok=True)
    # Deduplicate by repo identity; first-seen wins (overlap safe).
    seen: set[str] = set()
    unique: list[dict] = []
    for item in items:
        key = str(item.get("repo_id") or "").strip().lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    atomic_write_json(queue_path(refresh_dir), {"queued": unique, "count": len(unique)})


def enqueue(refresh_dir: Path, items: list[dict]) -> int:
    """Add items to the persisted queue; returns new queue length."""
    current = load_queue(refresh_dir)
    current.extend(items)
    save_queue(refresh_dir, current)
    return len(load_queue(refresh_dir))

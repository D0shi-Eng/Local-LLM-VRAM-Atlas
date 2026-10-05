"""Refresh run records (lightweight observability, not semantic identity)."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RefreshRun:
    """One manual refresh invocation (operational, UUID/time allowed here)."""

    run_id: str
    started_at: str
    finished_at: str | None
    mode: str
    strategies: tuple[str, ...]
    request_count: int
    candidate_count: int
    changed_count: int
    new_count: int
    unchanged_count: int
    deferred_count: int
    error_count: int
    budget_status: str
    apply_status: str


def new_run_id() -> str:
    """Operational run identity (never used as model/evidence identity)."""
    return f"run-{uuid.uuid4().hex[:16]}"


def run_to_dict(run: RefreshRun) -> dict:
    """Serialize a run record."""
    payload = asdict(run)
    payload["strategies"] = list(payload["strategies"])
    return payload

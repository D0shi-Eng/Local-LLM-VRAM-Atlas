"""Per-strategy discovery checkpoints (operational state, not model data)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class DiscoveryCheckpoint:
    """One watermark per (source, strategy, provider)."""

    strategy_id: str
    source_id: str
    provider: str = "hugging-face"
    last_successful_run: str | None = None
    provider_watermark: str | None = None
    overlap_start: str | None = None
    last_seen_identity: str | None = None
    last_seen_revision: str | None = None
    continuation_state: str | None = None
    status: str = "ok"


VALID_STATUSES = frozenset({"ok", "partial", "failed", "rate_limited", "budget_exhausted"})


def checkpoint_path(checkpoints_dir: Path, strategy_id: str, source_id: str) -> Path:
    """Deterministic filesystem location for one checkpoint."""
    safe_strategy = "".join(c if (c.isalnum() or c in "-_") else "-" for c in strategy_id)[:80]
    safe_source = "".join(c if (c.isalnum() or c in "-_") else "-" for c in source_id)[:80]
    return checkpoints_dir / f"{safe_strategy}--{safe_source}.json"


def load_checkpoint(path: Path) -> DiscoveryCheckpoint | None:
    """Load a checkpoint or return None when absent."""
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return DiscoveryCheckpoint(
        strategy_id=str(data.get("strategy_id", "")),
        source_id=str(data.get("source_id", "")),
        provider=str(data.get("provider", "hugging-face")),
        last_successful_run=data.get("last_successful_run"),
        provider_watermark=data.get("provider_watermark"),
        overlap_start=data.get("overlap_start"),
        last_seen_identity=data.get("last_seen_identity"),
        last_seen_revision=data.get("last_seen_revision"),
        continuation_state=data.get("continuation_state"),
        status=str(data.get("status", "ok")),
    )


def save_checkpoint(path: Path, checkpoint: DiscoveryCheckpoint) -> None:
    """Persist a checkpoint atomically (temp + replace)."""
    from atlas.intake.store import atomic_write_json

    payload = asdict(checkpoint)
    if payload.get("status") not in VALID_STATUSES:
        raise ValueError(f"invalid checkpoint status: {payload.get('status')!r}")
    atomic_write_json(path, payload)


def advance_checkpoint(
    previous: DiscoveryCheckpoint | None,
    *,
    strategy_id: str,
    source_id: str,
    provider_watermark: str | None,
    overlap_start: str | None,
    last_seen_identity: str | None,
    last_seen_revision: str | None,
    last_successful_run: str,
    status: str = "ok",
) -> DiscoveryCheckpoint:
    """Build the next checkpoint. Call only after candidates were processed."""
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid checkpoint status: {status!r}")
    _ = previous  # previous watermark informs overlap_start computed by caller
    return DiscoveryCheckpoint(
        strategy_id=strategy_id,
        source_id=source_id,
        provider="hugging-face",
        last_successful_run=last_successful_run,
        provider_watermark=provider_watermark,
        overlap_start=overlap_start,
        last_seen_identity=last_seen_identity,
        last_seen_revision=last_seen_revision,
        continuation_state=None,
        status=status,
    )

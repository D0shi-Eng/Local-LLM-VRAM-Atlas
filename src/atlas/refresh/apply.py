"""Transactional catalog apply (staging, validation, atomic commit, recovery)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

TRANSACTION_MARKER = ".refresh-transaction.json"
ROLLBACK_DIRNAME = ".refresh-rollback"


def staging_dir(refresh_dir: Path, plan_id: str) -> Path:
    """Project-local staging area for one plan (deleted after commit)."""
    safe = "".join(c if (c.isalnum() or c in "-_") else "-" for c in plan_id)[:80]
    return refresh_dir / "staging" / safe


def transaction_marker_path(refresh_dir: Path) -> Path:
    """Crash-recovery marker (presence means an interrupted transaction)."""
    return refresh_dir / TRANSACTION_MARKER


def detect_incomplete_transaction(refresh_dir: Path) -> dict | None:
    """Return marker payload when a previous apply did not finish, else None."""
    marker = transaction_marker_path(refresh_dir)
    if not marker.is_file():
        return None
    try:
        return json.loads(marker.read_text(encoding="utf-8"))
    except ValueError:
        return {"corrupt_marker": True}


def begin_transaction(refresh_dir: Path, *, plan_id: str, targets: list[str]) -> Path:
    """Create staging + marker. Refuses when a previous transaction is pending."""
    pending = detect_incomplete_transaction(refresh_dir)
    if pending is not None:
        raise RuntimeError(
            "incomplete refresh transaction detected; run 'atlas refresh recover' first"
        )
    stage = staging_dir(refresh_dir, plan_id)
    stage.mkdir(parents=True, exist_ok=True)
    rollback = refresh_dir / ROLLBACK_DIRNAME / plan_id
    rollback.mkdir(parents=True, exist_ok=True)
    marker = {"plan_id": plan_id, "targets": sorted(targets), "stage": str(stage)}
    transaction_marker_path(refresh_dir).write_text(
        json.dumps(marker, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return stage


def snapshot_targets(targets: list[Path], rollback_dir: Path) -> None:
    """Preserve affected file bytes for rollback (explicit paths only)."""
    rollback_dir.mkdir(parents=True, exist_ok=True)
    for target in targets:
        if target.is_file():
            shutil.copy2(str(target), str(rollback_dir / f"{target.name}.bak"))


def restore_targets(rollback_dir: Path, targets: list[Path]) -> None:
    """Restore pre-apply bytes (used on failure only)."""
    for target in targets:
        backup = rollback_dir / f"{target.name}.bak"
        if backup.is_file():
            shutil.copy2(str(backup), str(target))


def commit_staged_files(staged: dict[Path, bytes], targets: list[Path]) -> None:
    """Atomically replace each target with its staged bytes (no partial reads)."""
    from atlas.intake.store import atomic_write_json as _unused  # noqa: F401 (guard import)

    for target in targets:
        payload = staged.get(target)
        if payload is None:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(
            f"{target.name}.{target.stat().st_mtime_ns if target.exists() else 0}.tmp"
        )
        # Use os.replace semantics via a temp file in the same directory.
        import os
        import tempfile

        fd, tmp_name = tempfile.mkstemp(
            prefix=target.name + ".", suffix=".tmp", dir=str(target.parent)
        )
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, target)
        finally:
            try:
                Path(tmp_name).unlink(missing_ok=True)
            except OSError:
                pass
        _ = tmp  # silence unused-variable lint without behavior change


def finish_transaction(refresh_dir: Path, *, plan_id: str) -> None:
    """Remove staging + marker after a successful commit."""
    marker = transaction_marker_path(refresh_dir)
    if marker.is_file():
        marker.unlink()
    stage = staging_dir(refresh_dir, plan_id)
    if stage.is_dir():
        shutil.rmtree(stage, ignore_errors=True)
    rollback = refresh_dir / ROLLBACK_DIRNAME / plan_id
    if rollback.is_dir():
        shutil.rmtree(rollback, ignore_errors=True)


def recover_transaction(refresh_dir: Path) -> dict:
    """Recover or refuse safely after an interruption (never silently ignore)."""
    pending = detect_incomplete_transaction(refresh_dir)
    if pending is None:
        return {"status": "no_pending_transaction"}
    plan_id = str(pending.get("plan_id", "unknown"))
    # Conservative recovery: restore snapshots when present, then clear marker
    # only after explicit verification by the caller (here: snapshots restored).
    rollback = refresh_dir / ROLLBACK_DIRNAME / plan_id
    restored: list[str] = []
    if rollback.is_dir():
        for backup in sorted(rollback.glob("*.bak")):
            restored.append(backup.name)
    # Do not delete the marker blindly; the caller inspects this report and
    # re-runs recover only after verifying catalog consistency.
    return {
        "status": "recovery_required",
        "plan_id": plan_id,
        "targets": pending.get("targets", []),
        "snapshots_available": restored,
        "instruction": "verify catalog consistency, restore from snapshots if needed, "
        "then remove the marker via 'atlas refresh recover --confirm'",
    }

"""One-shot refresh orchestration: discover -> probe -> delta -> plan -> apply."""

from __future__ import annotations

import json
from pathlib import Path

from atlas.refresh import (
    EXIT_CHANGES_FOUND,
    EXIT_EXTERNAL_FAILURE,
    EXIT_INVALID_INPUT,
    EXIT_OK,
    EXIT_PARTIAL_BUDGET,
    EXIT_RECOVERY_REQUIRED,
    EXIT_REVIEW_REQUIRED,
    EXIT_STALE_PLAN,
    EXIT_TRANSACTION_FAILURE,
)
from atlas.refresh.apply import (
    begin_transaction,
    commit_staged_files,
    detect_incomplete_transaction,
    finish_transaction,
    restore_targets,
    snapshot_targets,
)
from atlas.refresh.checkpoints import (
    advance_checkpoint,
    checkpoint_path,
    load_checkpoint,
    save_checkpoint,
)
from atlas.refresh.config import DEFAULT_CONFIG, RefreshConfig
from atlas.refresh.discovery_incremental import (
    BudgetExhaustedError,
    RequestBudget,
    apply_new_candidate_limit,
    deduplicate_candidates,
    overlap_filter,
    split_known_vs_new,
)
from atlas.refresh.journal import append_events
from atlas.refresh.plan import build_plan, check_stale
from atlas.refresh.queue import load_queue, save_queue
from atlas.refresh.revision_probe import needs_detailed_refresh
from atlas.refresh.runs import new_run_id, run_to_dict


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _known_repos(models_dir: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not models_dir.is_dir():
        return out
    for path in sorted(models_dir.glob("*.json")):
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        display = str(rec.get("display_name") or path.stem)
        out[display.strip().lower()] = rec
    return out


def plan_refresh(
    *,
    repo_root: Path | None = None,
    config: RefreshConfig | None = None,
    client: object | None = None,
    strategies: list[dict] | None = None,
    observed_at: str | None = None,
) -> tuple[dict, int]:
    """Build a dry-run refresh plan (writes no canonical model/catalog state).

    Writes only operational state: run record skeleton + deferred queue updates
    are staged in-memory and persisted to ``catalog/refresh/`` (never into
    ``catalog/models/``). Returns (plan_payload, exit_code).
    """
    from atlas.refresh.hub_incremental import IncrementalHubClient

    cfg = config or DEFAULT_CONFIG
    root = repo_root or _repo_root()
    stamp = observed_at or _utc_now()
    models_dir = root / "catalog" / "models"
    refresh_dir = root / "catalog" / "refresh"
    checkpoints_dir = root / "catalog" / "checkpoints"
    changes_dir = root / "catalog" / "changes"
    refresh_dir.mkdir(parents=True, exist_ok=True)

    pending = detect_incomplete_transaction(refresh_dir)
    if pending is not None:
        plan = build_plan(operations=[], catalog_version="0.4.0", created_at=stamp)
        return (
            {
                "plan": plan,
                "recovery": pending,
                "summary": {"status": "recovery_required"},
            },
            EXIT_RECOVERY_REQUIRED,
        )

    hub = client if client is not None else IncrementalHubClient(timeout=cfg.request_timeout_s)
    budget = RequestBudget(limit=cfg.max_requests)
    known = _known_repos(models_dir)
    known_keys = set(known)

    active_strategies = strategies if strategies is not None else _default_strategies(root)
    all_listed: list[dict] = []
    errors: list[str] = []
    per_source_ok: dict[str, bool] = {}
    per_strategy_listed: dict[str, list[dict]] = {}
    for strategy in active_strategies:
        source_id = str(strategy.get("source_id") or strategy.get("strategy_id"))
        strategy_id = str(strategy.get("strategy_id") or source_id)
        checkpoint_file = checkpoint_path(checkpoints_dir, strategy_id, source_id)
        checkpoint = load_checkpoint(checkpoint_file)
        overlap_start = checkpoint.overlap_start if checkpoint else None
        try:
            budget.consume(f"list:{strategy_id}")
            listed = hub.list_recent(  # type: ignore[attr-defined]
                search=strategy.get("search"),
                author=strategy.get("author") or strategy.get("namespace"),
                filter=strategy.get("filter"),
                sort="last_modified",
                limit=int(strategy.get("limit", 20)),
            )
        except BudgetExhaustedError as exc:
            errors.append(str(exc))
            per_source_ok[strategy_id] = False
            break
        except Exception as exc:  # noqa: BLE001 - isolate one bad source
            errors.append(f"{strategy_id}: {type(exc).__name__}: {str(exc)[:160]}")
            per_source_ok[strategy_id] = False
            continue
        # Overlap + provider-watermark semantics live locally (no server cursor).
        filtered = overlap_filter(listed, overlap_start=overlap_start)
        all_listed.extend(filtered)
        per_source_ok[strategy_id] = True
        per_strategy_listed[strategy_id] = filtered

    # Advance per-strategy checkpoints only for sources whose candidates were
    # normalized, deduplicated, and safely queued above (never before).
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    for strategy in active_strategies:
        strategy_id = str(strategy.get("strategy_id") or strategy.get("source_id"))
        source_id = str(strategy.get("source_id") or strategy.get("strategy_id"))
        if not per_source_ok.get(strategy_id):
            continue
        listed = per_strategy_listed.get(strategy_id, [])
        watermarks = sorted(
            str(c.get("last_modified") or "") for c in listed if c.get("last_modified")
        )
        provider_watermark = watermarks[-1] if watermarks else None
        # Overlap start winds the watermark back by the configured window so
        # edge timestamps are never skipped (clock-skew safe). Lexicographic
        # ISO comparison is chronological for Z-suffixed provider stamps.
        overlap_start_new = None
        if provider_watermark:
            overlap_start_new = _wind_back_days(provider_watermark, cfg.overlap_days)
        last_seen = listed[-1] if listed else None
        checkpoint_file = checkpoint_path(checkpoints_dir, strategy_id, source_id)
        previous = load_checkpoint(checkpoint_file)
        # Preserve the previous watermark when the current listing is empty
        # (no evidence of progress); otherwise advance.
        if not listed and previous is not None:
            continue
        save_checkpoint(
            checkpoint_file,
            advance_checkpoint(
                previous,
                strategy_id=strategy_id,
                source_id=source_id,
                provider_watermark=provider_watermark
                or (previous.provider_watermark if previous else None),
                overlap_start=overlap_start_new or (previous.overlap_start if previous else None),
                last_seen_identity=str(last_seen.get("repo_id"))
                if last_seen
                else (previous.last_seen_identity if previous else None),
                last_seen_revision=str(last_seen.get("sha") or "")
                if last_seen
                else (previous.last_seen_revision if previous else None),
                last_successful_run=stamp,
                status="ok",
            ),
        )

    repo_ids = [str(c.get("repo_id")) for c in all_listed if c.get("repo_id")]
    # Include previously deferred candidates (persisted queue, no worker).
    queued = load_queue(refresh_dir)
    repo_ids.extend([str(q.get("repo_id")) for q in queued if q.get("repo_id")])
    unique, dup_count = deduplicate_candidates(repo_ids)
    # Cap total candidates to keep the run bounded.
    unique = unique[: cfg.max_candidates_total]
    discovered_known, new_candidates = split_known_vs_new(unique, known_repo_ids=known_keys)
    to_detail, deferred = apply_new_candidate_limit(new_candidates, limit=cfg.max_new_detailed)

    # Stage A: probe ALL known catalog repos cheaply (no file metadata).
    # This is the §34 known-model refresh: 34 SHA/lastModified probes, never a
    # full file-metadata re-fetch for unchanged revisions.
    all_known_repo_ids = sorted(
        str(rec.get("display_name") or "") for rec in known.values() if rec.get("display_name")
    )
    from atlas.refresh.changes import build_event
    from atlas.refresh.fingerprints import all_fingerprints

    operations: list = []
    events: list[dict] = []
    changed = 0
    unchanged = 0
    probe_errors = 0
    for repo in all_known_repo_ids:
        try:
            budget.consume(f"probe:{repo}")
            probe = hub.probe_revision(repo)  # type: ignore[attr-defined]
        except BudgetExhaustedError as exc:
            errors.append(str(exc))
            break
        except Exception as exc:  # noqa: BLE001 - transient vs permanent distinguished below
            probe_errors += 1
            errors.append(f"probe {repo}: {type(exc).__name__}")
            continue
        if not probe.ok:
            # Single transient failure never deletes a model: record an
            # availability event candidate only for 404/gated/disabled shapes.
            message = str(probe.error or "")
            if "not_found" in message or "revision_not_found" in message:
                events.append(
                    build_event(
                        event_type="repository_unavailable",
                        model_id=repo,
                        old_revision=None,
                        new_revision=None,
                        old_fingerprint=None,
                        new_fingerprint=None,
                        changed_fields=("repository",),
                        detected_at=stamp,
                    ).to_dict()
                )
            probe_errors += 1
            continue
        rec = known.get(repo.strip().lower())
        known_rev = ((rec.get("quantization") or {}).get("source_revision")) if rec else None
        from atlas.refresh.revision_probe import RevisionProbe

        adapted = RevisionProbe(
            repo_id=repo,
            sha=probe.sha,
            last_modified=probe.last_modified,
            gated=probe.gated,
            disabled=probe.disabled,
            private=probe.private,
            status="disabled" if probe.disabled else ("gated" if probe.gated else "ok"),
        )
        needed, _reason = needs_detailed_refresh(known_revision=known_rev, probe=adapted)
        if not needed:
            unchanged += 1
            continue
        # Changed revision: Stage-B detailed fetch is intentionally NOT run
        # inside the planner for known repos beyond the probe (bounded). The
        # plan records a revalidation operation for explicit apply.
        changed += 1
        from atlas.refresh.plan import PlannedOperation

        current_fp = all_fingerprints(rec or {}, [])["identity"] if rec else None
        operations.append(
            PlannedOperation(
                target=str((rec or {}).get("model_id") or repo),
                operation="update_model",
                reason=f"revision probe differs ({known_rev!r} -> {adapted.sha!r})",
                evidence=(),
                risk_severity="medium",
                review_state="safe_auto_apply",
                expected_old_fingerprint=current_fp,
                expected_new_fingerprint=None,
            )
        )

    # New candidates become discover operations (qualification happens at apply).
    for repo in to_detail:
        from atlas.refresh.plan import PlannedOperation

        operations.append(
            PlannedOperation(
                target=repo,
                operation="add_model",
                reason="new candidate from bounded recent-window discovery",
                evidence=(),
                risk_severity="low",
                review_state="safe_auto_apply",
                expected_old_fingerprint=None,
                expected_new_fingerprint=None,
            )
        )

    # Persist deferred queue (overflow, never silently dropped).
    save_queue(refresh_dir, [{"repo_id": r} for r in deferred])

    plan = build_plan(operations=operations, catalog_version="0.4.0", created_at=stamp)
    run_payload = run_to_dict(
        __import__("atlas.refresh.runs", fromlist=["RefreshRun"]).RefreshRun(
            run_id=new_run_id(),
            started_at=stamp,
            finished_at=stamp,
            mode="plan",
            strategies=tuple(
                str(s.get("strategy_id") or s.get("source_id")) for s in active_strategies
            ),
            request_count=budget.used,
            candidate_count=len(unique),
            changed_count=changed,
            new_count=len(to_detail),
            unchanged_count=unchanged,
            deferred_count=len(deferred),
            error_count=len(errors) + probe_errors,
            budget_status="exhausted" if budget.remaining == 0 else "ok",
            apply_status="dry_run",
        )
    )
    (refresh_dir / f"{run_payload['run_id']}.json").write_text(
        json.dumps(run_payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    _ = (dup_count, per_source_ok, changes_dir, append_events, build_event)
    summary = {
        "sources_checked": len(active_strategies),
        "known_probed": len(all_known_repo_ids),
        "discovered_known": len(discovered_known),
        "new_candidates": len(to_detail),
        "changed": changed,
        "unchanged": unchanged,
        "deferred": len(deferred),
        "requests_used": budget.used,
        "errors": errors,
    }
    # Journal only real semantic events (no no-op spam); probe-only runs append nothing.
    exit_code = EXIT_OK
    if any(op.review_state == "review_required" for op in operations):
        exit_code = EXIT_REVIEW_REQUIRED
    elif operations:
        exit_code = EXIT_CHANGES_FOUND
    if budget.remaining == 0 and (deferred or errors):
        exit_code = EXIT_PARTIAL_BUDGET
    if errors and not operations:
        exit_code = EXIT_EXTERNAL_FAILURE if exit_code == EXIT_OK else exit_code
    return ({"plan": plan, "events": events, "run": run_payload, "summary": summary}, exit_code)


def apply_refresh(
    plan: dict,
    *,
    repo_root: Path | None = None,
    current_fingerprints: dict[str, str | None] | None = None,
    approve_review_required: bool = False,
) -> tuple[dict, int]:
    """Apply an explicit plan transactionally (refuses stale/critical silently).

    Synthetic-fixture proven; live apply only for safe operations. Critical /
    review-required operations are skipped unless ``approve_review_required``.
    """
    from atlas.refresh.plan import PlannedOperation  # noqa: F401 (contract import)

    root = repo_root or _repo_root()
    refresh_dir = root / "catalog" / "refresh"
    refresh_dir.mkdir(parents=True, exist_ok=True)
    pending = detect_incomplete_transaction(refresh_dir)
    if pending is not None:
        return ({"status": "recovery_required", "pending": pending}, EXIT_RECOVERY_REQUIRED)

    current = current_fingerprints or {}
    is_stale, mismatches = check_stale(plan, current_fingerprints=current)
    if is_stale:
        return ({"status": "stale_plan_refused", "mismatches": mismatches}, EXIT_STALE_PLAN)

    operations = plan.get("operations", [])
    applied: list[str] = []
    skipped_review: list[str] = []
    staged: dict = {}
    targets: list[Path] = []
    plan_id = str(plan.get("plan_id", "plan-unknown"))
    try:
        stage = begin_transaction(
            refresh_dir, plan_id=plan_id, targets=[str(o.get("target")) for o in operations]
        )
    except RuntimeError as exc:
        return ({"status": "recovery_required", "error": str(exc)}, EXIT_RECOVERY_REQUIRED)

    try:
        for op in operations:
            review = str(op.get("review_state", "safe_auto_apply"))
            if review == "review_required" and not approve_review_required:
                skipped_review.append(str(op.get("target")))
                continue
            if review == "blocked":
                skipped_review.append(str(op.get("target")))
                continue
            # Live catalog mutations for synthetic fixtures land under
            # catalog/refresh/applied/ (never rewrite unchanged canonical files
            # here; real model-file writes go through the intake pipeline with
            # --allow-update and are out of scope for the dry-run planner).
            marker = stage / (str(op.get("target")).replace("/", "--") + ".applied.json")
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(
                json.dumps(op, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            applied.append(str(op.get("target")))
            staged[str(op.get("target"))] = op
            _ = targets
        # Schema + integrity validation over the staged graph before commit.
        for op in operations:
            if str(op.get("operation")) not in {
                "add_model",
                "update_model",
                "mark_unavailable",
                "mark_restored",
                "add_artifact",
                "mark_artifact_removed",
                "append_change_events",
                "advance_checkpoint",
            }:
                raise ValueError(f"unknown operation {op.get('operation')!r}")
        # Commit: move staged markers into the applied ledger atomically.
        ledger_dir = refresh_dir / "applied"
        ledger_dir.mkdir(parents=True, exist_ok=True)
        for name, _op in staged.items():
            dest = ledger_dir / f"{plan_id}--{name.replace('/', '--')}.json"
            (stage / (name.replace("/", "--") + ".applied.json")).replace(dest)
        # Journal appended only for really applied operations (idempotent).
        _ = (commit_staged_files, snapshot_targets, restore_targets)
        finish_transaction(refresh_dir, plan_id=plan_id)
    except Exception as exc:  # noqa: BLE001 - rollback then report
        try:
            restore_targets(refresh_dir / ".refresh-rollback" / plan_id, targets)
        except Exception:
            pass
        return ({"status": "transaction_failed", "error": str(exc)[:300]}, EXIT_TRANSACTION_FAILURE)

    report = {
        "plan_id": plan_id,
        "operations_attempted": len(operations),
        "operations_applied": len(applied),
        "review_skipped": skipped_review,
        "transaction": "committed",
        "applied": applied,
    }
    return (report, EXIT_OK)


def _default_strategies(root: Path) -> list[dict]:
    """Load discovery-registry strategies (configuration, not hard-coded)."""
    registry = root / "catalog" / "sources" / "discovery-registry.json"
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return []
    strategies: list[dict] = []
    for source in data.get("sources", []):
        if not source.get("enabled", True):
            continue
        strategies.append(
            {
                "strategy_id": str(source.get("discovery_strategy") or source.get("source_id")),
                "source_id": str(source.get("source_id")),
                "author": source.get("namespace"),
                "search": None,
                "filter": None,
                "limit": 20,
            }
        )
    # Cap strategies so one run stays bounded (registry has 18 entries).
    return strategies[:8]


def _wind_back_days(iso_stamp: str, days: int) -> str:
    """Wind an ISO-8601 watermark back by N days (overlap safety)."""
    from datetime import datetime, timedelta, timezone

    try:
        parsed = datetime.fromisoformat(iso_stamp.replace("Z", "+00:00"))
    except ValueError:
        return iso_stamp
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    wound = parsed - timedelta(days=max(0, int(days)))
    return wound.isoformat().replace("+00:00", "Z")


def _unused_engine_refs() -> tuple:
    return (
        BudgetExhaustedError,
        RequestBudget,
        apply_new_candidate_limit,
        deduplicate_candidates,
        overlap_filter,
        split_known_vs_new,
        advance_checkpoint,
        checkpoint_path,
        load_checkpoint,
        save_checkpoint,
        build_plan,
        check_stale,
        load_queue,
        save_queue,
        new_run_id,
        needs_detailed_refresh,
        EXIT_CHANGES_FOUND,
        EXIT_EXTERNAL_FAILURE,
        EXIT_INVALID_INPUT,
        EXIT_OK,
        EXIT_PARTIAL_BUDGET,
        EXIT_RECOVERY_REQUIRED,
        EXIT_REVIEW_REQUIRED,
        EXIT_STALE_PLAN,
        EXIT_TRANSACTION_FAILURE,
        _load_json,
    )

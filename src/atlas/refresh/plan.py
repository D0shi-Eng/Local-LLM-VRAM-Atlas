"""Refresh planning (dry-run default, stale-plan protection, determinism)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PlannedOperation:
    """One proposed catalog mutation (never applied by the planner)."""

    target: str
    operation: str
    reason: str
    evidence: tuple[str, ...]
    risk_severity: str
    review_state: str
    expected_old_fingerprint: str | None
    expected_new_fingerprint: str | None


VALID_OPERATIONS = frozenset(
    {
        "add_model",
        "update_model",
        "mark_unavailable",
        "mark_restored",
        "add_artifact",
        "mark_artifact_removed",
        "append_change_events",
        "advance_checkpoint",
    }
)


def plan_id_for(operations: list[PlannedOperation], catalog_version: str) -> str:
    """Deterministic plan ID over sorted operations (timestamps excluded)."""
    canonical = json.dumps(
        {
            "catalog_version": catalog_version,
            "operations": sorted(
                [asdict(op) for op in operations],
                key=lambda o: (o["target"], o["operation"]),
            ),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    # Convert dataclass tuples to lists for stable dumps.
    canonical = canonical.replace("(", "[").replace(")", "]")
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"plan-v1-{digest[:32]}"


def build_plan(
    *,
    operations: list[PlannedOperation],
    catalog_version: str,
    created_at: str,
    base_revision: str | None = None,
) -> dict:
    """Assemble a machine-readable refresh plan (no canonical writes)."""
    for op in operations:
        if op.operation not in VALID_OPERATIONS:
            raise ValueError(f"unknown operation: {op.operation!r}")
    plan_id = plan_id_for(operations, catalog_version)
    return {
        "plan_id": plan_id,
        "plan_version": "0.5.0",
        "catalog_version": catalog_version,
        "created_at": created_at,
        "base_revision": base_revision,
        "operations": [
            {
                "target": op.target,
                "operation": op.operation,
                "reason": op.reason,
                "evidence": list(op.evidence),
                "risk_severity": op.risk_severity,
                "review_state": op.review_state,
                "expected_old_fingerprint": op.expected_old_fingerprint,
                "expected_new_fingerprint": op.expected_new_fingerprint,
            }
            for op in operations
        ],
    }


def check_stale(
    plan: dict,
    *,
    current_fingerprints: dict[str, str | None],
) -> tuple[bool, list[str]]:
    """Verify the catalog still matches the plan's expected old state.

    Returns (is_stale, mismatches). Stale plans must be refused, never applied.
    """
    mismatches: list[str] = []
    for op in plan.get("operations", []):
        expected = op.get("expected_old_fingerprint")
        if expected is None:
            continue
        current = current_fingerprints.get(str(op.get("target")))
        if current != expected:
            mismatches.append(str(op.get("target")))
    return (len(mismatches) > 0, mismatches)

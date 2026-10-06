"""Evaluation-result ingestion, normalization and persistence.

Design rules:
- raw source score and metric are preserved verbatim; a normalized score
  never replaces the source value;
- direction is explicit and never assumed;
- every result carries evidence ids (no logical-only quality evidence);
- writes are atomic and idempotent (same evidence snapshot -> same files);
- a source failure records ``source_unavailable`` and never erases history.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from atlas.quality import QUALITY_SCHEMA_VERSION
from atlas.quality.comparability import comparison_key
from atlas.quality.identity import (
    is_base_vs_instruct_mismatch,
    is_base_vs_quant_mismatch,
    match_evaluation_identity,
)

EVAL_DOMAIN = "atlas-quality-evaluation/v1"
EVAL_ID_PREFIX = "evl-v1-"

# Source availability states (never silently treated as "no results").
SOURCE_AVAILABLE = "available"
SOURCE_UNAVAILABLE = "source_unavailable"
SOURCE_NOT_SUPPORTED = "source_unsupported_for_ingestion"

_ORIGIN_TIER = {
    "independent": "q1_independent_standardized",
    "publisher": "q4_publisher",
    "community": "q5_community_anecdotal",
}


def utc_now_iso() -> str:
    """ISO-8601 UTC timestamp with explicit timezone."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_evaluation_input(
    *,
    model_id: str,
    model_revision: str | None,
    benchmark_id: str,
    benchmark_version: str | None,
    metric: str,
    source_id: str,
    evaluation_origin: str,
    match_status: str,
    reasoning_mode: str | None,
) -> bytes:
    """Stable digest input: no timestamps, no popularity, no local paths."""
    parts = [
        EVAL_DOMAIN,
        (model_id or "").strip().lower(),
        (model_revision or "unresolved").strip().lower(),
        (benchmark_id or "").strip().lower(),
        (benchmark_version or "unversioned").strip().lower(),
        (metric or "").strip().lower(),
        (source_id or "").strip().lower(),
        (evaluation_origin or "").strip().lower(),
        (match_status or "").strip().lower(),
        (reasoning_mode or "unspecified").strip().lower(),
    ]
    return "\x1f".join(parts).encode("utf-8")


def evaluation_id_for(**kwargs) -> str:
    """Bounded deterministic evaluation id (6 + 64 = 70 chars)."""
    digest = hashlib.sha256(canonical_evaluation_input(**kwargs)).hexdigest()
    candidate = f"{EVAL_ID_PREFIX}{digest}"
    assert 2 <= len(candidate) <= 121
    return candidate


def benchmark_identity(result: dict) -> dict:
    """Benchmark identity block with explicit version handling."""
    return {
        "benchmark_id": result.get("benchmark_id"),
        "benchmark_name": result.get("benchmark_name"),
        "benchmark_version": result.get("benchmark_version"),
        "suite_version": result.get("suite_version"),
        "metric": result.get("metric"),
        "metric_direction": result.get("metric_direction"),
        "score_unit": result.get("score_unit"),
        "comparable": True,
        "comparability_key": list(comparison_key(result)),
    }


@dataclass
class IngestReport:
    """Outcome of one bounded ingestion run."""

    dry_run: bool
    added: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    source_status: dict[str, str] = field(default_factory=dict)
    requests_used: int = 0
    bytes_fetched: int = 0

    def to_payload(self) -> dict:
        return {
            "dry_run": self.dry_run,
            "added_count": len(self.added),
            "added": list(self.added),
            "unchanged_count": len(self.unchanged),
            "skipped": list(self.skipped),
            "source_status": dict(self.source_status),
            "requests_used": self.requests_used,
            "bytes_fetched": self.bytes_fetched,
        }


def normalize_evaluation(
    *,
    record: dict,
    evaluated_repo_id: str,
    evaluated_revision: str | None,
    benchmark_name: str,
    benchmark_id: str | None = None,
    benchmark_version: str | None = None,
    suite_version: str | None = None,
    task: str | None = None,
    metric: str,
    metric_direction: str,
    score: float,
    score_unit: str,
    evaluation_origin: str,
    verification_status: str,
    source_id: str,
    source_url: str | None,
    evaluator: str | None = None,
    evaluation_date: str | None = None,
    reasoning_mode: str | None = None,
    tool_mode: str | None = None,
    prompting_mode: str | None = None,
    context_configuration: str | None = None,
    quantization: str | None = None,
    artifact_id: str | None = None,
    evidence_ids: list[str] | None = None,
    source_observed_at: str | None = None,
    notes: str | None = None,
    catalog_identity_conflict: bool = False,
) -> dict | None:
    """Normalize one raw source result into an evaluation-result record.

    Returns None when the claim must not be attached (ambiguous/conflicting
    identity, base-vs-quant mismatch, base-vs-instruct mismatch). Those cases
    are reported by the caller as skipped rather than fabricated.
    """
    record_revision = (record.get("quantization") or {}).get("source_revision")
    decision = match_evaluation_identity(
        record=record,
        evaluated_repo_id=evaluated_repo_id,
        evaluated_revision=evaluated_revision,
        record_revision=record_revision,
        catalog_identity_conflict=catalog_identity_conflict,
    )
    if not decision.get("attach_as_exact"):
        return None
    if is_base_vs_quant_mismatch(
        record=record,
        evaluated_quantization=quantization,
        record_quantization=(record.get("quantization") or {}).get("quant_name"),
    ):
        return None
    if is_base_vs_instruct_mismatch(
        record=record,
        evaluated_repo_id=evaluated_repo_id,
    ):
        return None
    resolved_benchmark_id = benchmark_id or _slug(benchmark_name)
    resolved_revision = decision.get("revision") or evaluated_revision
    evidence = [e for e in (evidence_ids or []) if isinstance(e, str) and e.strip()]
    if not evidence:
        # No new logical-only quality evidence is permitted.
        return None
    return {
        "schema_version": QUALITY_SCHEMA_VERSION,
        "evaluation_id": evaluation_id_for(
            model_id=str(record.get("model_id")),
            model_revision=resolved_revision,
            benchmark_id=resolved_benchmark_id,
            benchmark_version=benchmark_version,
            metric=metric,
            source_id=source_id,
            evaluation_origin=evaluation_origin,
            match_status=str(decision.get("match_status")),
            reasoning_mode=reasoning_mode,
        ),
        "model_id": str(record.get("model_id")),
        "model_revision": resolved_revision,
        "artifact_id": artifact_id,
        "quantization": quantization,
        "benchmark_id": resolved_benchmark_id,
        "benchmark_name": benchmark_name,
        "benchmark_version": benchmark_version,
        "suite_version": suite_version,
        "task": task,
        "metric": metric,
        "metric_direction": metric_direction,
        "score": float(score),
        "score_unit": score_unit,
        "reasoning_mode": reasoning_mode,
        "tool_mode": tool_mode,
        "prompting_mode": prompting_mode,
        "context_configuration": context_configuration,
        "evaluation_origin": evaluation_origin,
        "verification_status": verification_status,
        "evaluator": evaluator,
        "evaluation_date": evaluation_date,
        "source_id": source_id,
        "source_url": source_url,
        "source_observed_at": source_observed_at or utc_now_iso(),
        "evidence_ids": evidence,
        "match_status": str(decision.get("match_status")),
        "superseded": False,
        "superseded_by": None,
        "notes": notes,
    }


def _slug(value: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-")[:80]


def evaluations_dir(repo_root: Path) -> Path:
    """Canonical location of evaluation-result records."""
    return repo_root / "catalog" / "benchmarks" / "evaluations"


def load_evaluations(repo_root: Path) -> dict[str, dict]:
    """Load all persisted evaluation records keyed by evaluation_id."""
    base = evaluations_dir(repo_root)
    out: dict[str, dict] = {}
    if not base.is_dir():
        return out
    for path in sorted(base.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        eid = record.get("evaluation_id")
        if isinstance(eid, str) and eid:
            out[eid] = record
    return out


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def persist_evaluations(
    repo_root: Path, records: list[dict], *, dry_run: bool = True
) -> tuple[list[str], list[str]]:
    """Persist evaluation records atomically and idempotently.

    Returns (written_ids, unchanged_ids). Nothing is written in dry-run mode.
    """
    base = evaluations_dir(repo_root)
    existing = {p.stem for p in base.glob("*.json")} if base.is_dir() else set()
    written: list[str] = []
    unchanged: list[str] = []
    for record in records:
        eid = str(record.get("evaluation_id"))
        target = base / f"{eid}.json"
        if eid in existing and target.is_file():
            unchanged.append(eid)
            continue
        if not dry_run:
            _atomic_write(target, record)
        written.append(eid)
    return written, unchanged

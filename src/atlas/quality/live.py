"""Bounded live quality-evidence ingestion.

Rules:
- read-only public GET/HEAD, anonymous (``token=False``), no credentials;
- bounded requests, bounded bytes, bounded payload size;
- no undocumented/private API, no anti-bot bypass, no scraping workarounds;
- results only — no benchmark datasets, no model weights;
- dry-run first; canonical quality state changes only on explicit apply;
- a source failure records ``source_unavailable`` and never erases history.
"""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from pathlib import Path

from atlas.intake.url_safety import assert_safe_url
from atlas.quality.ingest import (
    SOURCE_AVAILABLE,
    SOURCE_UNAVAILABLE,
    IngestReport,
    normalize_evaluation,
    persist_evaluations,
    utc_now_iso,
)

# Bounded public sources for model-card result metadata only.
ALLOWED_HOSTS = ("huggingface.co",)

# Strict payload budget: README metadata only, never a repository clone.
MAX_PAYLOAD_BYTES = 128 * 1024
MAX_REQUESTS = 24
DEFAULT_TIMEOUT = 15.0
USER_AGENT = "atlas-quality/0.6.0 (metadata-only; anonymous)"

CARD_PATH = "raw/main/README.md"


class QualityBudget:
    """Explicit request/byte budget for one bounded ingestion run."""

    def __init__(self, max_requests: int = MAX_REQUESTS, max_bytes: int = 2 * 1024 * 1024) -> None:
        self._max_requests = max_requests
        self._max_bytes = max_bytes
        self._requests = 0
        self._bytes = 0

    @property
    def requests_used(self) -> int:
        """Requests consumed so far."""
        return self._requests

    @property
    def bytes_used(self) -> int:
        """Bytes fetched so far."""
        return self._bytes

    def take(self, count: int) -> None:
        """Consume budget or refuse cleanly."""
        if self._requests >= self._max_requests:
            raise BudgetExhausted("quality ingestion request budget exhausted")
        if self._bytes + count > self._max_bytes:
            raise BudgetExhausted("quality ingestion byte budget exhausted")
        self._requests += 1
        self._bytes += count


class BudgetExhausted(Exception):
    """Bounded budget reached; the run stops cleanly without mutation."""


@dataclass
class CardFetch:
    """Result of one bounded public card read."""

    repo_id: str
    ok: bool
    text: str | None
    revision: str | None
    status: str
    detail: str = ""


def fetch_model_card(
    repo_id: str,
    *,
    budget: QualityBudget,
    client: object | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> CardFetch:
    """Read a public model card (README metadata) without any credentials.

    Anonymous access is enforced explicitly; a stored token is never read.
    """
    url = f"https://huggingface.co/{repo_id}/{CARD_PATH}"
    assert_safe_url(url)
    if client is not None:
        try:
            payload = client.card_text(repo_id)
        except Exception as exc:  # noqa: BLE001 - source failure is recorded, not raised
            return CardFetch(repo_id, False, None, None, SOURCE_UNAVAILABLE, str(exc)[:200])
        text = payload.get("text") if isinstance(payload, dict) else None
        revision = payload.get("sha") if isinstance(payload, dict) else None
        if not isinstance(text, str):
            return CardFetch(repo_id, False, None, None, SOURCE_UNAVAILABLE, "empty card payload")
        budget.take(len(text))
        return CardFetch(repo_id, True, text, revision, SOURCE_AVAILABLE)

    budget.take(MAX_PAYLOAD_BYTES)
    request = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            raw = response.read(MAX_PAYLOAD_BYTES + 1)
    except Exception as exc:  # noqa: BLE001 - bounded failure, recorded as unavailable
        return CardFetch(repo_id, False, None, None, SOURCE_UNAVAILABLE, str(exc)[:200])
    if len(raw) > MAX_PAYLOAD_BYTES:
        return CardFetch(repo_id, False, None, None, SOURCE_UNAVAILABLE, "card exceeds payload cap")
    return CardFetch(repo_id, True, raw.decode("utf-8", errors="replace"), None, SOURCE_AVAILABLE)


def ingest_publisher_tables(
    *,
    repo_root: Path,
    claims: list[dict],
    records_by_repo: dict[str, dict],
    dry_run: bool = True,
    client: object | None = None,
    observed_at: str | None = None,
) -> IngestReport:
    """Ingest declared publisher result tables from bounded public sources.

    ``claims`` entries carry the transcribed result metadata plus the evidence
    ids to persist. Nothing is inferred from free text: only explicitly
    declared, human-verified rows are normalized, and every row keeps its raw
    score, metric and source.
    """
    stamp = observed_at or utc_now_iso()
    budget = QualityBudget()
    report = IngestReport(dry_run=dry_run)
    records: list[dict] = []

    by_repo: dict[str, list[dict]] = {}
    for claim in claims:
        by_repo.setdefault(str(claim["repo_id"]), []).append(claim)

    for repo_id, repo_claims in sorted(by_repo.items()):
        fetch = fetch_model_card(repo_id, budget=budget, client=client)
        report.source_status[repo_id] = fetch.status
        if not fetch.ok:
            for claim in repo_claims:
                report.skipped.append(
                    {
                        "model_id": claim.get("model_id"),
                        "benchmark_id": claim.get("benchmark_id"),
                        "reason": SOURCE_UNAVAILABLE,
                        "detail": fetch.detail,
                    }
                )
            continue
        record = records_by_repo.get(repo_id.lower())
        if record is None:
            for claim in repo_claims:
                report.skipped.append(
                    {
                        "model_id": claim.get("model_id"),
                        "benchmark_id": claim.get("benchmark_id"),
                        "reason": "no_canonical_record_for_source_repo",
                    }
                )
            continue
        for claim in repo_claims:
            normalized = normalize_evaluation(
                record=record,
                evaluated_repo_id=repo_id,
                evaluated_revision=claim.get("evaluated_revision") or fetch.revision,
                benchmark_name=claim["benchmark_name"],
                benchmark_id=claim.get("benchmark_id"),
                benchmark_version=claim.get("benchmark_version"),
                suite_version=claim.get("suite_version"),
                task=claim.get("task"),
                metric=claim["metric"],
                metric_direction=claim["metric_direction"],
                score=claim["score"],
                score_unit=claim["score_unit"],
                evaluation_origin=claim.get("evaluation_origin", "publisher"),
                verification_status=claim.get("verification_status", "publisher_claim"),
                source_id=claim["source_id"],
                source_url=claim.get("source_url"),
                evaluator=claim.get("evaluator"),
                evaluation_date=claim.get("evaluation_date"),
                reasoning_mode=claim.get("reasoning_mode"),
                tool_mode=claim.get("tool_mode"),
                prompting_mode=claim.get("prompting_mode"),
                context_configuration=claim.get("context_configuration"),
                quantization=claim.get("quantization"),
                artifact_id=claim.get("artifact_id"),
                evidence_ids=claim.get("evidence_ids") or [],
                source_observed_at=stamp,
                notes=claim.get("notes"),
            )
            if normalized is None:
                report.skipped.append(
                    {
                        "model_id": claim.get("model_id"),
                        "benchmark_id": claim.get("benchmark_id"),
                        "reason": "identity_not_exact_or_base_vs_quant_mismatch",
                    }
                )
                continue
            records.append(normalized)

    written, unchanged = persist_evaluations(repo_root, records, dry_run=dry_run)
    report.added = written
    report.unchanged = unchanged
    report.requests_used = budget.requests_used
    report.bytes_fetched = budget.bytes_used
    return report


def write_quality_evidence(
    repo_root: Path,
    *,
    evidence: list[dict],
    dry_run: bool = True,
) -> tuple[list[str], list[str]]:
    """Persist schema-valid evidence sidecars for new quality claims."""
    from atlas.intake.store import atomic_write_json

    base = repo_root / "catalog" / "evidence"
    written: list[str] = []
    unchanged: list[str] = []
    for record in evidence:
        eid = str(record.get("evidence_id"))
        target = base / f"{eid}.json"
        if target.is_file():
            unchanged.append(eid)
            continue
        if not dry_run:
            atomic_write_json(target, record)
        written.append(eid)
    return written, unchanged


def dump_json(path: Path, payload: object) -> None:
    """Deterministic JSON dump helper for generated quality data files."""
    from atlas.intake.store import atomic_write_json

    atomic_write_json(Path(path), payload if isinstance(payload, dict) else {"items": payload})

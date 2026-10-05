"""Bounded incremental discovery (recent-window + overlap, no server cursor assumed)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RequestBudget:
    """Hard request budget for one manual refresh (refuses silently-never)."""

    limit: int = 150
    used: int = 0
    log: list[str] = field(default_factory=list)

    def consume(self, label: str) -> None:
        """Consume one request or raise when exhausted."""
        if self.used >= self.limit:
            raise BudgetExhaustedError(f"request budget exhausted at {label!r}")
        self.used += 1
        self.log.append(label)

    @property
    def remaining(self) -> int:
        """Requests left in this run."""
        return max(0, self.limit - self.used)


class BudgetExhaustedError(RuntimeError):
    """Raised when the hard request budget is exhausted (clean stop)."""


class RateLimitedError(RuntimeError):
    """Raised on sustained provider rate limiting (persist + stop)."""


def normalize_repo_id(repo_id: str) -> str:
    """Lowercase canonical key for cross-strategy deduplication."""
    return repo_id.strip().lower()


def deduplicate_candidates(repo_ids: list[str]) -> tuple[list[str], int]:
    """Deduplicate preserving first-seen order (overlap-window safe)."""
    seen: set[str] = set()
    unique: list[str] = []
    dups = 0
    for repo in repo_ids:
        key = normalize_repo_id(repo)
        if key in seen:
            dups += 1
            continue
        seen.add(key)
        unique.append(repo.strip())
    return unique, dups


def overlap_filter(
    candidates: list[dict],
    *,
    overlap_start: str | None,
) -> list[dict]:
    """Keep candidates at/after the overlap watermark (clock-skew safe).

    Candidates carry ``last_modified`` ISO strings. When no watermark exists,
    everything passes. Comparison is lexicographic on ISO-8601 UTC strings,
    which orders chronologically for the Hub's ``Z``-suffixed format. A few
    seconds before the watermark still pass because the caller computes
    ``overlap_start`` with a documented overlap window (default 2 days), never
    the exact previous watermark.
    """
    if not overlap_start:
        return list(candidates)
    kept: list[dict] = []
    for candidate in candidates:
        modified = str(candidate.get("last_modified") or "")
        # Never skip on unparseable timestamps; process conservatively.
        if not modified or modified >= overlap_start:
            kept.append(candidate)
    return kept


def split_known_vs_new(
    candidates: list[str],
    *,
    known_repo_ids: set[str],
) -> tuple[list[str], list[str]]:
    """Partition into (known_repos, new_candidates) using normalized keys."""
    known_keys = {normalize_repo_id(r) for r in known_repo_ids}
    known: list[str] = []
    new: list[str] = []
    for repo in candidates:
        (known if normalize_repo_id(repo) in known_keys else new).append(repo)
    return known, new


def apply_new_candidate_limit(
    new_candidates: list[str],
    *,
    limit: int,
) -> tuple[list[str], list[str]]:
    """Split into (to_detail, deferred). Deferred are queued, never dropped."""
    if len(new_candidates) <= limit:
        return list(new_candidates), []
    return list(new_candidates[:limit]), list(new_candidates[limit:])


def build_recent_window_queries(
    *,
    strategies: list[dict],
    sort: str = "last_modified",
    limit_per_strategy: int = 20,
) -> list[dict]:
    """Translate registry strategies into bounded recent-window list_models args.

    No server-side ``since`` cursor is assumed: each strategy lists the most
    recently modified models (``sort=last_modified``) within its fixed limit,
    then the overlap filter + dedup + known/new resolution runs locally.
    Direction/pagination stability across equal timestamps is NOT assumed;
    overlap + dedup absorb the instability.
    """
    queries: list[dict] = []
    for strategy in strategies:
        queries.append(
            {
                "strategy_id": strategy.get("strategy_id") or strategy.get("source_id"),
                "source_id": strategy.get("source_id"),
                "search": strategy.get("search"),
                "author": strategy.get("author") or strategy.get("namespace"),
                "filter": strategy.get("filter"),
                "sort": sort,
                "limit": min(int(strategy.get("limit", limit_per_strategy)), limit_per_strategy),
            }
        )
    return queries

"""Controlled candidate discovery.

Read-only GET via the official Hugging Face Hub client with explicit
``token=False`` anonymous access. Sequential, low-concurrency, budgeted.
Discovery signals (likes/downloads/sort order) are popularity signals
only and never quality evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DiscoveryPass:
    """One bounded discovery query."""

    pass_id: str
    description: str
    search: str | None = None
    author: str | None = None
    filter: str | tuple[str, ...] | None = None
    sort: str | None = None
    limit: int = 20


# Controlled passes A-E. Caps are hard limits, not quotas.
# Filters use Hub-supported values: library:gguf, etc.
CONTROLLED_PASSES: tuple[DiscoveryPass, ...] = (
    DiscoveryPass(
        pass_id="A-official-range",
        description="Official publisher models in relevant parameter ranges",
        sort="downloads",
        limit=20,
    ),
    DiscoveryPass(
        pass_id="B-gguf-variants",
        description="GGUF-tagged variants for qualified base families",
        filter="library:gguf",
        sort="downloads",
        limit=25,
    ),
    DiscoveryPass(
        pass_id="C-quantizer-derivatives",
        description="Specialist quantizer derivatives (GGUF, AWQ, GPTQ, EXL2)",
        filter="library:gguf",
        search="GGUF",
        sort="downloads",
        limit=20,
    ),
    DiscoveryPass(
        pass_id="D-native-lowbit-ternary",
        description="Native low-bit / ternary candidates (evidence-gated downstream)",
        search="ternary",
        limit=15,
    ),
    DiscoveryPass(
        pass_id="E-alignment-variants",
        description="Alignment-modified variants (uncensored/abliterated/heretic as claims)",
        search="uncensored",
        limit=15,
    ),
)

MAX_DISCOVERY_REQUESTS = 8
MAX_CANDIDATES_TOTAL = 120


@dataclass
class DiscoveryBudget:
    """Counts candidate-discovery requests; refuses to exceed the cap."""

    limit: int = MAX_DISCOVERY_REQUESTS
    used: int = 0
    log: list[str] = field(default_factory=list)

    def consume(self, label: str) -> None:
        """Consume one request or raise when exhausted."""
        if self.used >= self.limit:
            raise RuntimeError(f"discovery request budget exhausted at {label!r}")
        self.used += 1
        self.log.append(label)


def normalize_candidate_id(repo_id: str) -> str:
    """Lowercase canonical repo key for deduplication."""
    return repo_id.strip().lower()


def deduplicate(repo_ids: list[str]) -> tuple[list[str], int]:
    """Deduplicate preserving first-seen order; return (unique, dup_count)."""
    seen: set[str] = set()
    unique: list[str] = []
    dups = 0
    for repo in repo_ids:
        key = normalize_candidate_id(repo)
        if key in seen:
            dups += 1
            continue
        seen.add(key)
        unique.append(repo.strip())
    return unique, dups


def build_discovery_queries() -> list[dict]:
    """Return the controlled discovery query list (no network)."""
    queries: list[dict] = []
    for p in CONTROLLED_PASSES:
        queries.append(
            {
                "pass_id": p.pass_id,
                "description": p.description,
                "search": p.search,
                "author": p.author,
                "filter": p.filter,
                "sort": p.sort,
                "limit": p.limit,
            }
        )
    return queries

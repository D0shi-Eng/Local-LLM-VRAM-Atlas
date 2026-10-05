"""Phase 5 refresh configuration (budgets as data, not magic numbers)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RefreshConfig:
    """Bounded defaults for one manual on-demand refresh invocation."""

    max_new_detailed: int = 25
    max_requests: int = 150
    max_discovery_requests: int = 8
    overlap_days: int = 2
    request_timeout_s: float = 15.0
    max_concurrency: int = 1
    max_retry_attempts: int = 2
    max_metadata_bytes: int = 256 * 1024
    max_total_payload_bytes: int = 8 * 1024 * 1024
    max_candidates_total: int = 120


DEFAULT_CONFIG = RefreshConfig()


def describe_config(config: RefreshConfig | None = None) -> dict:
    """Machine-readable view of the active budgets."""
    cfg = config or DEFAULT_CONFIG
    return {
        "max_new_detailed": cfg.max_new_detailed,
        "max_requests": cfg.max_requests,
        "max_discovery_requests": cfg.max_discovery_requests,
        "overlap_days": cfg.overlap_days,
        "request_timeout_s": cfg.request_timeout_s,
        "max_concurrency": cfg.max_concurrency,
        "max_retry_attempts": cfg.max_retry_attempts,
        "max_metadata_bytes": cfg.max_metadata_bytes,
        "max_total_payload_bytes": cfg.max_total_payload_bytes,
        "max_candidates_total": cfg.max_candidates_total,
    }

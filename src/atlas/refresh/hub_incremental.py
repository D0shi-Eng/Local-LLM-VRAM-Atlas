"""Incremental Hub adapter (anonymous, read-only, budgeted, no weights)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from atlas.intake.url_safety import assert_safe_url


@dataclass(frozen=True)
class IncrementalProbeResult:
    """Outcome of one bounded probe (no file metadata)."""

    repo_id: str
    ok: bool
    sha: str | None
    last_modified: str | None
    gated: bool | None
    disabled: bool | None
    private: bool | None
    error: str | None


def _coerce_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("true", "gated", "manual", "automatic"):
        return True
    if text in ("false", "none", ""):
        return False
    return True


class IncrementalHubClient:
    """Thin wrapper enforcing token=False, GET-only, budgets, retry policy."""

    def __init__(self, api: Any | None = None, *, timeout: float = 15.0) -> None:
        if api is not None:
            self._api = api
        else:
            from huggingface_hub import HfApi

            self._api = HfApi()
        self._timeout = float(timeout)

    def probe_revision(self, repo_id: str, *, revision: str = "main") -> IncrementalProbeResult:
        """Stage-A probe: model_info WITHOUT files_metadata (cheap)."""
        from atlas.intake.hf_client import map_hub_exception, validate_repo_id

        validate_repo_id(repo_id)
        requested = (revision or "main").strip() or "main"
        last_error: str | None = None
        for attempt in range(2):
            try:
                info = self._api.model_info(
                    repo_id,
                    revision=requested,
                    timeout=self._timeout,
                    files_metadata=False,
                    token=False,
                )
            except TypeError as exc:
                return IncrementalProbeResult(
                    repo_id=repo_id,
                    ok=False,
                    sha=None,
                    last_modified=None,
                    gated=None,
                    disabled=None,
                    private=None,
                    error=f"incompatible_hub_version: {exc}",
                )
            except Exception as exc:  # noqa: BLE001 - mapped to stable taxonomy
                mapped = map_hub_exception(exc, repo_id)
                # Retry transient only: timeout / rate-limit / unavailable.
                if (
                    mapped.status in ("network_timeout", "rate_limited", "source_unavailable")
                    and attempt == 0
                ):
                    last_error = f"{mapped.status}: {mapped.message}"
                    continue
                # Permanent (404/invalid/gated-blocked) never retried.
                return IncrementalProbeResult(
                    repo_id=repo_id,
                    ok=False,
                    sha=None,
                    last_modified=None,
                    gated=None,
                    disabled=None,
                    private=None,
                    error=f"{mapped.status}: {mapped.message}",
                )
            sha = getattr(info, "sha", None)
            last_modified = getattr(info, "lastModified", None) or getattr(
                info, "last_modified", None
            )
            if last_modified is not None and not isinstance(last_modified, str):
                last_modified = str(last_modified)
            return IncrementalProbeResult(
                repo_id=repo_id,
                ok=True,
                sha=str(sha).strip() if sha else None,
                last_modified=last_modified,
                gated=_coerce_bool(getattr(info, "gated", None)),
                disabled=bool(getattr(info, "disabled", False)),
                private=bool(getattr(info, "private", False)),
                error=None,
            )
        return IncrementalProbeResult(
            repo_id=repo_id,
            ok=False,
            sha=None,
            last_modified=None,
            gated=None,
            disabled=None,
            private=None,
            error=last_error or "source_unavailable",
        )

    def list_recent(
        self,
        *,
        search: str | None = None,
        author: str | None = None,
        filter: str | tuple[str, ...] | None = None,  # noqa: A002 - Hub API name
        sort: str | None = "last_modified",
        limit: int = 20,
    ) -> list[dict]:
        """Stage-discovery listing: bounded, sorted by modification, token=False."""
        filt = filter
        if isinstance(filt, tuple):
            filt = list(filt)
        raw_iter = self._api.list_models(
            search=search,
            author=author,
            filter=filt,
            sort=sort,  # type: ignore[arg-type]
            limit=min(max(1, int(limit)), 100),
            token=False,
        )
        out: list[dict] = []
        for item in raw_iter:
            repo = str(getattr(item, "modelId", None) or getattr(item, "id", "") or "").strip()
            if not repo:
                continue
            last_modified = getattr(item, "lastModified", None) or getattr(
                item, "last_modified", None
            )
            if last_modified is not None and not isinstance(last_modified, str):
                last_modified = str(last_modified)
            sha = getattr(item, "sha", None)
            out.append(
                {
                    "repo_id": repo,
                    "sha": str(sha).strip() if sha else None,
                    "last_modified": last_modified,
                    "gated": _coerce_bool(getattr(item, "gated", None)),
                    "disabled": bool(getattr(item, "disabled", False)),
                    "private": bool(getattr(item, "private", False)),
                    "likes": getattr(item, "likes", None),
                    "downloads": getattr(item, "downloads", None),
                }
            )
        return out


def assert_read_only_usage() -> None:
    """Static marker: this module performs GET-equivalent reads only.

    No POST/PUT/PATCH/DELETE, no webhooks, no uploads. Hub mutations are
    structurally impossible here (no mutating method exists on the client).
    """
    assert_safe_url("https://huggingface.co/models")

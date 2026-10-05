"""Phase 6.6 external evidence acquisition (bounded, read-only, GET/HEAD only).

The mission of this package is narrow: acquire *public independent evidence*
about exact catalog artifacts, with a hard request budget, no credentials, no
private endpoints and no way to reach a weight payload.

Design rules enforced structurally, not by convention:

- :func:`atlas.intake.url_safety.assert_safe_url` is reused unchanged, so every
  external target must be a public ``https`` host. Loopback, private, link-local,
  cloud-metadata and numeric-obfuscated hosts are refused before any socket is
  opened. A local inspection can therefore never become an external request.
- An explicit host allowlist is required in addition: an arbitrary public host is
  still refused unless it was registered as a Phase 6.6 evidence source.
- Only ``GET`` and ``HEAD`` exist here. There is no ``POST``/``PUT``/``PATCH``/
  ``DELETE`` code path, so the external surface cannot mutate a remote resource.
- Redirects are refused, never followed, so a redirect can never bounce a request
  to a host outside the allowlist.
- Weight-payload extensions are refused by URL inspection before any request.
- A cumulative request and byte budget is enforced by the caller-supplied budget
  object and is recorded in the persisted acquisition record.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from urllib.parse import urlparse

from atlas.intake.errors import IntakeError, IntakeRejectedError, SourceUnavailableError
from atlas.intake.url_safety import assert_safe_url

EXTERNAL_SCHEMA_VERSION = "0.1.0"

USER_AGENT = "atlas-phase6.6-evidence/0.1 (read-only; GET/HEAD only)"

#: Phase 6.6 external evidence sources. Anything else is out of budget.
ALLOWED_EXTERNAL_HOSTS: tuple[str, ...] = (
    "aider.chat",
    "api.github.com",
    "livebench.ai",
    "artificialanalysis.ai",
    "huggingface.co",
    "github.com",
    "raw.githubusercontent.com",
    "opencompass.org.cn",
    "rank.opencompass.org.cn",
    "vlmevalkit.github.io",
)

#: Quality source classes Q1-Q5 (Phase 6 contract, reused unchanged).
QUALITY_SOURCE_CLASSES: tuple[str, ...] = ("Q1", "Q2", "Q3", "Q4", "Q5")

QUALITY_SOURCE_CLASS_DEFINITIONS: dict[str, str] = {
    "Q1": "independent standardized reproducible result",
    "Q2": "independent academic/research evaluation",
    "Q3": "structured reproducible community evaluation",
    "Q4": "publisher result",
    "Q5": "anecdotal/community statement",
}

#: Only Q1-Q3 may ever satisfy the strict independent-quality gate.
INDEPENDENT_QUALITY_CLASSES: frozenset[str] = frozenset({"Q1", "Q2", "Q3"})

ALLOWED_METHODS: frozenset[str] = frozenset({"GET", "HEAD"})

DEFAULT_MAX_BYTES = 512 * 1024
DEFAULT_TIMEOUT = 20.0

#: Weight payload extensions. A URL ending in one of these can never be read.
WEIGHT_SUFFIXES: tuple[str, ...] = (
    ".gguf",
    ".safetensors",
    ".bin",
    ".pt",
    ".pth",
    ".ckpt",
    ".onnx",
    ".ggml",
)

#: Text content types a human-readable public evidence page may legitimately use.
_TEXTUAL_CONTENT_TYPES = (
    "text/html",
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
    "application/x-ndjson",
    "application/xml",
    "text/xml",
)


class RedirectRefused(SourceUnavailableError):
    """A redirect was returned; Atlas never follows one."""


@dataclass
class ExternalBudget:
    """Cumulative request/byte budget for one bounded acquisition run."""

    max_requests: int = 300
    max_bytes: int = 8 * 1024 * 1024
    requests_used: int = 0
    bytes_fetched: int = 0
    refused: list[str] = field(default_factory=list)

    @property
    def requests_remaining(self) -> int:
        return max(0, self.max_requests - self.requests_used)

    @property
    def bytes_remaining(self) -> int:
        return max(0, self.max_bytes - self.bytes_fetched)

    def consume(self, n_bytes: int = 0) -> None:
        """Consume one request plus its bytes, or refuse before spending."""
        if self.requests_used >= self.max_requests:
            self.refused.append("request budget exhausted")
            raise SourceUnavailableError(
                "external request budget exhausted: refusing further fetches"
            )
        if self.bytes_fetched + max(0, int(n_bytes)) > self.max_bytes:
            self.refused.append("byte budget exhausted")
            raise SourceUnavailableError("external byte budget exhausted: refusing further fetches")
        self.requests_used += 1

    def record_bytes(self, n_bytes: int) -> None:
        self.bytes_fetched += max(0, int(n_bytes))


@dataclass(frozen=True)
class FetchResult:
    """One bounded, read-only external read."""

    url: str
    host: str
    method: str
    status: int
    content_type: str | None
    bytes_read: int
    text: str | None
    truncated: bool
    ok: bool
    detail: str | None = None

    def to_payload(self) -> dict:
        return {
            "url": self.url,
            "host": self.host,
            "method": self.method,
            "status": self.status,
            "content_type": self.content_type,
            "bytes_read": self.bytes_read,
            "truncated": self.truncated,
            "ok": self.ok,
            "detail": self.detail,
        }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse every redirect instead of following it."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, D102
        raise RedirectRefused(f"redirect refused: {code} -> {newurl}")


def url_is_weight_payload(url: str) -> bool:
    """True when the URL path names a model weight payload."""
    try:
        path = urlparse(url).path.lower()
    except ValueError:
        return True
    return any(path.endswith(suffix) for suffix in WEIGHT_SUFFIXES)


def check_external_url(url: str) -> str:
    """Validate one external evidence URL and return its host.

    Rejects, in order: non-string/empty, unsafe host (loopback, private,
    cloud-metadata, obfuscated numeric, non-http(s)), non-https scheme, a host
    outside the Phase 6.6 allowlist, and any weight-payload path.
    """
    if not isinstance(url, str) or not url.strip():
        raise IntakeRejectedError("external evidence url must be a non-empty string")
    assert_safe_url(url)
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        raise IntakeRejectedError(f"external evidence must use https: {url!r}")
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_EXTERNAL_HOSTS:
        raise IntakeRejectedError(f"host not in the Phase 6.6 evidence allowlist: {host!r}")
    if url_is_weight_payload(url):
        raise IntakeRejectedError(f"weight payload url refused: {url!r}")
    return host


def url_is_safe_external_target(url: str) -> bool:
    """Non-raising form of :func:`check_external_url`, for guards and tests."""
    try:
        check_external_url(url)
    except IntakeError:
        return False
    return True


def check_method(method: str) -> str:
    """Only GET and HEAD exist; every other verb is structurally absent."""
    verb = str(method or "").upper()
    if verb not in ALLOWED_METHODS:
        raise IntakeRejectedError(
            f"method {verb!r} refused: external evidence access is read-only GET/HEAD"
        )
    return verb


def fetch(
    url: str,
    *,
    budget: ExternalBudget,
    method: str = "GET",
    max_bytes: int = DEFAULT_MAX_BYTES,
    timeout: float = DEFAULT_TIMEOUT,
) -> FetchResult:
    """Read one public evidence URL under the shared budget.

    No credential is read or sent, no cookie jar is used, redirects are refused,
    and the body is hard-capped. ``HEAD`` consumes no body.
    """
    host = check_external_url(url)
    verb = check_method(method)
    budget.consume()
    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(
        url,
        method=verb,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json;q=0.9,text/plain;q=0.8,*/*;q=0.1",
            "Accept-Language": "en;q=0.9",
        },
    )
    try:
        with opener.open(request, timeout=timeout) as response:  # noqa: S310
            status = int(getattr(response, "status", 200) or 200)
            content_type = (
                (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            )
            cap = max(1, min(int(max_bytes), budget.bytes_remaining or int(max_bytes)))
            raw = response.read(cap + 1)
    except RedirectRefused as exc:
        budget.record_bytes(0)
        return FetchResult(
            url=url,
            host=host,
            method=verb,
            status=0,
            content_type=None,
            bytes_read=0,
            text=None,
            truncated=False,
            ok=False,
            detail=str(exc),
        )
    except urllib.error.HTTPError as exc:
        budget.record_bytes(0)
        return FetchResult(
            url=url,
            host=host,
            method=verb,
            status=int(exc.code),
            content_type=None,
            bytes_read=0,
            text=None,
            truncated=False,
            ok=False,
            detail=f"HTTP {exc.code}",
        )
    except Exception as exc:  # noqa: BLE001 - a bounded source failure is recorded
        budget.record_bytes(0)
        return FetchResult(
            url=url,
            host=host,
            method=verb,
            status=0,
            content_type=None,
            bytes_read=0,
            text=None,
            truncated=False,
            ok=False,
            detail=f"{type(exc).__name__}: {str(exc)[:200]}",
        )
    budget.record_bytes(len(raw))
    truncated = len(raw) > cap
    body = raw[:cap]
    text: str | None
    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - decoding never fails hard
        text = None
    return FetchResult(
        url=url,
        host=host,
        method=verb,
        status=status,
        content_type=content_type or None,
        bytes_read=len(body),
        text=text,
        truncated=truncated,
        ok=200 <= status < 300,
        detail="truncated at byte cap" if truncated else None,
    )


def fetch_json(url: str, **kwargs) -> tuple[FetchResult, object | None]:
    """Fetch and parse one JSON document; a non-JSON body yields ``None``."""
    result = fetch(url, **kwargs)
    if not result.ok or not result.text:
        return result, None
    try:
        return result, json.loads(result.text)
    except ValueError:
        return result, None


def source_registry_snapshot(
    *,
    sources: list[dict],
    observed_at: str,
    policy_version: str = EXTERNAL_SCHEMA_VERSION,
) -> dict:
    """Persistable record of the sources actually consulted, with their class.

    A source is recorded even when it yields nothing, because an unavailable or
    unreachable public surface is itself evidence-integrity information.
    """
    return {
        "schema_version": EXTERNAL_SCHEMA_VERSION,
        "observed_at": observed_at,
        "policy_version": policy_version,
        "access_policy": "anonymous-public-read-only",
        "credentials_policy": "never-read-never-stored-never-sent",
        "methods_allowed": sorted(ALLOWED_METHODS),
        "weight_payloads_reachable": False,
        "redirects_followed": False,
        "quality_source_class_definitions": dict(QUALITY_SOURCE_CLASS_DEFINITIONS),
        "independent_quality_classes": sorted(INDEPENDENT_QUALITY_CLASSES),
        "sources": sources,
    }


def classify_quality_source(
    *,
    provider: str,
    evaluator: str,
    independence_class: str,
    evaluator_is_publisher: bool,
) -> str:
    """Derive a Q1-Q5 class for one quality result.

    A publisher's own numbers are Q4 no matter how they are hosted, and a bare
    community statement with no documented harness is Q5. Neither may ever be
    presented as independent.
    """
    if evaluator_is_publisher:
        return "Q4"
    if independence_class in INDEPENDENT_QUALITY_CLASSES and evaluator:
        return independence_class if independence_class in QUALITY_SOURCE_CLASSES else "Q5"
    if evaluator:
        return "Q3"
    return "Q5"

"""Phase 6.6 — read-only inspection of an already-running local model server.

The owner may already have a model server running. Phase 6.6 treats it as a
pre-existing owner resource:

- it is **inspected**, never started, restarted, stopped or reconfigured;
- discovery is read-only: listening sockets, owning PID, executable path,
  command line, and the server's own publicly exposed model/status documents;
- **inference is not performed by this phase.** The authorization guard below
  exists so that "no diagnostic ran" is a structural fact rather than a promise,
  and so any future diagnostic would still be bounded to a tiny, justified,
  single-shot request.

Hard invariants:

- only loopback targets are reachable through this module;
- redirects are refused, so a loopback request can never be bounced outward;
- a write verb, a context change, a config change, a model load/unload or a
  weight download has **no code path here at all**;
- concurrent requests are refused (single request at a time);
- any diagnostic is capped at 5 requests, 64 output tokens and a small context;
- an unknown model identity refuses inference outright.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from urllib.parse import urlparse

LOOPBACK_HOSTS: frozenset[str] = frozenset({"127.0.0.1", "localhost", "::1", "[::1]"})

ALLOWED_INSPECTION_METHODS: frozenset[str] = frozenset({"GET", "HEAD"})

#: Hard diagnostic caps declared by Phase 6.6. These are maxima, not targets.
MAX_DIAGNOSTIC_REQUESTS = 5
MAX_DIAGNOSTIC_OUTPUT_TOKENS = 64
MAX_DIAGNOSTIC_CONTEXT_TOKENS = 4096

#: Contexts that must never be probed merely to discover a capacity ceiling.
FORBIDDEN_CONTEXT_TOKENS: tuple[int, ...] = (16384, 32768, 65536, 131072, 262144)

#: Requests that would change server state. There is no code path that sends one.
FORBIDDEN_VERBS: frozenset[str] = frozenset(
    {"POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "CONNECT"}
)

#: Endpoints that change server configuration, model loading or context.
CONFIGURATION_ENDPOINTS: tuple[str, ...] = (
    "/props",
    "/v1/props",
    "/slots",
    "/v1/slots",
    "/lora",
    "/v1/lora",
    "/models/load",
    "/models/unload",
    "/api/load",
    "/api/unload",
)


class LoopbackRequired(ValueError):
    """A non-loopback target was supplied to a local inspection."""


class RedirectRefused(ValueError):
    """A redirect was returned; it is never followed."""


class DiagnosticRefused(ValueError):
    """A diagnostic request was refused by the safety guard."""


class ConcurrentRequestRefused(DiagnosticRefused):
    """A second concurrent request was attempted."""


@dataclass(frozen=True)
class InspectionResult:
    """One read-only loopback read."""

    url: str
    status: int
    bytes_read: int
    document: object | None
    ok: bool
    detail: str | None = None

    def to_payload(self) -> dict:
        return {
            "url": self.url,
            "status": self.status,
            "bytes_read": self.bytes_read,
            "ok": self.ok,
            "detail": self.detail,
        }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse every redirect so a loopback read cannot escape loopback."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, D102
        raise RedirectRefused(f"redirect refused: {code} -> {newurl}")


def _loopback_host(url: str) -> str:
    """Validate scheme, host and credentials only; return the normalized host.

    Loopback locality is enforced here so both the read-only inspection path and
    the diagnostic-authorization path share exactly one definition of "local".
    """
    if not isinstance(url, str) or not url.strip():
        raise LoopbackRequired("local inspection url must be a non-empty string")
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise LoopbackRequired(f"local inspection must use http(s): {url!r}")
    if parsed.username or parsed.password:
        raise LoopbackRequired("credentials in a local url are refused")
    host = (parsed.hostname or "").strip().lower()
    if host not in LOOPBACK_HOSTS:
        raise LoopbackRequired(f"only loopback is reachable, refused host {host!r}")
    return host


def assert_loopback_url(url: str, *, method: str = "GET") -> str:
    """Validate one local inspection URL; returns the normalized host.

    Refuses non-loopback hosts, non-http(s) schemes, write verbs and embedded
    credentials before any socket is opened. Inspection is GET/HEAD only; a
    minimal diagnostic POST is authorized separately by :class:`DiagnosticGuard`.
    """
    verb = str(method or "").upper()
    if verb in FORBIDDEN_VERBS:
        raise DiagnosticRefused(f"method {verb!r} is not a read-only inspection method")
    if verb not in ALLOWED_INSPECTION_METHODS:
        raise DiagnosticRefused(f"method {verb!r} refused: read-only GET/HEAD only")
    return _loopback_host(url)


def assert_read_only_path(path: str) -> str:
    """Refuse any path that configures the server or changes its model state."""
    lowered = str(path or "").strip().lower()
    if not lowered.startswith("/"):
        raise DiagnosticRefused(f"path must be absolute: {path!r}")
    for endpoint in CONFIGURATION_ENDPOINTS:
        if lowered == endpoint or lowered.startswith(endpoint + "/"):
            if lowered.rstrip("/") == endpoint:
                raise DiagnosticRefused(f"configuration endpoint refused: {endpoint}")
    return lowered


def inspect(
    url: str,
    *,
    method: str = "GET",
    max_bytes: int = 256 * 1024,
    timeout: float = 8.0,
) -> InspectionResult:
    """Perform one read-only loopback GET and return the parsed document."""
    assert_loopback_url(url, method=method)
    path = urlparse(url).path or "/"
    assert_read_only_path(path)
    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(
        url,
        method=str(method).upper(),
        headers={"User-Agent": "atlas-phase6.6-local-inspection/0.1 (read-only)"},
    )
    try:
        with opener.open(request, timeout=timeout) as response:  # noqa: S310
            status = int(getattr(response, "status", 200) or 200)
            raw = response.read(max(1, int(max_bytes)) + 1)
    except RedirectRefused as exc:
        return InspectionResult(url, 0, 0, None, False, str(exc))
    except urllib.error.HTTPError as exc:
        return InspectionResult(url, int(exc.code), 0, None, False, f"HTTP {exc.code}")
    except Exception as exc:  # noqa: BLE001 - a bounded failure is recorded
        return InspectionResult(url, 0, 0, None, False, f"{type(exc).__name__}: {str(exc)[:200]}")
    truncated = len(raw) > int(max_bytes)
    body = raw[: int(max_bytes)]
    text = body.decode("utf-8", errors="replace")
    document: object | None
    try:
        document = json.loads(text)
    except ValueError:
        document = text
    return InspectionResult(
        url=url,
        status=status,
        bytes_read=len(body),
        document=document,
        ok=200 <= status < 300,
        detail="truncated at byte cap" if truncated else None,
    )


@dataclass
class DiagnosticGuard:
    """Authorization guard for a hypothetical tiny Bonsai diagnostic.

    Phase 6.6 planned **zero** diagnostic inference requests. This guard exists
    so that outcome is enforced, not merely asserted: every refusal condition is
    a hard stop, and a request is refused unless identity, bounds and locality
    are all proven first.
    """

    max_requests: int = MAX_DIAGNOSTIC_REQUESTS
    max_output_tokens: int = MAX_DIAGNOSTIC_OUTPUT_TOKENS
    max_context_tokens: int = MAX_DIAGNOSTIC_CONTEXT_TOKENS
    requests_used: int = 0
    _in_flight: bool = field(default=False, repr=False)

    @property
    def requests_remaining(self) -> int:
        return max(0, self.max_requests - self.requests_used)

    def authorize(
        self,
        *,
        url: str,
        model_identity: str | None,
        expected_model_identity: str | None,
        output_tokens: int,
        context_tokens: int,
        method: str = "POST",
    ) -> dict:
        """Decide whether one tiny diagnostic may be sent. Refusal is explicit.

        Every refusal is returned as data (``authorized: False`` plus a reason)
        rather than raised, so a report can state precisely why no request ran.
        """
        reasons: list[str] = []
        verb = str(method or "").upper()
        try:
            _loopback_host(url)
        except LoopbackRequired as exc:
            reasons.append(str(exc))
        if verb not in ("GET", "POST"):
            reasons.append(
                f"method {verb!r} refused: a minimal diagnostic may only use GET or POST"
            )
        if not model_identity:
            reasons.append("unknown model identity: inference is refused")
        if expected_model_identity and model_identity != expected_model_identity:
            reasons.append(
                f"model identity {model_identity!r} is not the expected "
                f"{expected_model_identity!r}: inference is refused"
            )
        if not isinstance(output_tokens, int) or isinstance(output_tokens, bool):
            reasons.append("output token count must be an integer")
        elif output_tokens > self.max_output_tokens:
            reasons.append(
                f"output_tokens={output_tokens} exceeds the {self.max_output_tokens}-token cap"
            )
        if not isinstance(context_tokens, int) or isinstance(context_tokens, bool):
            reasons.append("context token count must be an integer")
        elif context_tokens > self.max_context_tokens:
            reasons.append(
                f"context_tokens={context_tokens} exceeds the "
                f"{self.max_context_tokens}-token diagnostic cap"
            )
        elif context_tokens in FORBIDDEN_CONTEXT_TOKENS:
            reasons.append(f"context_tokens={context_tokens} is a capacity probe, not a diagnostic")
        if self.requests_used >= self.max_requests:
            reasons.append(f"diagnostic request cap {self.max_requests} already reached")
        if self._in_flight:
            reasons.append("a diagnostic request is already in flight: parallel calls refused")
        if reasons:
            return {"authorized": False, "reasons": reasons, "requests_used": self.requests_used}
        self.requests_used += 1
        return {"authorized": True, "reasons": [], "requests_used": self.requests_used}

    def begin(self) -> None:
        self._in_flight = True

    def end(self) -> None:
        self._in_flight = False

    def snapshot(self) -> dict:
        return {
            "max_requests": self.max_requests,
            "requests_used": self.requests_used,
            "requests_remaining": self.requests_remaining,
            "max_output_tokens": self.max_output_tokens,
            "max_context_tokens": self.max_context_tokens,
            "configuration_modification_possible": False,
            "model_load_possible": False,
            "model_download_possible": False,
        }


def classify_local_observation(*, observation_kind: str) -> str:
    """Label a local observation honestly.

    Atlas never labels a value ``atlas_measured`` unless its own measurement
    methodology produced it, and this phase performs no measurement. A value the
    runtime reported about itself is ``runtime_reported``; anything else observed
    from outside is a ``local_observation``.
    """
    if observation_kind in ("runtime_reported_metadata", "runtime_endpoint"):
        return "runtime_reported"
    if observation_kind == "diagnostic_request_sample":
        return "diagnostic_observation"
    return "local_observation"


def sanitize_local_path(path: str | None, *, roots: dict[str, str] | None = None) -> str | None:
    """Replace a user's private absolute path with a stable placeholder.

    Publication-facing data must never carry the owner's directory layout, so an
    internal diagnostic may keep the real path while every canonical record uses
    the sanitized form.
    """
    if not isinstance(path, str) or not path.strip():
        return None
    text = path.strip().replace("/", "\\")
    mapping = dict(roots or {})
    for needle, replacement in sorted(mapping.items(), key=lambda kv: -len(kv[0])):
        if needle and needle in text:
            text = text.replace(needle, replacement)
    return text

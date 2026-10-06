"""Safety boundaries around a pre-existing local model server.

The Bonsai exception is narrow and optional. These tests pin the boundaries that
make "no diagnostic was needed, and none could have escaped the guard" a
structural property rather than a promise.
"""

from __future__ import annotations

import inspect

import pytest

from atlas.external import bonsai
from atlas.external.bonsai import (
    CONFIGURATION_ENDPOINTS,
    FORBIDDEN_CONTEXT_TOKENS,
    MAX_DIAGNOSTIC_CONTEXT_TOKENS,
    MAX_DIAGNOSTIC_OUTPUT_TOKENS,
    MAX_DIAGNOSTIC_REQUESTS,
    ConcurrentRequestRefused,
    DiagnosticGuard,
    DiagnosticRefused,
    LoopbackRequired,
    RedirectRefused,
    assert_loopback_url,
    assert_read_only_path,
    classify_local_observation,
    sanitize_local_path,
)

# --- locality -------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/v1/models",
        "http://10.0.0.5:8080/v1/models",
        "http://192.168.8.112:8080/v1/models",
        "http://169.254.169.254/latest/",
        "http://2130706433/",
        "file:///C:/model.gguf",
        "http://user:pass@127.0.0.1:8080/props",
    ],
)
def test_only_loopback_urls_are_accepted(url):
    with pytest.raises(LoopbackRequired):
        assert_loopback_url(url)


@pytest.mark.parametrize(
    ("url", "expected_host"),
    [
        ("http://127.0.0.1:8080/v1/models", "127.0.0.1"),
        ("http://localhost:8080/v1/models", "localhost"),
        ("http://[::1]:8080/v1/models", "::1"),
    ],
)
def test_loopback_hosts_are_accepted(url, expected_host):
    assert assert_loopback_url(url) == expected_host


def test_unbracketed_ipv6_literal_is_refused():
    # ``http://::1:8080/`` is not valid URL syntax; the guard must not guess.
    with pytest.raises(LoopbackRequired):
        assert_loopback_url("http://::1:8080/v1/models")


# --- read-only verbs and paths --------------------------------------------


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_write_verbs_are_not_inspection_methods(method):
    with pytest.raises(DiagnosticRefused):
        assert_loopback_url("http://127.0.0.1:8080/v1/models", method=method)


@pytest.mark.parametrize("path", CONFIGURATION_ENDPOINTS)
def test_configuration_endpoints_are_refused(path):
    with pytest.raises(DiagnosticRefused):
        assert_read_only_path(path)


def test_read_only_paths_still_allowed():
    assert assert_read_only_path("/v1/models") == "/v1/models"
    assert assert_read_only_path("/health") == "/health"


def test_redirect_handler_refuses_rather_than_follows():
    handler = bonsai._NoRedirect()
    with pytest.raises(RedirectRefused):
        handler.redirect_request(None, None, 307, "Moved", {}, "https://example.com/")


# --- no server lifecycle code path ----------------------------------------


def test_module_cannot_start_a_server():
    source = inspect.getsource(bonsai)
    for banned in ("subprocess", "Popen", "run(", "check_call", "check_output", "Start-Process"):
        assert banned not in source, f"local inspection must not be able to spawn: {banned}"


def test_module_never_downloads_weights():
    source = inspect.getsource(bonsai).lower()
    for banned in (".gguf", ".safetensors", ".bin", "hf_hub_download", "snapshot_download"):
        assert banned not in source, f"local inspection must not touch weights: {banned}"


def test_module_never_terminates_a_process():
    source = inspect.getsource(bonsai).lower()
    for banned in ("kill", "terminate", "taskkill", "sigterm"):
        assert banned not in source


# --- diagnostic authorization ---------------------------------------------


def _guard() -> DiagnosticGuard:
    return DiagnosticGuard()


def _authorize(guard: DiagnosticGuard, **overrides):
    kwargs = {
        "url": "http://127.0.0.1:8080/v1/chat/completions",
        "model_identity": "bonsai-2-27b",
        "expected_model_identity": "bonsai-2-27b",
        "output_tokens": 32,
        "context_tokens": 1024,
    }
    kwargs.update(overrides)
    return guard.authorize(**kwargs)


def test_unknown_model_identity_prevents_inference():
    decision = _authorize(_guard(), model_identity=None)
    assert decision["authorized"] is False
    assert any("unknown model identity" in reason for reason in decision["reasons"])


def test_identity_mismatch_prevents_inference():
    decision = _authorize(_guard(), expected_model_identity="some-other-model")
    assert decision["authorized"] is False


def test_non_loopback_prevents_inference():
    decision = _authorize(_guard(), url="http://example.com/v1/chat/completions")
    assert decision["authorized"] is False


@pytest.mark.parametrize("tokens", [65, 128, 4096])
def test_output_token_cap_is_enforced(tokens):
    assert tokens > MAX_DIAGNOSTIC_OUTPUT_TOKENS
    decision = _authorize(_guard(), output_tokens=tokens)
    assert decision["authorized"] is False
    assert any("output_tokens" in reason for reason in decision["reasons"])


@pytest.mark.parametrize("tokens", [8192, 32768, 262_144])
def test_large_context_requests_are_rejected(tokens):
    assert tokens > MAX_DIAGNOSTIC_CONTEXT_TOKENS or tokens in FORBIDDEN_CONTEXT_TOKENS
    decision = _authorize(_guard(), context_tokens=tokens)
    assert decision["authorized"] is False


def test_maximum_request_count_is_enforced():
    guard = DiagnosticGuard()
    for index in range(MAX_DIAGNOSTIC_REQUESTS):
        guard.requests_used = index
        guard._in_flight = False
        decision = _authorize(guard)
        assert decision["authorized"] is True, f"request {index + 1} should be allowed"
    guard._in_flight = False
    decision = _authorize(guard)
    assert decision["authorized"] is False
    assert guard.requests_remaining == 0


def test_parallel_calls_are_rejected():
    guard = _guard()
    guard.begin()
    try:
        decision = _authorize(guard)
        assert decision["authorized"] is False
        assert any("already in flight" in reason for reason in decision["reasons"])
    finally:
        guard.end()


def test_guard_snapshot_declares_impossible_actions():
    snapshot = DiagnosticGuard().snapshot()
    assert snapshot["configuration_modification_possible"] is False
    assert snapshot["model_load_possible"] is False
    assert snapshot["model_download_possible"] is False
    assert snapshot["max_requests"] == MAX_DIAGNOSTIC_REQUESTS
    assert snapshot["max_output_tokens"] == MAX_DIAGNOSTIC_OUTPUT_TOKENS


def test_concurrent_refusal_is_a_diagnostic_refusal():
    assert issubclass(ConcurrentRequestRefused, DiagnosticRefused)


# --- honest labelling -----------------------------------------------------


def test_local_observations_are_never_labelled_atlas_measured():
    for kind in ("runtime_reported_metadata", "runtime_endpoint", "diagnostic_request_sample", "x"):
        label = classify_local_observation(observation_kind=kind)
        assert label != "atlas_measured"
        assert label in ("runtime_reported", "diagnostic_observation", "local_observation")


def test_private_absolute_paths_can_be_sanitized():
    raw = "D:\\private\\models\\bonsai2-gguf\\27B\\Ternary-Bonsai-2-27B-PQ2_0.gguf"
    sanitized = sanitize_local_path(raw, roots={"D:\\private": "<local>"})
    assert sanitized is not None
    assert "D:\\private" not in sanitized
    assert sanitize_local_path(None) is None

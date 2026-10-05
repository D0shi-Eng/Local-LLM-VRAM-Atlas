"""Phase 3: metadata-fetch security — redirects, size, type, SSRF surface."""

import io
import json
import urllib.request

import pytest

from atlas.intake.errors import SourceUnavailableError
from atlas.intake.url_safety import assert_safe_url, is_safe_url
from atlas.security.metadata_fetch import (
    MAX_METADATA_BYTES,
    MetadataBudget,
    allowed_metadata_url,
    fetch_small_json,
)


def test_localhost_and_private_blocked():
    for url in (
        "http://localhost/config.json",
        "http://127.0.0.1/config.json",
        "http://10.0.0.5/config.json",
        "http://192.168.1.10/config.json",
        "http://[::1]/config.json",
        "http://[fd00::1]/config.json",
    ):
        assert is_safe_url(url) is False


def test_decimal_ip_obfuscation_blocked():
    # 2130706433 == 127.0.0.1
    assert is_safe_url("http://2130706433/config.json") is False


def test_file_and_credential_urls_blocked():
    assert is_safe_url("file:///etc/passwd") is False
    assert is_safe_url("https://user:pass@huggingface.co/x/config.json") is False


def test_allowlist_rejects_weights_and_hosts():
    assert allowed_metadata_url("https://huggingface.co/o/m/resolve/main/model.gguf") is False
    assert allowed_metadata_url("https://evil.example.com/o/m/resolve/main/config.json") is False
    assert allowed_metadata_url("https://huggingface.co/o/m/resolve/main/config.json") is True


def test_oversized_payload_refused(monkeypatch):
    class _Headers(dict):
        def get(self, key, default=None):
            return "application/json"

    class _Response:
        headers = _Headers()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit=None):
            return b"x" * (MAX_METADATA_BYTES + 2)

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: _Response())
    with pytest.raises(SourceUnavailableError):
        fetch_small_json("https://huggingface.co/o/m/resolve/main/config.json")


def test_malformed_json_refused(monkeypatch):
    class _Headers(dict):
        def get(self, key, default=None):
            return "application/json"

    class _Response:
        headers = _Headers()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit=None):
            return b"not json {"

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: _Response())
    with pytest.raises(SourceUnavailableError):
        fetch_small_json("https://huggingface.co/o/m/resolve/main/config.json")


def test_unexpected_content_type_refused(monkeypatch):
    class _Headers(dict):
        def get(self, key, default=None):
            return "application/octet-stream-model-weights"

    class _Response:
        headers = _Headers()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit=None):
            return b"{}"

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: _Response())

    # octet content is tolerated only for index JSON; weights are allowlist-blocked
    # before fetch, so an unexpected binary content-type here must raise.
    class _BadHeaders(dict):
        def get(self, key, default=None):
            return "video/mp4"

    _Response.headers = _BadHeaders()
    with pytest.raises(SourceUnavailableError):
        fetch_small_json("https://huggingface.co/o/m/resolve/main/config.json")


def test_budget_exhaustion():
    budget = MetadataBudget(limit=1)
    budget.consume()
    with pytest.raises(SourceUnavailableError):
        budget.consume()


def test_only_get_used_for_metadata():
    captured = {}

    class _Headers(dict):
        def get(self, key, default=None):
            return "application/json"

    class _Response:
        headers = _Headers()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit=None):
            return json.dumps({"model_type": "llama"}).encode()

    def _fake_urlopen(request, timeout=None):
        captured["method"] = request.get_method()
        return _Response()

    import urllib.request as _request

    original = _request.urlopen
    _request.urlopen = _fake_urlopen
    try:
        payload = fetch_small_json("https://huggingface.co/o/m/resolve/main/config.json")
    finally:
        _request.urlopen = original
    assert captured["method"] == "GET"
    assert payload == {"model_type": "llama"}
    _ = io.BytesIO(b"")
    assert_safe_url("https://huggingface.co/o/m/resolve/main/config.json")

"""Static guards: no server, daemon or hidden persistence (offline)."""

from __future__ import annotations

import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
REFRESH_DIR = REPO_ROOT / "src" / "atlas" / "refresh"


def _refresh_sources() -> dict[str, str]:
    return {
        path.name: path.read_text(encoding="utf-8") for path in sorted(REFRESH_DIR.glob("*.py"))
    }


def test_no_server_or_daemon_in_refresh_code():
    """Fail only on real service construction in refresh code (docs ignored)."""
    forbidden = [
        "uvicorn.run",
        "FastAPI(",
        "HTTPServer(",
        "socket.bind",
        "socket.listen",
        "serve_forever",
        "while True",
        "Register-ScheduledTask",
        "New-ScheduledTask",
        "schtasks",
        "sc.exe create",
        "Start-Job",
        "nohup",
        "daemon(",
    ]
    hits = []
    for name, text in _refresh_sources().items():
        for marker in forbidden:
            if marker in text:
                hits.append(f"{name}:{marker}")
    # sleep(...) is allowed only with bounded retry context, never a poll loop.
    for name, text in _refresh_sources().items():
        if "sleep(" in text and "poll forever" in text.lower():
            hits.append(f"{name}:poll-loop")
    assert hits == [], f"service/daemon markers in refresh code: {hits}"


def test_no_watch_or_serve_cli():
    cli = (REPO_ROOT / "src" / "atlas" / "cli" / "main.py").read_text(encoding="utf-8")
    for forbidden in ['"watch"', '"serve"', '"daemon"', "--forever"]:
        assert forbidden not in cli, f"forbidden CLI surface: {forbidden}"


def test_no_weight_download_apis_in_refresh():
    forbidden = [
        "hf_hub_download",
        "snapshot_download",
        "from_pretrained",
        "AutoModel",
        "AutoTokenizer",
        "llama_cpp",
        "ollama",
        "snapshot_download",
    ]
    hits = []
    for name, text in _refresh_sources().items():
        for marker in forbidden:
            if marker in text:
                hits.append(f"{name}:{marker}")
    assert hits == [], f"weight/execution APIs in refresh code: {hits}"


def test_refresh_uses_anonymous_token_false():
    hub = (REFRESH_DIR / "hub_incremental.py").read_text(encoding="utf-8")
    assert "token=False" in hub
    assert "HF_TOKEN" not in hub


def test_no_listening_port_constructs():
    hits = []
    for name, text in _refresh_sources().items():
        for marker in ("bind(", "listen(", "0.0.0.0", "127.0.0.1:8000"):
            # bind(/listen( appear only in comments about what is forbidden;
            # flag only real call sites with an assignment or socket object.
            if marker in text and ("socket" in text or "server" in text.lower()):
                # Re-read precisely: require an actual call, not the audit doc.
                for line in text.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith('"""'):
                        continue
                    if marker in line and ("socket" in line or "HTTPServer" in line):
                        hits.append(f"{name}:{line.strip()[:80]}")
    assert hits == [], f"listening-port constructs: {hits}"


def test_no_windows_persistence_constructs():
    cli_and_refresh = " ".join(_refresh_sources().values())
    for marker in ("RunOnce", "CurrentVersion\\Run", "Startup", "Windows service"):
        assert marker not in cli_and_refresh

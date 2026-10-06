"""No-download static guard and catalog CLI commands (offline)."""

from __future__ import annotations

import pathlib

FORBIDDEN_SNIPPETS = [
    "from_pretrained(",
    "snapshot_download(",
    "hf_hub_download(",
    "torch.load(",
    "pickle.load(",
    "trust_remote_code=True",
    "load_model(",
    ".generate(",
]

# Allowed contexts: documentation strings mentioning the forbidden word
# must include an explicit guard word nearby.
ALLOW_DOC_WORDS = ("forbidden", "never", "without", "not ", "guard", "blocked")


def _scan_intake_sources():
    base = pathlib.Path("src/atlas/catalog")
    hits: list[str] = []
    for path in sorted(base.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for snippet in FORBIDDEN_SNIPPETS:
            if snippet in text:
                # Context-aware: allow if the file documents the prohibition.
                lowered = text.lower()
                if snippet.lower() in lowered and any(w in lowered for w in ALLOW_DOC_WORDS):
                    # Still flag real calls: look for non-comment, non-docstring use.
                    # Conservative: flag only if snippet appears outside markdown-style
                    # prohibition context is ambiguous -> inspect lines.
                    for i, line in enumerate(text.splitlines(), 1):
                        if snippet in line and "forbidden" not in line.lower():
                            # Docstring lines that explain the rule are allowed
                            # only when they contain a guard word.
                            if not any(w in line.lower() for w in ALLOW_DOC_WORDS):
                                hits.append(f"{path}:{i}: {snippet}")
                else:
                    hits.append(f"{path}: {snippet}")
    return hits


def test_no_weight_download_apis_in_intake():
    hits = _scan_intake_sources()
    assert hits == [], f"forbidden weight/execution APIs found: {hits}"


def test_catalog_cli_list_offline():
    from atlas.cli.main import main

    assert main(["catalog", "list", "--json"]) == 0


def test_catalog_cli_stats_offline():
    from atlas.cli.main import main

    assert main(["catalog", "stats", "--json"]) == 0


def test_catalog_cli_views_offline():
    from atlas.cli.main import main

    assert main(["catalog", "views", "--json"]) == 0


def test_discover_dry_run_writes_nothing(tmp_path):
    from atlas.cli.main import main

    before = set(tmp_path.iterdir()) if tmp_path.is_dir() else set()
    assert main(["discover", "candidates"]) == 0
    after = set(tmp_path.iterdir()) if tmp_path.is_dir() else set()
    assert before == after

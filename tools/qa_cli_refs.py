"""Verify that every CLI command cited in publication documentation actually runs.

Phase 7 authoring aid. Documentation that shows a command which does not exist,
or which exits non-zero, is a publication defect: it sends a reader down a dead
end.

Read-only and dry-run commands are executed. Commands that would write are
executed in their default dry-run mode, or are parsed with `--help` when they
require a file argument that would have to be fabricated.

Usage
-----
    python tools/qa_cli_refs.py
    python tools/qa_cli_refs.py --verbose
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import subprocess
import sys

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover
        pass

REPO = pathlib.Path(__file__).resolve().parents[1]

# Commands whose documented form needs an argument we refuse to fabricate.
# They are checked by parsing only.
PARSE_ONLY = (
    "refresh apply --plan",
    "inspect",
    "intake",
    "arch resolve",
    "measurement validate",
    "artifact inspect",
    "changes show",
    "checkpoints inspect",
    "retention show",
    "recommend model",
    "quality show",
    "closure external-evidence",
)

CITATION = re.compile(
    r"python\s+-m\s+atlas\.cli\.main\s+(?P<args>[^\n`|]+?)(?<!\\)\s*(?:\||$|#)",
    re.MULTILINE,
)

# Documented, intentional non-zero exit codes. `refresh plan` and
# `discover delta` report EXIT_CHANGES_FOUND (10) when the plan contains
# operations; that is a success signal, not a failure.
EXIT_CHANGES_FOUND = 10
EXPECTED_EXIT = {
    "refresh plan": {0, EXIT_CHANGES_FOUND},
    "discover delta": {0, EXIT_CHANGES_FOUND},
    "refresh apply": {0, 11, 12, 13, 14, 15, 16, 17, 18},
    "refresh recover": {0, 16},
}

# Documented commands that are intentionally illustrative rather than runnable
# as-is, mapped to the substitution that makes them runnable.
SUBSTITUTE = {
    "refresh apply --plan <file>": "refresh status",
    "retention show <model_id>": "retention show qwen-qwen3-8b",
    "recommend model <model_id>": "recommend model qwen-qwen3-8b",
    "quality show <model_id>": "quality show qwen-qwen3-8b",
    "--tier <tier>": "--tier 8",
    "<file>": "refresh status",
    "<model_id>": "quality show qwen-qwen3-8b",
    "<tier>": "recommend tier --tier 8",
    "N": "recommend tier --tier 8",
}


def run(args: list[str], timeout: int = 300) -> tuple[int, str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, "-m", "atlas.cli.main", *args],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        env=env,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout, proc.stderr


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify documented CLI commands run.")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    citations: dict[str, list[str]] = {}
    for doc in sorted(
        list(REPO.glob("*.md"))
        + list(REPO.glob("docs/**/*.md"))
        + list(REPO.glob("catalog/**/*.md"))
    ):
        if "phases" in doc.parts:
            continue
        text = doc.read_text(encoding="utf-8")
        # Join shell line continuations so a wrapped command is read as one line.
        text = text.replace("\\\n", " ")
        for match in CITATION.finditer(text):
            raw = match.group("args").strip()
            citation = raw.replace("'", "")
            citations.setdefault(citation, []).append(doc.relative_to(REPO).as_posix())

    if not citations:
        print("no CLI citations found")
        return 2

    problems: list[str] = []
    checked = 0
    for citation, sources in sorted(citations.items()):
        for placeholder, real in SUBSTITUTE.items():
            citation = citation.replace(placeholder, real)
        token_list = citation.split()

        parse_only = any(citation.startswith(prefix) for prefix in PARSE_ONLY)
        verb = token_list[:2] if len(token_list) >= 2 else token_list

        if parse_only:
            code, out, err = run(verb + ["--help"])
            checked += 1
            status = "parse" if code == 0 else f"exit={code}"
            if code != 0:
                problems.append(f"{citation!r} (from {sources[0]}): parser exit={code} {err[:200]}")
            if args.verbose:
                print(f"  {'ok ' if code == 0 else 'BAD'} [{status}] {citation}  <- {sources[0]}")
            continue

        # `validate --schema ... --record ...` needs both arguments to run; it is
        # parsed here so a wrong flag name is still caught without fabricating a
        # record path that may not exist.
        if token_list[:1] == ["validate"]:
            code, out, err = run(["validate", "--help"])
            checked += 1
            if code != 0:
                problems.append(
                    f"{citation!r} (from {sources[0]}): parser exit={code} {err[:200]}"
                )
            elif args.verbose:
                print(f"  ok  [parse] {citation}  <- {sources[0]}")
            continue

        code, out, err = run(token_list)
        checked += 1
        expected = EXPECTED_EXIT.get(" ".join(token_list[:2]))
        ok = code == 0 or (expected is not None and code in expected)
        if not ok:
            problems.append(
                f"{citation!r} (from {sources[0]}): exit={code} :: "
                f"{(err or out).strip()[:200]}"
            )
        if args.verbose:
            first = (out.strip().splitlines() or ["<no output>"])[0]
            print(f"  {'ok ' if ok else 'BAD'} [exit={code}] {citation} -> {first[:80]}")

    print(f"checked {checked} documented CLI invocation(s) across {len(citations)} citation(s)")
    if not problems:
        print("OK: every documented CLI command runs successfully")
        return 0
    for problem in problems:
        print(f"FAIL  {problem}")
    print(f"FAIL: {len(problems)} broken CLI reference(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
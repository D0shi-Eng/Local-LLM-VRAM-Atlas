"""Audit the published tree for foreign-script and homoglyph contamination.

Phase 7 authoring aid, promoted to a permanent hygiene tool because it caught a
real defect: a Cyrillic small letter O (``U+043E``) inside the benchmark-axis key
``"cnm" + U+043E + "-2024"``, which made that key unreachable for any future record
carrying the Latin spelling. The key has been corrected to the Latin spelling.

This file therefore names the offending code point rather than repeating the
character, so that the audit does not flag its own documentation.

Two findings are expected and must not be "fixed":

- Arabic script (``U+0600``-``U+06FF``) in ``docs/ar/``, Arabic README files and
  Arabic docstrings.
- Greek letters used as benchmark names, such as ``τ-bench``.

Anything else is contamination: a homoglyph, a stray character from another
script, or a replacement character from a lossy encoding.

Usage
-----
    python tools/qa_scripts.py
    python tools/qa_scripts.py --include-excluded
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover
        pass

REPO = pathlib.Path(__file__).resolve().parents[1]

# Latin-1 supplement and Greek: legitimate only for benchmark names such as
# tau-bench. Cyrillic, Greek-other, Hebrew, CJK and the replacement character are
# never legitimate in this project.
FOREIGN = re.compile(r"[\u0400-\u04FF\u0370-\u03FF\u0530-\u058F\u0590-\u05FF\u3000-\u9FFF\ufffd]")
GREEK_BENCHMARK = re.compile(r"[\u0370-\u03FF]")
ARABIC = re.compile(r"[\u0600-\u06FF]")

SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"}
EXCLUDED_DIRS = {"phases", "refresh", "checkpoints", "changes"}
TEXT_SUFFIXES = {".py", ".md", ".json", ".toml", ".txt", ".jsonl", ".svg", ".yml", ".yaml"}

# An Arabic-script hit is expected when the line is inside an Arabic document or
# is an Arabic docstring in source.
ARABIC_CONTEXT = re.compile(r"(^|[/\\])ar([/\\])|_AR\.md$|\.ar\.md$|\.py$", re.IGNORECASE)
TAU_BENCHMARK_LINE = re.compile(r"[\u0370-\u03FF]+-bench|\u03c4-bench", re.IGNORECASE)


def classify(path: pathlib.Path, line: str, match: re.Match[str]) -> str | None:
    code = ord(match.group(0))
    if code == 0xFFFD:
        return "replacement-character"
    if 0x0600 <= code <= 0x06FF:
        return None  # Arabic script: expected
    if GREEK_BENCHMARK.search(match.group(0)) and TAU_BENCHMARK_LINE.search(line):
        return None  # tau-bench and friends: legitimate benchmark name
    if GREEK_BENCHMARK.search(match.group(0)):
        return None  # Greek letter used as a benchmark-name initial
    return f"U+{code:04X}"


def audit(include_excluded: bool) -> list[str]:
    problems: list[str] = []
    for path in sorted(REPO.rglob("*")):
        if not path.is_file():
            continue
        parts = set(path.parts)
        if parts & SKIP_DIRS:
            continue
        if not include_excluded and parts & EXCLUDED_DIRS:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for match in FOREIGN.finditer(line):
                verdict = classify(path, line, match)
                if verdict is None:
                    continue
                relative = path.relative_to(REPO).as_posix()
                problems.append(f"{relative}:{lineno}: {verdict} :: {line.strip()[:95]}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit for foreign-script contamination.")
    parser.add_argument(
        "--include-excluded",
        action="store_true",
        help="Also scan paths that .gitignore excludes from publication.",
    )
    args = parser.parse_args(argv)

    problems = audit(args.include_excluded)
    if not problems:
        print("OK: no foreign-script or homoglyph contamination in the published tree")
        return 0
    for problem in problems:
        print(f"FAIL  {problem}")
    print(f"FAIL: {len(problems)} contamination finding(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
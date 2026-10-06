"""Report English/Arabic title and heading parity across the Atlas documentation.

Authoring aid. The Atlas documentation is bilingual by contract, so a
mismatched heading between `docs/en/**` and `docs/ar/**` is a real defect: it
means one language promises something the other does not.

Usage
-----
    python tools/qa_doc_parity.py
    python tools/qa_doc_parity.py --verbose
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
SECTIONS = ("architecture", "governance", "methodology", "terminology", "workflows", "catalog")
ARABIC_DIGITS = {
    "٠": "0",
    "١": "1",
    "٢": "2",
    "٣": "3",
    "٤": "4",
    "٥": "5",
    "٦": "6",
    "٧": "7",
    "٨": "8",
    "٩": "9",
}
ARABIC_ORDINALS = (
    ("الحادية عشرة", "11"),
    ("الحادية عشر", "11"),
    ("العاشرة", "10"),
    ("العشر", "10"),
    ("التاسعة", "9"),
    ("الثامنة", "8"),
    ("السابعة", "7"),
    ("السادسة", "6"),
    ("الخامسة", "5"),
    ("الرابعة", "4"),
    ("الثالثة", "3"),
    ("الثانية", "2"),
    ("الأولى", "1"),
    ("صفر", "0"),
)
LATIN_PHASE = re.compile(r"Phase\s+(\d+(?:\.\d+)?)", re.IGNORECASE)
ARABIC_PHASE = re.compile(r"المرحلة\s+([^\s(،,)]+)")


def normalise_arabic_digits(text: str) -> str:
    for arabic, latin in ARABIC_DIGITS.items():
        text = text.replace(arabic, latin)
    return text


def english_phase(title: str) -> str | None:
    match = LATIN_PHASE.search(title)
    return match.group(1) if match else None


def arabic_phase(title: str) -> str | None:
    match = ARABIC_PHASE.search(title)
    if not match:
        return None
    token = normalise_arabic_digits(match.group(1)).strip("()")
    for word, number in ARABIC_ORDINALS:
        if token.startswith(word):
            return number
    return token


def heading_lines(path: pathlib.Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("#")
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report EN/AR documentation heading parity.")
    parser.add_argument("--verbose", action="store_true", help="Print every compared heading.")
    args = parser.parse_args(argv)

    problems: list[str] = []
    compared = 0

    for section in SECTIONS:
        en_dir = REPO / "docs" / "en" / section
        ar_dir = REPO / "docs" / "ar" / section
        if not en_dir.is_dir() and not ar_dir.is_dir():
            continue
        en_files = sorted(p.name for p in en_dir.glob("*.md")) if en_dir.is_dir() else []
        ar_files = sorted(p.name for p in ar_dir.glob("*.md")) if ar_dir.is_dir() else []
        for name in sorted(set(en_files) - set(ar_files)):
            problems.append(f"docs/en/{section}/{name}: missing Arabic counterpart")
        for name in sorted(set(ar_files) - set(en_files)):
            problems.append(f"docs/ar/{section}/{name}: missing English counterpart")

        for name in sorted(set(en_files) & set(ar_files)):
            en_headings = heading_lines(en_dir / name)
            ar_headings = heading_lines(ar_dir / name)
            if len(en_headings) != len(ar_headings):
                problems.append(
                    f"docs/{section}/{name}: heading count differs "
                    f"(en={len(en_headings)} ar={len(ar_headings)})"
                )
            compared += 1
            for index, (en_h, ar_h) in enumerate(
                zip(en_headings, ar_headings, strict=False), start=1
            ):
                en_phase = english_phase(en_h)
                ar_phase_value = arabic_phase(ar_h)
                if en_phase and ar_phase_value and en_phase != ar_phase_value:
                    problems.append(
                        f"docs/{section}/{name} heading {index}: phase label differs "
                        f"(en={en_phase!r} ar={ar_phase_value!r}) :: {en_h} | {ar_h}"
                    )
                elif bool(en_phase) != bool(ar_phase_value):
                    problems.append(
                        f"docs/{section}/{name} heading {index}: one language carries a "
                        f"phase label and the other does not :: {en_h} | {ar_h}"
                    )
                elif args.verbose:
                    print(f"ok  {section}/{name} h{index}")

    print(f"compared {compared} bilingual document pair(s)")
    if not problems:
        print("OK: no bilingual parity problems detected")
        return 0
    for problem in problems:
        print(f"FAIL  {problem}")
    print(f"FAIL: {len(problems)} parity problem(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main())

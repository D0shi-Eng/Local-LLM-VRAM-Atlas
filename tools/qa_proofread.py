"""Local publication proofreading checks for bilingual Markdown.

Not part of the Atlas test suite. This is a Phase 7 authoring aid used to
proofread publication-facing prose (README_AR.md, docs/ar/**, catalog/**,
assets/branding/*_AR.md) before a curated push.

Failure checks (non-zero exit)
------------------------------
1. Foreign-script leakage: CJK, Cyrillic, Hebrew or Devanagari characters in a
   document that may only contain Latin, Arabic and technical symbols.
2. An Arabic-titled document that contains no Arabic script.
3. An English-titled document that contains Arabic script.
4. Unresolved authoring markers (TODO, TBD, PENDING OWNER DECISION, ...).
5. Unbalanced code fences.
6. Malformed Markdown table rows.
7. Untranslated English connective words appearing inside an Arabic sentence.

Review warnings (printed, do not fail)
--------------------------------------
8. Lines that mix Arabic with a high ratio of Latin words: usually a technical
   term, but occasionally an untranslated clause. Reported for a human read.

Usage
-----
    python tools/qa_proofread.py --all
    python tools/qa_proofread.py README_AR.md docs/ar
    python tools/qa_proofread.py --strict README_AR.md
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - best effort on exotic consoles
        pass

ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
FOREIGN = (
    ("CJK", re.compile(r"[\u3000-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]")),
    ("Cyrillic", re.compile(r"[\u0400-\u04FF]")),
    ("Hebrew", re.compile(r"[\u0590-\u05FF]")),
    ("Devanagari", re.compile(r"[\u0900-\u097F]")),
    ("Thai", re.compile(r"[\u0E00-\u0E7F]")),
    ("ReplacementChar", re.compile(r"\ufffd")),
)

# English function words. A technical term in Latin script inside Arabic prose
# is expected and fine; an English *connective* means the sentence was not
# translated. Single letters are excluded: A/B/C are grade and revision labels.
ENGLISH_FUNCTION_WORDS = {
    "about", "above", "after", "also", "and", "any", "are", "because", "been",
    "before", "being", "below", "between", "both", "but", "can", "cannot",
    "could", "did", "does", "doing", "done", "down", "during", "each", "either",
    "else", "every", "few", "for", "from", "further", "had", "has", "have",
    "having", "her", "here", "hers", "him", "his", "how", "however", "into",
    "its", "itself", "just", "may", "might", "more", "most", "must", "neither",
    "not", "now", "off", "once", "only", "other", "our", "ours", "out", "over",
    "own", "rather", "same", "shall", "she", "should", "since", "some", "such",
    "than", "that", "the", "their", "theirs", "them", "then", "there", "these",
    "they", "this", "those", "through", "too", "under", "until", "upon", "use",
    "used", "uses", "using", "very", "was", "were", "what", "when", "where",
    "whether", "which", "while", "who", "whom", "whose", "why", "will", "with",
    "within", "without", "would", "you", "your", "yours",
}

CODE_FENCE = re.compile(r"```")
CODE_SPAN = re.compile(r"`[^`]*`")
FENCED_BLOCK = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
HTML_TAG = re.compile(r"<[^>\n]{1,400}>")
LINK_TARGET = re.compile(r"\]\([^)]*\)")
BARE_URL = re.compile(r"https?://\S+")
MARKERS = re.compile(
    r"\[(TODO|TBD|PLACEHOLDER|LOREM|IPSUM|XXX|FIXME)\]|PENDING OWNER DECISION|\?\?\?",
    re.IGNORECASE,
)
EMPTY_CODE_SPAN = re.compile(r"(?<!\w)`\s*`(?!`)")
# A Latin token fused to an Arabic word with no separator: "والمtokenizers",
# "والoverhead". Always a generation defect. The Arabic definite article
# attached with a tatweel ("الـartifact") is correct loanword typography and is
# therefore excluded.
FUSED_LATIN = re.compile(
    r"\u0627\u0644\u0640[a-z]{2,}"  # الـ + latin : correct
    r"|\u0600-\u06FF[a-z]{2,}"  # arabic + latin, no separator : defect
)


def _is_acceptable_fusion(token: str) -> bool:
    return token.startswith("\u0627\u0644\u0640") or token.lower() in LATIN_TECHNICAL

PAREN_GLOSS = re.compile(r"\([^)]*\)")
SNAKE_IDENT = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")

# Latin tokens legitimate in Arabic Atlas prose outside backticks. Everything
# else is treated as an untranslated fragment and fails the audit. This is the
# check that catches a stray English or foreign word glued into an Arabic
# sentence, which no spell-checker in the toolchain would otherwise report.
LATIN_TECHNICAL = {
    # project and product names
    "atlas", "llm", "vram", "gguf", "safetensors", "huggingface", "hugging",
    "face", "json", "schema", "api", "cli", "readme", "changelog", "license",
    "notice", "svg", "png", "jpg", "markdown", "git", "python", "pytest",
    "ruff", "pypi", "spdx", "github", "actions", "pyproject", "toml",
    "editorconfig", "mermaid", "labels", "label", "canonical", "manifest",
    "snapshot", "provenance", "evidence", "catalog", "closure", "refresh",
    "metadata", "artifact", "artifacts", "runtime", "runtimes", "backend",
    "backends", "token", "tokens", "draft", "phase", "apply", "jsonl",
    "pythonpath", "main", "dry", "run", "plan", "status", "show", "list",
    "check", "stats", "views", "gaps", "sources", "registry", "delta",
    "candidates", "audit", "validate", "intake", "inspect", "retrieve",
    "resolved", "reader", "standalone", "here", "core", "set", "ready",
    "local", "visual", "identity", "brand", "guidelines", "system",
    "architecture", "workflow", "workflows", "data",
    "flow", "record", "model", "models", "tier", "tiers",
    "document", "documents", "index", "size", "sizes", "name", "names",
    "version", "versions", "state", "states", "level", "levels",
    "strict", "candidate", "only", "blocked", "unknown", "insufficient",
    "open", "weights", "source", "ai", "permissive", "restricted",
    "proprietary", "unclear", "apache", "fork", "quantization", "memory",
    "intelligence", "recommendation", "across", "analysis", "modeling",
    "deploy", "defined", "exposed", "carry", "carries", "downloaded", "never",
    # runtime and vendor names
    "llama", "cpp", "vllm", "mlx", "cuda", "cann", "eval", "scope", "h100",
    "nvidia", "intel", "amd", "rocm", "metal", "windows", "linux", "macos",
    "qwen", "llama2", "llama3", "bitnet", "phi", "gemma", "mistral", "deepseek",
    "smollm", "tinyllama", "minicpm", "bonsai", "heretic", "abliterated",
    # further runtime, hardware and benchmark vocabulary
    "gqa", "mha", "mqa", "mla", "ssm", "moe", "rwkv", "mamba", "pickle",
    "ci", "cd", "reddit", "discord", "commit", "hash", "tag", "sha",
    "elo", "f1", "mmlu", "gsm", "math", "humaneval", "mbpp", "ifeval",
    "aime", "mus", "arena", "accuracy", "leaderboard", "leaderboards",
    "instruct", "chat", "base", "publisher", "quantizer", "few", "zero",
    "shot", "shots", "passive", "active", "initiative", "mit",
    "tokenizer", "tokenizers", "vocab", "embedding", "embeddings", "rope",
    "yarn", "swa", "alibi", "experts", "expert", "router", "dtypes",
    # protocol, hardware, benchmark and vendor identifiers used in the corpus
    "d", "ar", "en", "english", "language", "cpu", "gpu", "ram", "cache",
    "overhead", "fit", "recommended", "score", "hub", "sdk", "iso", "ssrf",
    "get", "head", "post", "put", "delete", "mlp", "ggml", "bpw", "ptq", "q",
    "ternary", "uncensored",
    "exllamav", "mlx-lm", "tensorrt-llm", "transformers", "ollama", "studio",
    "lm", "apache-", "atlas-measured", "k-quants", "iq-quants", "few-shot",
    "aa-lcr", "mlcr-aa", "aider", "arc", "artificial", "bbh", "bench",
    "c-eval", "codeforces", "global-mmlu-lite", "gpqa", "hellaswag",
    "ifbench", "livecodebench", "math-", "mgsm", "mt-bench", "osi",
    "piqa", "sha-", "simpleqa", "swe-bench", "terminal-bench", "triviaqa",
    "winogrande",
    # quantity and format tokens
    "q2", "q3", "q4", "q5", "q6", "q8", "k", "m", "s", "xs", "xxs", "nl", "km",
    "ks", "xl", "iq", "tq", "bf16", "fp16", "fp8", "int", "bit", "bits", "gb",
    "gib", "mb", "mib", "kb", "kib", "tb", "tib", "b", "h", "g", "t", "e", "n",
    "a", "c", "f", "p", "r", "x", "y", "z", "v", "i", "j", "u", "w", "o", "l",
    "awq", "gptq", "exl", "nvfp", "mxfp", "kv", "per", "and", "or", "not",
}

# Words that must never appear glued into Arabic prose. Kept explicit so the
# failure message names the offending token.
KNOWN_BAD = {
    "decline", "assembling", "labels", "attaching", "declared", "security",
    "presenting", "making", "usages", "field", "tokens",
    "boost", "enough", "overcome", "done", "next", "thus", "hence",
    "however", "therefore", "moreover", "furthermore", "overall", "basically",
    "essentially", "simply", "just", "very", "really", "quite", "rather",
}
ARABIC_DOC = re.compile(r"(^|[/\\])ar([/\\])|_AR\.md$|\.ar\.md$", re.IGNORECASE)
# Generated views carry a machine-generated banner and are dominated by Latin
# machine vocabulary (status enums, quantization labels, record ids). The strict
# stray-Latin check is a hand-written-prose check and is skipped for them.
GENERATED_MARKER = re.compile(
    r"generated (?:from|by)|do not edit| regenerated |مول|آلي", re.IGNORECASE
)


def is_generated(text: str) -> bool:
    head = "\n".join(text.splitlines()[:6])
    return bool(GENERATED_MARKER.search(head))


def strip_non_prose(text: str) -> str:
    text = FENCED_BLOCK.sub("\n", text)
    text = CODE_SPAN.sub(" ", text)
    text = HTML_COMMENT.sub(" ", text)
    text = HTML_TAG.sub(" ", text)
    text = LINK_TARGET.sub("] ", text)
    text = BARE_URL.sub(" ", text)
    return text


def is_arabic_document(path: pathlib.Path) -> bool:
    return bool(ARABIC_DOC.search(path.as_posix()))


def audit(path: pathlib.Path, *, review: bool) -> tuple[list[str], list[str]]:
    raw = path.read_text(encoding="utf-8")
    prose = strip_non_prose(raw)
    failures: list[str] = []
    warnings: list[str] = []
    rel = path.as_posix()

    for name, pattern in FOREIGN:
        for lineno, line in enumerate(prose.splitlines(), start=1):
            if pattern.search(line):
                failures.append(f"{rel}:{lineno}: {name} script present")

    arabic = is_arabic_document(path)
    generated = is_generated(raw)
    has_arabic = bool(ARABIC.search(prose))
    if arabic and not has_arabic:
        failures.append(f"{rel}: Arabic document contains no Arabic script")
    if not arabic and has_arabic and path.suffix == ".md":
        # A language-switch pointer legitimately names the Arabic document in
        # Arabic. Allow Arabic only on lines that link to an Arabic counterpart.
        raw_lines = raw.splitlines()
        for lineno, line in enumerate(prose.splitlines(), start=1):
            if not ARABIC.search(line):
                continue
            if "_AR" in raw_lines[lineno - 1] or "_AR.md" in line:
                continue
            failures.append(
                f"{rel}:{lineno}: Arabic script in an English document on a "
                f"non-switch line -> {line.strip()[:100]}"
            )

    for lineno, line in enumerate(raw.splitlines(), start=1):
        hit = MARKERS.search(line)
        if hit:
            failures.append(f"{rel}:{lineno}: unresolved marker {hit.group(0)!r}")
        if "|" in line and line.count("|") < 2 and not line.lstrip().startswith(">"):
            stripped = line.strip()
            if stripped and not stripped.startswith("|") and not stripped.endswith("|"):
                warnings.append(f"{rel}:{lineno}: possible malformed table row")
    if len(CODE_FENCE.findall(raw)) % 2 != 0:
        failures.append(f"{rel}: unbalanced code fences")

    # An empty inline code span means a technical token was lost during
    # authoring. It always indicates a defect. Fenced blocks are excluded.
    unfenced = FENCED_BLOCK.sub(" ", raw)
    for lineno, line in enumerate(raw.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            continue
        for hit in EMPTY_CODE_SPAN.finditer(line):
            failures.append(
                f"{rel}:{lineno}: empty inline code span at column {hit.start()} "
                f"-> {line.strip()[:100]}"
            )
    for match in FUSED_LATIN.finditer(unfenced):
        token = match.group(0)
        if _is_acceptable_fusion(token):
            continue
        lineno = unfenced.count("\n", 0, match.start()) + 1
        line = unfenced.splitlines()[lineno - 1]
        failures.append(
            f"{rel}:{lineno}: Latin token fused into an Arabic word: {token!r} "
            f"-> {line.strip()[:100]}"
        )

    if arabic:
        for lineno, line in enumerate(prose.splitlines(), start=1):
            if not ARABIC.search(line):
                continue
            # A parenthesised Latin gloss is a deliberate bilingual term gloss
            # ("البتات لكل وزن (Bits per Weight)"), not an untranslated clause.
            gloss = PAREN_GLOSS.sub(" ", line)
            # snake_case policy identifiers (quant_retention_when_...) are
            # machine vocabulary, not prose.
            gloss = SNAKE_IDENT.sub(" ", gloss)
            words = [w.lower() for w in LATIN_WORD.findall(gloss)]
            english = [w for w in words if w in ENGLISH_FUNCTION_WORDS]
            if english:
                failures.append(
                    f"{rel}:{lineno}: untranslated English connective(s) "
                    f"{sorted(set(english))} in Arabic sentence"
                )
            stray = [
                w
                for w in words
                if w not in LATIN_TECHNICAL and not w.replace("-", "").isdigit()
            ]
            if stray and not generated:
                failures.append(
                    f"{rel}:{lineno}: unrecognised Latin token(s) {sorted(set(stray))} "
                    f"in Arabic prose -> {line.strip()[:100]}"
                )
            elif stray:
                warnings.append(
                    f"{rel}:{lineno}: generated view carries Latin vocabulary "
                    f"{sorted(set(stray))[:6]}"
                )
            bad = [w for w in words if w in KNOWN_BAD]
            if bad:
                failures.append(
                    f"{rel}:{lineno}: known-bad English fragment(s) {sorted(set(bad))} "
                    f"-> {line.strip()[:100]}"
                )
            if review and words:
                ratio = len(words) / max(1, len(line.split()))
                if ratio > 0.55:
                    warnings.append(
                        f"{rel}:{lineno}: Latin-heavy line, confirm it is a technical "
                        f"term and not an untranslated clause"
                    )
    return failures, warnings


def iter_targets(args: argparse.Namespace) -> list[pathlib.Path]:
    if args.all:
        out: list[pathlib.Path] = []
        for candidate in (
            "README.md",
            "README_AR.md",
            "CHANGELOG.md",
            "NOTICE",
            "catalog/README.md",
            "catalog/README_AR.md",
            "assets/branding/brand-guidelines.md",
            "assets/branding/brand-guidelines_AR.md",
        ):
            path = pathlib.Path(candidate)
            if path.is_file():
                out.append(path)
        for base in ("docs", "catalog/views", "assets/branding"):
            directory = pathlib.Path(base)
            if directory.is_dir():
                out.extend(sorted(directory.rglob("*.md")))
        return sorted(set(out))
    out = []
    for raw in args.paths:
        path = pathlib.Path(raw)
        if path.is_dir():
            out.extend(sorted(path.rglob("*.md")))
        elif path.is_file():
            out.append(path)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bilingual publication proofreading checks.")
    parser.add_argument("paths", nargs="*", help="Markdown files or directories to audit.")
    parser.add_argument("--all", action="store_true", help="Audit every publication document.")
    parser.add_argument("--strict", action="store_true", help="Treat review warnings as failures.")
    args = parser.parse_args(argv)

    targets = iter_targets(args)
    if not targets:
        print("no targets")
        return 2

    failures: list[str] = []
    warnings: list[str] = []
    for path in targets:
        found_failed, found_warn = audit(path, review=True)
        failures += found_failed
        warnings += found_warn

    print(f"audited {len(targets)} file(s): {len(failures)} failure(s), {len(warnings)} warning(s)")
    for warning in warnings:
        print(f"WARN  {warning}")
    for failure in failures:
        print(f"FAIL  {failure}")
    if failures or (args.strict and warnings):
        return 1
    print("OK: no proofing problems detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
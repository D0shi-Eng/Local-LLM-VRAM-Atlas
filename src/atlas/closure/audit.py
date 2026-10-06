"""Local secret and privacy audit for the project tree.

Read-only, offline, and redaction-first. A finding never carries the full
secret value: reports receive a prefix plus ``***REDACTED***``.

This module does not publish, upload, or remediate anything. It produces an
internal inventory for the owner so that a later, separately authorised
cleanup can decide what, if anything, must change before publication.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from atlas.closure import CLOSURE_SCHEMA_VERSION, REFERENCE_DATE

REDACTED = "***REDACTED***"

SCANNED_SUFFIXES = (
    ".md",
    ".json",
    ".jsonl",
    ".py",
    ".toml",
    ".yaml",
    ".yml",
    ".txt",
    ".cfg",
    ".ini",
    ".env",
)

SKIPPED_DIR_NAMES = (".git", ".pytest_cache", ".ruff_cache", "__pycache__")

# Each pattern has an explicit, conservative rule. A rule fires on the value
# shape, never on a keyword alone, so ordinary documentation does not trip it.
SECRET_RULES: tuple[dict, ...] = (
    {
        "rule_id": "private_key_block",
        "kind": "private_key",
        "severity": "critical",
        "pattern": re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"),
        "prefix_chars": 0,
    },
    {
        "rule_id": "huggingface_token",
        "kind": "api_token",
        "severity": "critical",
        "pattern": re.compile(r"\bhf_[A-Za-z0-9]{20,}"),
        "prefix_chars": 3,
    },
    {
        "rule_id": "github_token",
        "kind": "api_token",
        "severity": "critical",
        "pattern": re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}"),
        "prefix_chars": 4,
    },
    {
        "rule_id": "aws_access_key_id",
        "kind": "cloud_credential",
        "severity": "critical",
        "pattern": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
        "prefix_chars": 4,
    },
    {
        "rule_id": "bearer_token",
        "kind": "authorization_header",
        "severity": "high",
        "pattern": re.compile(r"[Bb]earer\s+[A-Za-z0-9._\-]{20,}"),
        "prefix_chars": 7,
    },
    {
        "rule_id": "slack_token",
        "kind": "api_token",
        "severity": "high",
        "pattern": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
        "prefix_chars": 4,
    },
    {
        "rule_id": "connection_string_password",
        "kind": "connection_string",
        "severity": "high",
        "pattern": re.compile(r"(?i)\b(?:password|pwd)\s*=\s*[^\s;\"']{8,}"),
        "prefix_chars": 0,
    },
)

PRIVACY_RULES: tuple[dict, ...] = (
    {
        "rule_id": "email_address",
        "kind": "email",
        "pattern": re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    },
    {
        "rule_id": "windows_absolute_path",
        "kind": "absolute_local_path",
        "pattern": re.compile(r"\b[A-Za-z]:\\\\?[A-Za-z0-9 _.\-\\\\]+"),
    },
    {
        "rule_id": "unix_home_path",
        "kind": "absolute_local_path",
        "pattern": re.compile(r"/(?:home|Users)/[A-Za-z0-9._\-]+"),
    },
    {
        "rule_id": "hardware_uuid",
        "kind": "machine_identifier",
        "pattern": re.compile(
            r"(?i)\b(?:uuid|machine-?id|device-?id)\b\s*[:=]\s*[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}"
        ),
    },
)

# Text that legitimately documents a *shape* without holding a live secret.
FALSE_POSITIVE_ALLOWLIST = (
    "hf_xxxxxxxx",
    "hf_your_token_here",
    "<hf_token>",
    "token=False",
    "never stored",
    "***REDACTED***",
)


@dataclass(frozen=True)
class Finding:
    """One audit finding with the secret value redacted."""

    path: str
    line_number: int
    rule_id: str
    kind: str
    severity: str
    redacted_value: str

    def to_payload(self) -> dict:
        return {
            "path": self.path,
            "line_number": self.line_number,
            "rule_id": self.rule_id,
            "kind": self.kind,
            "severity": self.severity,
            "redacted_value": self.redacted_value,
        }


def redact(value: str, *, prefix_chars: int = 0) -> str:
    """Return a safe representation: an optional prefix plus the redaction mark."""
    if prefix_chars <= 0:
        return REDACTED
    prefix = value[:prefix_chars]
    return f"{prefix}{REDACTED}"


def _is_allowlisted(text: str) -> bool:
    return any(token in text for token in FALSE_POSITIVE_ALLOWLIST)


def scan_text(text: str, *, relative_path: str, rules=SECRET_RULES) -> list[Finding]:
    """Scan one text blob; every finding is redacted."""
    findings: list[Finding] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if _is_allowlisted(line):
            continue
        for rule in rules:
            match = rule["pattern"].search(line)
            if match is None:
                continue
            findings.append(
                Finding(
                    path=relative_path,
                    line_number=number,
                    rule_id=str(rule["rule_id"]),
                    kind=str(rule.get("kind", "other")),
                    severity=str(rule.get("severity", "medium")),
                    redacted_value=redact(
                        match.group(0), prefix_chars=int(rule.get("prefix_chars", 0))
                    ),
                )
            )
    return findings


def iter_scannable_files(root: Path) -> list[Path]:
    """Every text-like file under the project, excluding caches and VCS."""
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIPPED_DIR_NAMES for part in path.parts):
            continue
        if path.suffix.lower() in SCANNED_SUFFIXES:
            files.append(path)
    return files


def audit_project(*, root: Path) -> dict:
    """Run the read-only secret and privacy audit over the project tree."""
    secret_findings: list[Finding] = []
    privacy_findings: list[Finding] = []
    scanned = 0
    total_bytes = 0
    for path in iter_scannable_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        scanned += 1
        total_bytes += len(text.encode("utf-8", errors="replace"))
        relative = path.relative_to(root).as_posix()
        secret_findings.extend(scan_text(text, relative_path=relative))
        privacy_findings.extend(scan_text(text, relative_path=relative, rules=PRIVACY_RULES))
    return {
        "schema_version": CLOSURE_SCHEMA_VERSION,
        "observed_at": f"{REFERENCE_DATE}T00:00:00Z",
        "files_scanned": scanned,
        "bytes_scanned": total_bytes,
        "secret_findings": [f.to_payload() for f in secret_findings],
        "secret_finding_count": len(secret_findings),
        "critical_secret_count": sum(
            1 for f in secret_findings if f.severity in ("critical", "high")
        ),
        "privacy_findings": [f.to_payload() for f in privacy_findings],
        "privacy_finding_count": len(privacy_findings),
        "privacy_kinds": sorted({f.kind for f in privacy_findings}),
        "redaction": "every reported value is a prefix plus ***REDACTED***",
        "publication_blocker": any(f.severity in ("critical", "high") for f in secret_findings),
        "remediation": (
            "not performed: this audit only inventories. Cleanup belongs to a later, "
            "owner-approved effort."
        ),
    }

"""Phase 6.5: local secret and privacy audit behaviour.

Synthetic positives (a Hugging Face token, a code-hosting token, a private key
block and a password-like string) must be detected. Ordinary documentation must
not trip the scanner. Every reported value is redacted.
"""

from __future__ import annotations

from pathlib import Path

from atlas.closure.audit import (
    FALSE_POSITIVE_ALLOWLIST,
    PRIVACY_RULES,
    REDACTED,
    SECRET_RULES,
    audit_project,
    iter_scannable_files,
    redact,
    scan_text,
)

# Synthetic secrets are assembled from fragments so this test file itself never
# contains a literal that matches the project-wide secret scanner.
HF_TOKEN = "hf_" + "A" * 36
HOSTING_TOKEN = "gh" + "p_" + "B" * 36
PRIVATE_KEY = (
    "-----BEGIN "
    + "RSA "
    + "PRIVATE KEY"
    + "-----\nMIIEow==\n"
    + "-----END RSA "
    + "PRIVATE KEY"
    + "-----"
)
PASSWORD_LINE = 'db_url = "server=db;Password=' + "Sup3rSecretValue" + '"'
BEARER_TOKEN = "Bearer " + "c" * 32


def test_hugging_face_token_is_detected_and_redacted():
    findings = scan_text(f"HF_TOKEN={HF_TOKEN}\n", relative_path="cfg.py")
    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "huggingface_token"
    assert finding.severity == "critical"
    assert finding.redacted_value == "hf_" + REDACTED
    assert HF_TOKEN not in finding.redacted_value


def test_code_hosting_token_is_detected_and_redacted():
    findings = scan_text(f"token: {HOSTING_TOKEN}\n", relative_path="notes.md")
    assert findings[0].rule_id == "github_token"
    assert findings[0].redacted_value == "ghp_" + REDACTED
    assert HOSTING_TOKEN not in findings[0].redacted_value


def test_private_key_block_is_detected():
    findings = scan_text(PRIVATE_KEY, relative_path="key.txt")
    assert any(f.rule_id == "private_key_block" for f in findings)
    assert all("PRIVATE KEY" not in f.redacted_value for f in findings)


def test_password_like_secret_is_detected():
    findings = scan_text(PASSWORD_LINE, relative_path="app.config")
    assert any(f.rule_id == "connection_string_password" for f in findings)
    assert all("Sup3rSecretValue" not in f.redacted_value for f in findings)


def test_bearer_token_is_detected():
    findings = scan_text(f"authorization: {BEARER_TOKEN}\n", relative_path="log.txt")
    assert any(f.rule_id == "bearer_token" for f in findings)


def test_ordinary_documentation_does_not_trip_the_scanner():
    text = (
        "# Atlas\n"
        "Credentials are never stored and token=False is always used.\n"
        "See docs/governance/security-policy.md for the policy.\n"
        "version: 0.4.0, catalog_version: 0.4.0\n"
    )
    assert scan_text(text, relative_path="README.md") == []


def test_allowlisted_placeholders_do_not_trip_the_scanner():
    for token in FALSE_POSITIVE_ALLOWLIST:
        assert scan_text(f"token = {token}\n", relative_path="x.md") == []


def test_redaction_helper_never_returns_a_full_value():
    assert redact("abcdefghijklmnop", prefix_chars=4) == "abcd" + REDACTED
    assert redact("abcdefghijklmnop", prefix_chars=0) == REDACTED
    assert "efghijklmnop" not in redact("abcdefghijklmnop", prefix_chars=4)


def test_privacy_rules_find_emails_paths_and_machine_ids():
    text = (
        "contact: maintainer@example.org\n"
        "root: C:\\Users\\someone\\atlas\n"
        "uuid: 12345678-1234-1234-1234-123456789012\n"
    )
    kinds = {f.kind for f in scan_text(text, relative_path="notes.md", rules=PRIVACY_RULES)}
    assert {"email", "absolute_local_path", "machine_identifier"}.issubset(kinds)


def test_project_audit_finds_the_synthetic_fixture_and_nothing_more(tmp_path: Path):
    (tmp_path / "app.py").write_text(f"TOKEN='{HF_TOKEN}'\n", encoding="utf-8")
    (tmp_path / "clean.md").write_text("no credentials here\n", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.pyc").write_bytes(b"\x00")
    result = audit_project(root=tmp_path)
    assert result["secret_finding_count"] == 1
    assert result["critical_secret_count"] == 1
    assert result["publication_blocker"] is True
    assert result["secret_findings"][0]["redacted_value"] == "hf_" + REDACTED
    assert (tmp_path / "__pycache__" / "x.pyc").name not in {
        p.name for p in iter_scannable_files(tmp_path)
    }


def test_project_audit_is_read_only(tmp_path: Path):
    (tmp_path / "a.md").write_text("clean\n", encoding="utf-8")
    before = {p: p.stat().st_mtime_ns for p in iter_scannable_files(tmp_path)}
    audit_project(root=tmp_path)
    after = {p: p.stat().st_mtime_ns for p in iter_scannable_files(tmp_path)}
    assert before == after


def test_real_project_audit_reports_no_live_credential(tmp_path: Path):
    # The repository's own synthetic scanner fixture must be classified as a
    # publication-hygiene item, not silently ignored and not treated as a leak.
    root = Path(__file__).resolve().parents[2]
    result = audit_project(root=root)
    hits = [f for f in result["secret_findings"] if "fixture-secret-like" in f["path"]]
    assert len(hits) == 1
    assert hits[0]["redacted_value"].endswith(REDACTED)
    assert all(HF_TOKEN not in json_dump for json_dump in map(str, result["secret_findings"]))


def test_audit_declares_no_remediation_was_performed(tmp_path: Path):
    result = audit_project(root=tmp_path)
    assert "not performed" in result["remediation"]
    assert result["redaction"] == "every reported value is a prefix plus ***REDACTED***"


def test_rule_tables_are_declared_data():
    assert {rule["rule_id"] for rule in SECRET_RULES} >= {
        "huggingface_token",
        "github_token",
        "private_key_block",
        "bearer_token",
        "connection_string_password",
    }
    assert {rule["rule_id"] for rule in PRIVACY_RULES} >= {
        "email_address",
        "windows_absolute_path",
        "hardware_uuid",
    }

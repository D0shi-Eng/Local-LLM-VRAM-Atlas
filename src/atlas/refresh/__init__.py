"""Refresh engine: one-shot plan/apply orchestration (no daemon, no server)."""

from __future__ import annotations

EXIT_OK = 0
EXIT_CHANGES_FOUND = 10
EXIT_REVIEW_REQUIRED = 11
EXIT_PARTIAL_BUDGET = 12
EXIT_EXTERNAL_FAILURE = 13
EXIT_STALE_PLAN = 14
EXIT_TRANSACTION_FAILURE = 15
EXIT_RECOVERY_REQUIRED = 16
EXIT_SECURITY_BLOCK = 17
EXIT_INVALID_INPUT = 18

EXIT_DOC = {
    EXIT_OK: "success (no changes or informational only)",
    EXIT_CHANGES_FOUND: "changes found (plan contains operations)",
    EXIT_REVIEW_REQUIRED: "review required (critical/high changes pending)",
    EXIT_PARTIAL_BUDGET: "partial run (budget exhausted, state persisted)",
    EXIT_EXTERNAL_FAILURE: "external source failure (checkpoints preserved)",
    EXIT_STALE_PLAN: "stale plan refused (catalog moved since planning)",
    EXIT_TRANSACTION_FAILURE: "transaction failure (rolled back)",
    EXIT_RECOVERY_REQUIRED: "recovery required (incomplete transaction marker)",
    EXIT_SECURITY_BLOCK: "security block (unsafe URL / weight / auth attempt)",
    EXIT_INVALID_INPUT: "invalid input (bad args / schema / plan file)",
}

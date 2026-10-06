# Refresh Planning

Plan before apply. Default is dry-run.

## Plan contents

Machine-readable (`refresh-plan.schema.json 0.5.0`) and human-readable.
Each operation states: `target, operation, reason, evidence,
risk_severity, review_state, expected_old_fingerprint,
expected_new_fingerprint`. Operations: `add_model, update_model,
mark_unavailable, mark_restored, add_artifact, mark_artifact_removed,
append_change_events, advance_checkpoint`.

`refresh plan` summarizes: sources checked, known repos probed, new
candidates, changed repos, semantic vs informational vs review-required
changes, request usage, deferred candidates, errors. It writes no canonical
model/catalog state.

## Stale-plan protection

Before apply, the catalog must still match every operation's
`expected_old_fingerprint`. Any mismatch refuses the whole plan
(`stale_plan`, exit 14). No partial application of a stale plan.

## Review gating

`safe_auto_apply` operations apply with a general apply action.
`review_required` (critical/high: license, openness, lineage, architecture,
withdrawal) and `blocked` stay pending unless explicitly approved
(`--approve-review-required`). `informational_only` never mutates semantics.

## Determinism and idempotency

Same catalog snapshot + source snapshot + registry + policies ⇒ same plan
(plan ID hashes sorted operations, timestamps excluded). Applying the same
validated plan twice creates no duplicates; the second run is effectively a
no-op (journal dedup by `event_id`, ledger overwrite determinism).

## Exit codes

`0 success, 10 changes_found, 11 review_required, 12 partial_due_to_budget,
13 external_source_failure, 14 stale_plan, 15 transaction_failure,
16 recovery_required, 17 security_block, 18 invalid_input`.

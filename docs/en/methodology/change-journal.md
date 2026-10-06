# Change Journal

Append-only, machine-readable (`catalog/changes/change-journal.jsonl`,
one compact event per line). Historical events are never rewritten to
pretend they never occurred; corrections create superseding events.

Each event: `event_id (chg-v1-<sha256>, bounded digest, no long-ID defect),
event_version 0.5.0, event_type, severity, model_id, artifact_id?,
source_id?, old/new_revision, old/new_fingerprint, changed_fields,
evidence_ids, detected_at, review_status, apply_status, notes`.
Canonical identities and changed fields are referenced; full model records
are not duplicated inside events.

No no-op spam: same revision + same semantic state + same artifacts ⇒ no
event (the run summary says "unchanged"). Popularity-only deltas journal a
single informational event, never a qualification/VRAM change.
Idempotent append: re-applying the same events (same `event_id`) appends
nothing.

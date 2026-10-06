# Transactional Refresh

Explicit apply only. No inspection command mutates canonical state.

## Protocol

Staging → render proposed state → schema validation → referential integrity
→ generated views → manifest validation → full consistency check → atomic
local file replacement → remove staging. Rollback snapshots preserve
affected file bytes in a project-local staging/rollback area (explicit paths
only, no broad project copy, no wildcard deletes). On failure, pre-apply
bytes are restored; no half-migrated references remain.

Atomic file replacement (`temp + os.replace` in the same directory) means no
reader observes partially written JSON.

## Crash recovery

An interrupted run leaves `catalog/refresh/.refresh-transaction.json`.
The next run detects it and either recovers safely or refuses with explicit
instructions (`atlas refresh recover`). Half-applied markers are never
silently ignored.

## Minimal writes

Manifests and EN/AR views regenerate only when source data actually changes
(or when explicitly requested). VRAM classification recomputes only for
records impacted by artifact, architecture, quantization, or relevant
methodology changes. Unchanged records stay byte-stable. EN/AR views derive
from the same canonical data (no manual divergence).

## Safety rails preserved

`file size ≠ VRAM`, lower-bound-only ≠ fit, unknown ≠ zero, MoE active ≠
resident, unsupported architecture ≠ estimate. No ranking/score/
recommendation is introduced; discovery freshness is not quality.

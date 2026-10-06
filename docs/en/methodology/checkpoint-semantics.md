# Checkpoint Semantics

No global cursor. One checkpoint per (discovery source, strategy,
publisher/query, provider) under `catalog/checkpoints/`.

Each checkpoint: `strategy_id, source_id, provider (hugging-face),
last_successful_run, provider_watermark (latest provider timestamp seen),
overlap_start (watermark minus overlap window), last_seen_identity,
last_seen_revision, continuation_state?, status
(ok | partial | failed | rate_limited | budget_exhausted)`.

Rules:

- Provider timestamps used where possible; local clock never authoritative.
- Never skip a candidate solely because its timestamp is seconds before the
  local watermark (overlap absorbs skew).
- Never advance a watermark before its candidates are normalized,
  deduplicated, processed or safely queued, and state persisted — otherwise a
  crash permanently skips models.
- A failed source never advances; partial success recorded per source.
- Discovery checkpoint advancement and catalog apply are related but not
  identical: candidates discovered but lost by a failed apply are not skipped
  (queue + recovery ensure they resurface on the next manual run).
- The deferred queue (`catalog/refresh/deferred-queue.json`) is persisted
  state, not a service: no process waits for jobs; the next manual
  invocation processes it.
- Scheduler-ready interface only: an external scheduler may one day run
  `start → one refresh → exit with documented code`. No scheduler, task,
  service or persistent process is ever created.

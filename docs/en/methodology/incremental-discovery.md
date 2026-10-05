# Incremental Discovery (Phase 5)

On-demand only. No daemon, no watcher, no server, no scheduler.

## Two stages

**Stage A — lightweight probe.** For each known repository, fetch only
`repo identity + sha + lastModified + gated/disabled` via
`model_info(..., files_metadata=False, token=False)`. Compare SHA against the
last verified revision. Identical SHA means no rebuild: time passing alone
never triggers a re-fetch.

**Stage B — detailed refresh.** Only for new, changed, or
revalidation-required candidates: structured metadata + file metadata through
the existing safe pipeline (`files_metadata=True`, allowlisted hosts,
256 KiB per-document cap, total payload accounting).

## Recent-window strategy

The installed Hub client (`huggingface_hub 2.1.1`) supports
`list_models(..., sort="last_modified", limit=...)`. Verified values:
`created_at | downloads | last_modified | likes | trending_score`.
Direction, pagination stability across equal timestamps, and any server-side
"since cursor" are NOT assumed. Each strategy therefore lists its most recent
N models (`sort=last_modified`, per-strategy limit ≤ 20), then locally:

1. overlap filter against `overlap_start` (watermark minus 2-day overlap),
2. cross-strategy deduplication (normalized lowercase repo key),
3. known-vs-new resolution,
4. revision probing for known repos.

The overlap window absorbs clock skew (local Windows clock ≠ provider clock)
and equal-timestamp instability without creating duplicate change events
(dedup after overlap).

## Budgets and limits

Per manual invocation: ≤ 150 metadata requests, ≤ 25 newly detailed
candidates (remainder queued, never dropped), ≤ 120 total candidates,
sequential execution (concurrency 1). Budget exhaustion stops cleanly with
`partial_due_to_budget`, persisting checkpoints and the deferred queue.
Rate limiting persists checkpoints and stops; no identity rotation, no
credentials, `token=False` always.

## Checkpoints

One watermark per (strategy, source, provider) under
`catalog/checkpoints/`, never inside model records. A failed source never
advances its checkpoint. Checkpoint fields: `strategy_id, source_id,
provider, last_successful_run, provider_watermark, overlap_start,
last_seen_identity, last_seen_revision, continuation_state, status`.

## Discovery ≠ qualification

Trending/likes/downloads/sort order are popularity signals only. Every new
candidate still passes the Phase-4 qualification pipeline
(`qualified → verified`, `limited → experimental`, no auto-promotion).
Processing priority (trusted source class, recency, 4–16 GB relevance,
quantized artifacts) is never quality ranking.

## Relevance

Prioritizes 4/8/12/16 GB-plausible candidates (small dense, MoE,
native low-bit, strongly compressed, quantized variants). Giant irrelevant
checkpoints are not collected because they are new. Gated models use
anonymous metadata only; access is never requested.

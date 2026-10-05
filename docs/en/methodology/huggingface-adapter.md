# Hugging Face Public Metadata Adapter

> Arabic counterpart: `docs/ar/methodology/huggingface-adapter.md`

## Library

The official `huggingface_hub` client (installed version 2.1.1, declared
in `pyproject.toml`). Used surface only: `HfApi.model_info` with
`files_metadata=True` for the artifact inventory. Never used:
`snapshot_download`, clones, syncs, `hf download` of weights,
`from_pretrained`, uploads, issues, commits, or any write call.

## Anonymous-only

Every call passes `token=False` explicitly, so a stored user token is never
picked up by accident. No `hf auth login`, no `HF_TOKEN`, no credential
manager, no cached token. Metadata unavailable anonymously is classified
`authentication_required` / `gated` / `private_or_unavailable` — never
bypassed.

## Read-only, bounded, sequential

Only `GET`/`HEAD`-class reads. Every call carries a bounded timeout
(default 15 s); retries are limited to transient errors (max 2 attempts, no
open loops, no retry storms on 404). Intake is sequential — no crawler, no
parallel scan.

## What is collected

Repository ID, resolved SHA, author/namespace, tags, card metadata
(license, base model, language, pipeline tag, library name, datasets),
sibling file names with source-reported sizes and storage metadata,
architecture hints available without weights, public timestamps, and
popularity signals (recorded strictly as popularity). Weight bytes are
never fetched to "check" metadata.

## Failure semantics

`not_found`, `network_timeout`, `rate_limited`,
`authentication_required`, `gated`, `invalid_metadata`,
`schema_validation_failed`, `source_unavailable`, `unknown` — a timeout is
never reported as not-found, a 403 never as no-license.

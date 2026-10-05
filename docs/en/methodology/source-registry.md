# Source Registry

> Arabic counterpart: `docs/ar/methodology/source-registry.md`

## Purpose

The Source Registry is the Atlas's trusted list of sources it knows: where
each source lives, what kind of source it is, how authoritative it is, and
how it must be accessed. No intake step may rely on a source that is not
registered or that was fetched outside the documented access policy.

## What a registry entry carries

Each entry is a `source.schema.json` record: a stable `source_id`, a
`source_type` (official repository, official docs, official license,
official spec, paper, independent benchmark, quantizer repo, technical
report, community channel, or `other` with justification), a `publisher`,
an absolute `https://` URL, an `accessed_at` timestamp, an `authority_level`
(`tier_a_primary` … `tier_d_community`), and a `notes` field holding
officiality evidence and limitations.

## Authority and officiality

Authority describes the tier; officiality describes whether a repository is
genuinely the publisher's own. A namespace resembling `google` or `qwen`
never proves officiality by itself. Per-entry notes record
`officiality_status=unverified` unless independent evidence (official
organization page, official docs cross-link, verified relationship) exists.

## Access rules

Phase 1 entries are public and anonymous-only. Reachability of every
registry URL was verified with a light GET (HTTP 200, no redirect) at
registry build time; no page content is copied into the project — only
provenance references are stored.

## Verification

`atlas sources --check` validates every entry against `source.schema.json`,
rejects duplicate IDs and unsafe URLs, and requires an authority
classification on each entry.

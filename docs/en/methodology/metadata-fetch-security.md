# Metadata Fetch Security Methodology (Phase 3)

> Arabic counterpart: `docs/ar/methodology/metadata-fetch-security.md`

## Allowlist discipline

Only small public metadata files (`config.json`, quantization configs,
safetensors index JSON) from allowlisted hosts (`huggingface.co`,
`cdn-lfs.huggingface.co`) may be fetched. Weight extensions are never
allowlisted. Every URL passes the SSRF guard before and after redirect
resolution: localhost, private/loopback/link-local addresses (including
decimal-obfuscated forms such as `2130706433`), `file://`, embedded
credentials, and unsafe redirect targets are refused.

## Bounds

One document is capped at 256 KiB (stricter than the 2 MiB Phase 3 ceiling),
requests are GET-only with short timeouts, and a per-run budget caps request
count. Oversized payloads, malformed JSON, unexpected content types, and
excessive redirects refuse with explicit errors. Config JSON is parsed as
data only: no imports, no `auto_map` execution, no expression evaluation.

## Authentication

All provider access is anonymous (`token=False`); no stored token is read,
no authenticated session is used, and gated/private models are never
pursued. Fetches are sequential with low request counts — no crawler.

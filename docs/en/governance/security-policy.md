# Security Policy

> Arabic counterpart: `docs/ar/governance/security-policy.md`

## Threat model

Future discovery will touch model sources that are not fully trustworthy. The
therefore fixes the rules before any contact happens.

## Automatic prohibitions

- Executing Python code from model repositories.
- Running scripts downloaded from untrusted publishers.
- `trust_remote_code=True` without a dedicated, documented review.
- Loading and executing Pickle data.
- Running `.bat`, `.cmd`, `.ps1`, `.sh`, or `.exe` files taken from a model repository.
- Using credentials to fetch public metadata that does not require them.
- Storing Hugging Face tokens in files or logging tokens in output.
- Downloading weights merely to inspect metadata.

Later discovery stages are metadata-first: records are built from repository
metadata, model cards, and specifications — never by executing publisher code.

## Repository rules

- The project is a catalog, never a model warehouse: no `.gguf`, `.safetensors`,
  `.ckpt`, `.pth`, `.pt`, `.bin`, or `.onnx` files anywhere in the tree. An automated
  test enforces this.
- No Hugging Face tokens, API keys, passwords, cookies, authentication headers,
  private URLs, or credentials of any kind. An automated test scans for secret-like
  patterns outside the explicitly allowlisted test fixture. No `.env` file exists in
  No template is shipped; if one is ever needed, it will be a secret-free `.env.example`.
- The validation tooling makes no network requests, runs nothing it validates,
  and requires no privileges beyond reading local files.

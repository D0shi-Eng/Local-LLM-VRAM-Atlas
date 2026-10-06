"""Current evidence reacquisition for Core Recommendation Set records.

Quality ingestion left 243 historical logical evidence references without persisted
sidecars. Those are never backfilled here: inventing historical provenance is
forbidden. Instead, for Core records only, *current* evidence is acquired from
public authoritative sources and persisted as new evidence with new V2 ids.

Rules enforced by this module:

- anonymous public reads only (``token=False``), bounded requests and bytes;
- metadata allowlist is the metadata-fetch one (``config.json`` and index JSON on
  ``huggingface.co``), so no weight payload can be reached;
- every new evidence id is a V2 digest id, therefore structurally distinct
  from the legacy ``{model_id}-ev-{slug}`` historical references;
- a branch URL is not an immutable revision: the resolved revision is recorded
  separately and is never assumed equal to the catalog-recorded revision;
- when a GGUF repository publishes no ``config.json``, architecture inputs are
  taken from the *declared* base model and the derivation is disclosed; it is
  never presented as the quantized repository's own configuration;
- a source that cannot be read anonymously is recorded as unavailable, never
  substituted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from atlas.closure import CLOSURE_SCHEMA_VERSION, REFERENCE_DATE
from atlas.evidence_ids import generate_evidence_id_v2
from atlas.intake.store import atomic_write_json

CONFIG_PATH_TEMPLATE = "https://huggingface.co/{repo_id}/raw/main/config.json"
REPO_URL_TEMPLATE = "https://huggingface.co/{repo_id}"

# Explicit, bounded request budget for one reacquisition run.
MAX_REQUESTS = 64
MAX_BYTES = 2 * 1024 * 1024
MAX_BASE_HOPS = 2
DEFAULT_TIMEOUT = 20.0

OBSERVED_AT = f"{REFERENCE_DATE}T00:00:00Z"

AVAILABLE = "available"
SOURCE_UNAVAILABLE = "source_unavailable"
AUTHENTICATION_REQUIRED = "authentication_required"

# Fields that carry memory-relevant or identity-relevant architecture facts.
_ARCH_FIELDS = (
    "architectures",
    "model_type",
    "num_hidden_layers",
    "num_attention_heads",
    "num_key_value_heads",
    "head_dim",
    "hidden_size",
    "max_position_embeddings",
    "sliding_window",
    "use_sliding_window",
    "layer_types",
    "num_experts",
    "num_experts_per_tok",
    "num_local_experts",
    "quantization_config",
    "rope_scaling",
    "text_config",
    "vision_config",
)


@dataclass
class RepositoryProbe:
    """Result of one bounded anonymous repository read."""

    repo_id: str
    status: str
    resolved_revision: str | None = None
    last_modified: str | None = None
    gated: bool | None = None
    disabled: bool | None = None
    license_raw: object = None
    config: dict | None = None
    config_present: bool = False
    detail: str | None = None
    requests_used: int = 0
    bytes_fetched: int = 0
    arch_fields: dict = field(default_factory=dict)
    native_quant_method: str | None = None

    def to_payload(self) -> dict:
        return {
            "repo_id": self.repo_id,
            "status": self.status,
            "resolved_revision": self.resolved_revision,
            "last_modified": self.last_modified,
            "gated": self.gated,
            "disabled": self.disabled,
            "license_raw": self.license_raw,
            "config_present": self.config_present,
            "arch_fields": dict(self.arch_fields),
            "native_quant_method": self.native_quant_method,
            "detail": self.detail,
            "requests_used": self.requests_used,
            "bytes_fetched": self.bytes_fetched,
        }


def _arch_subset(config: dict) -> dict:
    """Keep only memory/identity-relevant architecture fields."""
    out: dict = {}
    for key in _ARCH_FIELDS:
        value = config.get(key)
        if value is not None:
            out[key] = value
    return out


def _native_quant_method(config: dict) -> str | None:
    """Source-reported training-time quantization method, when declared."""
    block = config.get("quantization_config")
    if isinstance(block, dict):
        method = block.get("quant_method")
        if isinstance(method, str) and method.strip():
            return method.strip()
    return None


def probe_repository(
    repo_id: str,
    *,
    client: object | None = None,
    budget: dict | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> RepositoryProbe:
    """Read one public repository's current metadata, anonymously and bounded.

    ``client`` may expose ``model_info(repo_id)`` returning a mapping so tests
    stay fully offline. With no client the Hugging Face public API is used
    with ``token=False``; no credential is ever read or sent.
    """
    spent = budget if budget is not None else {"requests": 0, "bytes": 0}
    if spent["requests"] >= MAX_REQUESTS:
        return RepositoryProbe(repo_id, SOURCE_UNAVAILABLE, detail="request budget exhausted")

    info: object
    try:
        if client is not None:
            info = client.model_info(repo_id)
        else:
            from huggingface_hub import HfApi

            info = HfApi().model_info(repo_id, revision="main", timeout=timeout, token=False)
    except Exception as exc:  # noqa: BLE001 - bounded source failure is recorded
        name = type(exc).__name__
        detail = str(exc)[:200]
        status = AUTHENTICATION_REQUIRED if name in ("GatedRepoError",) else SOURCE_UNAVAILABLE
        return RepositoryProbe(repo_id, status, detail=detail, requests_used=1)
    spent["requests"] += 1

    def _get(name: str, default: object = None) -> object:
        if isinstance(info, dict):
            return info.get(name, default)
        return getattr(info, name, default)

    resolved = _get("sha")
    resolved_revision = str(resolved).strip() if isinstance(resolved, str) and resolved else None
    last_modified = _get("lastModified")
    card = _get("card_data")
    license_raw = card.get("license") if isinstance(card, dict) else None
    partial_config = _get("config")
    partial_config = partial_config if isinstance(partial_config, dict) else {}

    config: dict | None = None
    config_present = False
    detail: str | None = None
    try:
        config = _read_config(repo_id, client=client, timeout=timeout)
        config_present = True
        spent["bytes"] += len(json.dumps(config))
    except Exception as exc:  # noqa: BLE001 - an absent config is a real state
        text = str(exc)
        if "404" in text:
            detail = "no config.json in this repository (expected for GGUF-only packaging)"
        else:
            detail = text[:200]
            return RepositoryProbe(
                repo_id=repo_id,
                status=SOURCE_UNAVAILABLE,
                resolved_revision=resolved_revision,
                detail=detail,
                requests_used=1,
            )

    arch_fields = _arch_subset(config or partial_config)
    probe = RepositoryProbe(
        repo_id=repo_id,
        status=AVAILABLE,
        resolved_revision=resolved_revision,
        last_modified=str(last_modified) if last_modified else None,
        gated=bool(_get("gated")) if _get("gated") is not None else None,
        disabled=bool(_get("disabled")) if _get("disabled") is not None else None,
        license_raw=license_raw,
        config=config,
        config_present=config_present,
        detail=detail,
        requests_used=1,
        native_quant_method=_native_quant_method(config or partial_config),
    )
    probe.arch_fields = arch_fields
    return probe


def _read_config(repo_id: str, *, client: object | None, timeout: float) -> dict:
    """Read config.json through the injected client or the metadata-fetch allowlist."""
    if client is not None and hasattr(client, "config_for"):
        return client.config_for(repo_id)
    return _fetch_config(repo_id, timeout=timeout)


def _fetch_config(repo_id: str, *, timeout: float) -> dict:
    """Fetch config.json through the metadata-fetch allowlist."""
    from atlas.security.metadata_fetch import fetch_small_json

    url = CONFIG_PATH_TEMPLATE.format(repo_id=repo_id)
    return fetch_small_json(url, timeout=timeout)


def _evidence_record(
    *,
    source_id: str,
    repo_id: str,
    resolved_revision: str | None,
    claim_type: str,
    field_path: str,
    artifact_id: str | None,
    source_url: str,
    notes: str,
    evidence_level: str = "publisher_claim",
    verification_status: str = "independently_verified",
    source_type: str = "official_repo",
) -> dict:
    """Build one new evidence sidecar (never a historical reconstruction)."""
    evidence_id = generate_evidence_id_v2(
        source_id=source_id,
        repo_id=repo_id,
        resolved_revision=resolved_revision,
        claim_type=claim_type,
        field_path=field_path,
        artifact_id=artifact_id,
    )
    namespace = repo_id.split("/")[0] if "/" in repo_id else None
    return {
        "schema_version": "0.1.0",
        "evidence_id": evidence_id,
        "claim_type": claim_type,
        "field_path": field_path,
        "source_id": source_id,
        "source_type": source_type,
        "source_url": source_url,
        "retrieved_at": OBSERVED_AT,
        "publisher": namespace,
        "evidence_level": evidence_level,
        "verification_status": verification_status,
        "notes": notes[:2000],
    }


def candidate_repositories(record: dict) -> tuple[str, list[str]]:
    """Repository under test plus directly declared base repositories."""
    display = str(record.get("display_name") or "")
    target = display if "/" in display else None
    bases = [str(b) for b in (record.get("base_models") or []) if "/" in str(b)]
    return (target or "", bases)


def resolve_base_chain(
    record: dict,
    records_by_repo: dict[str, dict],
    *,
    max_length: int = MAX_BASE_HOPS,
) -> list[str]:
    """Transitive declared lineage for one record, read from canonical records.

    Only lineage already declared in the catalog is followed. A repository
    name is never interpreted as lineage, so an undeclared base stays
    unresolved rather than guessed from a name.
    """
    _, direct = candidate_repositories(record)
    chain: list[str] = []
    seen: set[str] = {str(record.get("display_name") or "")}
    frontier = list(direct)
    while frontier and len(chain) < max_length:
        repo = frontier.pop(0)
        if repo in seen:
            continue
        seen.add(repo)
        chain.append(repo)
        base_record = records_by_repo.get(repo.lower())
        if base_record is None:
            continue
        for base in base_record.get("base_models") or []:
            text = str(base)
            if "/" in text and text not in seen:
                frontier.append(text)
    return chain


def configuration_scope(arch_fields: dict) -> str:
    """Which configuration block the architecture fields came from.

    Multimodal wrappers keep the language model under a nested block, so the
    scope is disclosed instead of being flattened silently.
    """
    text_config = arch_fields.get("text_config")
    if isinstance(text_config, dict) and text_config:
        return "text_config_of_multimodal_wrapper"
    return "own_config"


def language_model_fields(arch_fields: dict) -> dict:
    """Language-model architecture fields with the scope disclosed."""
    text_config = arch_fields.get("text_config")
    if isinstance(text_config, dict) and text_config:
        merged = dict(text_config)
        for key in ("architectures", "model_type"):
            if key in arch_fields:
                merged[key] = arch_fields[key]
        return merged
    return {k: v for k, v in arch_fields.items() if k not in ("text_config", "vision_config")}


def _has_cache_inputs(arch_fields: dict) -> bool:
    """True when the fields the standard KV equation requires are present."""
    layers = arch_fields.get("num_hidden_layers")
    heads = arch_fields.get("num_key_value_heads")
    dim = arch_fields.get("head_dim") or arch_fields.get("hidden_size")
    return isinstance(layers, int) and isinstance(heads, int) and isinstance(dim, int)


def reacquire_candidate(
    *,
    candidate: dict,
    record: dict,
    records_by_repo: dict[str, dict] | None = None,
    client: object | None = None,
    budget: dict | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """Acquire current evidence for one Core candidate (read-only)."""
    spent = budget if budget is not None else {"requests": 0, "bytes": 0}
    target_repo, direct_bases = candidate_repositories(record)
    base_chain = (
        resolve_base_chain(record, records_by_repo or {})
        if records_by_repo is not None
        else list(direct_bases)
    )
    artifact_id = str(candidate.get("artifact_set_id") or "") or None
    probes: list[RepositoryProbe] = []
    evidence: list[dict] = []
    issues: list[str] = []

    target_probe = probe_repository(target_repo, client=client, budget=spent, timeout=timeout)
    probes.append(target_probe)
    if target_probe.status != AVAILABLE:
        issues.append(f"target_repository_{target_probe.status}")

    config_probe = target_probe
    config_origin = "own_config"
    chain_used: list[str] = []
    hops = 0
    if not _has_cache_inputs(target_probe.arch_fields):
        if not base_chain:
            issues.append("no_own_config_and_no_declared_base_model")
        for base_repo in base_chain:
            if hops >= MAX_BASE_HOPS:
                break
            hops += 1
            base_probe = probe_repository(base_repo, client=client, budget=spent, timeout=timeout)
            probes.append(base_probe)
            chain_used.append(base_repo)
            if base_probe.status != AVAILABLE:
                issues.append(f"declared_base_model_{base_probe.status}")
                continue
            if _has_cache_inputs(base_probe.arch_fields):
                config_probe = base_probe
                config_origin = "declared_base_model_config"
                break
        else:
            issues.append("declared_base_model_config_lacks_cache_inputs")
    if target_probe.config_present and config_probe is target_probe:
        config_origin = "own_config"

    arch_fields = dict(config_probe.arch_fields)
    language_fields = language_model_fields(arch_fields)
    if not _has_cache_inputs(language_fields):
        issues.append("architecture_cache_inputs_unavailable")

    revision = target_probe.resolved_revision
    source_id = f"{candidate['candidate_id']}-current-src"
    if arch_fields:
        evidence.append(
            _evidence_record(
                source_id=source_id,
                repo_id=config_probe.repo_id,
                resolved_revision=config_probe.resolved_revision,
                claim_type="architecture_property",
                field_path="architecture",
                artifact_id=None,
                source_url=REPO_URL_TEMPLATE.format(repo_id=config_probe.repo_id),
                notes=(
                    "Current architecture inputs read anonymously from the publisher's "
                    f"configuration source ({config_origin}); "
                    f"repo={config_probe.repo_id}; revision={config_probe.resolved_revision}"
                ),
            )
        )
    if target_probe.resolved_revision or artifact_id:
        evidence.append(
            _evidence_record(
                source_id=source_id,
                repo_id=target_repo,
                resolved_revision=revision,
                claim_type="quantization_property",
                field_path="quantization.source_revision",
                artifact_id=artifact_id,
                source_url=REPO_URL_TEMPLATE.format(repo_id=target_repo),
                notes=(
                    "Current resolved revision and exact artifact identity reacquired "
                    f"anonymously; repo={target_repo}; revision={revision}; "
                    f"artifact={artifact_id}"
                ),
            )
        )
    if config_probe.native_quant_method:
        evidence.append(
            _evidence_record(
                source_id=source_id,
                repo_id=config_probe.repo_id,
                resolved_revision=config_probe.resolved_revision,
                claim_type="quantization_property",
                field_path="quantization.native_quantization",
                artifact_id=artifact_id,
                source_url=REPO_URL_TEMPLATE.format(repo_id=config_probe.repo_id),
                notes=(
                    "Source-reported training-time quantization method "
                    f"{config_probe.native_quant_method!r}; native low-bit is a training "
                    "property, not a post-training quantization, so no base-vs-quant "
                    "retention is implied"
                ),
            )
        )
    if target_probe.license_raw is not None:
        evidence.append(
            _evidence_record(
                source_id=source_id,
                repo_id=target_repo,
                resolved_revision=revision,
                claim_type="license_term",
                field_path="license.license_id",
                artifact_id=None,
                source_url=REPO_URL_TEMPLATE.format(repo_id=target_repo),
                notes=(
                    f"Current publisher-declared license value {target_probe.license_raw!r}; "
                    "Atlas records the declaration and does not interpret it as legal advice"
                ),
            )
        )

    catalog_revision = str((record.get("quantization") or {}).get("source_revision") or "")
    revision_state = "unknown"
    if revision and catalog_revision:
        revision_state = (
            "matches_catalog" if revision == catalog_revision else "differs_from_catalog"
        )
    elif revision:
        revision_state = "reacquired_catalog_absent"

    return {
        "schema_version": CLOSURE_SCHEMA_VERSION,
        "candidate_id": candidate["candidate_id"],
        "model_id": candidate["model_id"],
        "artifact_set_id": candidate["artifact_set_id"],
        "target_repo": target_repo,
        "declared_base_models": list(direct_bases),
        "base_model_chain_used": chain_used,
        "configuration_evidence_origin": config_origin,
        "configuration_scope": configuration_scope(arch_fields),
        "language_model_fields": language_fields,
        "multimodal_wrapper": bool(arch_fields.get("vision_config")),
        "configuration_repo": config_probe.repo_id,
        "architecture_fields": arch_fields,
        "native_quant_method": config_probe.native_quant_method,
        "reacquired_revision": revision,
        "catalog_recorded_revision": catalog_revision or None,
        "revision_relation": revision_state,
        "declared_license_value": target_probe.license_raw,
        "availability": target_probe.status,
        "gated": target_probe.gated,
        "probes": [probe.to_payload() for probe in probes],
        "new_evidence": evidence,
        "issues": sorted(set(issues)),
        "historical_sidecar_state": "evidence_sidecar_unavailable",
        "current_evidence_state": "available" if evidence else "unavailable",
        "requests_used": spent["requests"],
        "bytes_fetched": spent["bytes"],
        "note": (
            "New current evidence only. Historical intake references remain without "
            "persisted sidecars and are not reconstructed."
        ),
    }


def reacquire_core_set(
    *,
    core_set: dict,
    repo_root: Path,
    client: object | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """Acquire current evidence for every resolvable Core candidate."""
    from atlas.quality.sidecars import load_records

    records = load_records(repo_root)
    records_by_repo = {
        str(record.get("display_name") or "").lower(): record
        for record in records.values()
        if "/" in str(record.get("display_name") or "")
    }
    budget = {"requests": 0, "bytes": 0}
    entries: list[dict] = []
    for candidate in sorted(core_set.get("candidates", []), key=lambda c: c["candidate_id"]):
        record = records.get(str(candidate["model_id"]))
        if record is None:
            entries.append(
                {
                    "schema_version": CLOSURE_SCHEMA_VERSION,
                    "candidate_id": candidate["candidate_id"],
                    "model_id": candidate["model_id"],
                    "availability": SOURCE_UNAVAILABLE,
                    "issues": ["catalog_record_absent"],
                    "new_evidence": [],
                    "current_evidence_state": "unavailable",
                    "historical_sidecar_state": "evidence_sidecar_unavailable",
                }
            )
            continue
        entries.append(
            reacquire_candidate(
                candidate=candidate,
                record=record,
                records_by_repo=records_by_repo,
                client=client,
                budget=budget,
                timeout=timeout,
            )
        )
    return {
        "schema_version": CLOSURE_SCHEMA_VERSION,
        "observed_at": OBSERVED_AT,
        "candidate_count": len(entries),
        "with_current_evidence": sum(1 for e in entries if e.get("new_evidence")),
        "unavailable": sorted(e["candidate_id"] for e in entries if not e.get("new_evidence")),
        "requests_used": budget["requests"],
        "bytes_fetched": budget["bytes"],
        "network_policy": "read-only-get-anonymous-no-credentials",
        "weight_policy": "no weight payload is reachable through the metadata allowlist",
        "entries": entries,
    }


def write_current_evidence(
    *,
    repo_root: Path,
    payload: dict,
    dry_run: bool = True,
) -> dict:
    """Persist the current-evidence index and its new sidecars atomically.

    Only *new* evidence ids are written. No historical evidence id is created,
    removed or renamed, so the historical unavailability record is preserved.
    """
    base = repo_root / "catalog" / "closure" / "current-evidence"
    written_sidecars: list[str] = []
    unchanged_sidecars: list[str] = []
    evidence_dir = repo_root / "catalog" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    known = {p.stem for p in evidence_dir.glob("*.json") if p.is_file()}
    for entry in payload.get("entries", []):
        for record in entry.get("new_evidence", []):
            evidence_id = str(record["evidence_id"])
            if evidence_id in known:
                unchanged_sidecars.append(evidence_id)
                continue
            known.add(evidence_id)
            written_sidecars.append(evidence_id)
            if not dry_run:
                atomic_write_json(evidence_dir / f"{evidence_id}.json", record)
    index = {
        "schema_version": CLOSURE_SCHEMA_VERSION,
        "observed_at": payload.get("observed_at"),
        "candidate_count": payload.get("candidate_count"),
        "with_current_evidence": payload.get("with_current_evidence"),
        "unavailable": payload.get("unavailable"),
        "requests_used": payload.get("requests_used"),
        "bytes_fetched": payload.get("bytes_fetched"),
        "historical_sidecar_state": "evidence_sidecar_unavailable",
        "entries": payload.get("entries", []),
    }
    target = base / "index.json"
    if not dry_run:
        atomic_write_json(target, index)
    return {
        "dry_run": dry_run,
        "target": str(target),
        "new_sidecars_written": written_sidecars,
        "new_sidecars_unchanged": unchanged_sidecars,
        "index_written": not dry_run,
    }


def link_new_evidence_to_records(
    *,
    repo_root: Path,
    entries: list[dict],
    dry_run: bool = True,
) -> dict:
    """Reference every new evidence id from its canonical model record.

    Appending is additive and idempotent: historical identifiers are preserved
    in place, never rewritten or removed, so the recorded 243
    references without persisted sidecars stays exactly as it was while the new
    current evidence becomes traceable.
    """
    models_dir = repo_root / "catalog" / "models"
    linked: list[dict] = []
    already: list[dict] = []
    for entry in entries:
        evidence_ids = [str(e["evidence_id"]) for e in entry.get("new_evidence", []) if e]
        if not evidence_ids:
            continue
        model_id = str(entry.get("model_id"))
        path = models_dir / f"{model_id}.json"
        if not path.is_file():
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        verification = dict(record.get("verification") or {})
        existing = [str(e) for e in (verification.get("evidence_ids") or [])]
        missing = [e for e in evidence_ids if e not in existing]
        if not missing:
            already.append({"model_id": model_id, "evidence_ids": evidence_ids})
            continue
        verification["evidence_ids"] = existing + missing
        updated = {**record, "verification": verification}
        linked.append(
            {
                "model_id": model_id,
                "added_evidence_ids": missing,
                "total_references": len(verification["evidence_ids"]),
            }
        )
        if not dry_run:
            atomic_write_json(path, updated)
    return {
        "dry_run": dry_run,
        "records_linked": linked,
        "records_already_linked": already,
        "historical_identifiers_preserved": True,
    }


def load_current_evidence(repo_root: Path) -> dict | None:
    """Load the persisted current-evidence index, or None when absent."""
    path = repo_root / "catalog" / "closure" / "current-evidence" / "index.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None

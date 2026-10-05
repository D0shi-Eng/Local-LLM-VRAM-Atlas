"""Deterministic semantic fingerprints (volatile fields excluded)."""

from __future__ import annotations

import hashlib
import json


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def fingerprint(payload: object) -> str:
    """SHA-256 hex over canonical JSON (256-bit, deterministic)."""
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _strip_volatile(record: dict) -> dict:
    volatile = {
        "retrieved_at",
        "observed_at",
        "downloads",
        "likes",
        "trending_score",
        "trending",
        "captured_at",
    }
    return {k: v for k, v in record.items() if k not in volatile}


def identity_fingerprint(record: dict) -> str:
    """Platform + repo + revision + variant (no timestamps)."""
    quant = record.get("quantization") or {}
    return fingerprint(
        {
            "platform": "hugging-face",
            "display_name": record.get("display_name"),
            "model_id": record.get("model_id"),
            "source_revision": quant.get("source_revision"),
            "quant_name": quant.get("quant_name"),
            "format": quant.get("format"),
        }
    )


def license_fingerprint(record: dict) -> str:
    """License identity + verification (no popularity/timestamps)."""
    lic = record.get("license") or {}
    return fingerprint(
        {
            "license_id": lic.get("license_id"),
            "license_source": lic.get("license_source"),
            "verification_status": lic.get("verification_status"),
        }
    )


def openness_fingerprint(record: dict) -> str:
    """Openness class alone (high-impact, isolated)."""
    return fingerprint({"openness": record.get("openness")})


def lineage_fingerprint(record: dict) -> str:
    """Base-model edges + alignment base (no popularity)."""
    alignment = record.get("alignment") or {}
    return fingerprint(
        {
            "base_models": sorted(record.get("base_models") or []),
            "alignment_base": alignment.get("base_model"),
        }
    )


def architecture_fingerprint(record: dict) -> str:
    """Architecture + params + context (no volatile)."""
    return fingerprint(
        {
            "architecture": record.get("architecture"),
            "architecture_type": record.get("architecture_type"),
            "total_parameters_b": record.get("total_parameters_b"),
            "active_parameters_b": record.get("active_parameters_b"),
            "experts_total": record.get("experts_total"),
            "experts_active": record.get("experts_active"),
            "context_advertised": (record.get("context_length") or {}).get("advertised_max"),
        }
    )


def artifact_manifest_fingerprint(artifacts: list[dict]) -> str:
    """Sorted artifact identities + sizes + hashes (no timestamps)."""
    items = sorted(
        (
            {
                "artifact_set_id": a.get("artifact_set_id"),
                "variant": a.get("variant"),
                "format": a.get("format"),
                "files": sorted(
                    (str(f.get("filename")), f.get("size_bytes"), f.get("sha256"))
                    for f in (a.get("files") or [])
                ),
            }
            for a in artifacts
        ),
        key=lambda item: _canonical(item),
    )
    return fingerprint(items)


def quantization_fingerprint(record: dict) -> str:
    """Quant family/name/format + file size (no popularity)."""
    quant = record.get("quantization") or {}
    return fingerprint(
        {
            "format": quant.get("format"),
            "quant_family": quant.get("quant_family"),
            "quant_name": quant.get("quant_name"),
            "bits_per_weight": quant.get("bits_per_weight"),
            "file_size_bytes": quant.get("file_size_bytes"),
        }
    )


def alignment_fingerprint(record: dict) -> str:
    """Alignment variant claim (author claim, not quality)."""
    alignment = record.get("alignment") or {}
    return fingerprint(
        {
            "alignment_variant": alignment.get("alignment_variant"),
            "uncensored_claimed": alignment.get("uncensored_claimed"),
            "uncensoring_method": alignment.get("uncensoring_method"),
        }
    )


def popularity_fingerprint(record: dict) -> str:
    """Dedicated popularity fingerprint (informational only, never semantic)."""
    popularity = record.get("popularity") or {}
    return fingerprint(
        {
            "downloads": popularity.get("downloads"),
            "likes": popularity.get("likes"),
            "trending": popularity.get("trending"),
        }
    )


def all_fingerprints(record: dict, artifacts: list[dict] | None = None) -> dict[str, str]:
    """Compute every semantic fingerprint for delta comparison."""
    return {
        "identity": identity_fingerprint(record),
        "license": license_fingerprint(record),
        "openness": openness_fingerprint(record),
        "lineage": lineage_fingerprint(record),
        "architecture": architecture_fingerprint(record),
        "artifact_manifest": artifact_manifest_fingerprint(artifacts or []),
        "quantization": quantization_fingerprint(record),
        "alignment": alignment_fingerprint(record),
    }


def _unused_volatile_guard() -> dict:
    # Documents the volatile exclusion contract for reviewers.
    return _strip_volatile({"retrieved_at": "x", "downloads": 1, "a": 2})

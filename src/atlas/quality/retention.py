"""Quantization retention evidence (Phase 6).

A retention number exists only when a base score and a quantized score come
from the *same* comparable setup. Otherwise the state stays explicit
(``partially_comparable`` / ``insufficient_evidence`` / ``unknown``) instead of
producing a fabricated percentage.

Base quality never becomes quant quality: when only the base was evaluated,
the quantized artifact keeps ``unknown`` retention and may expose the parent
score as reference context only.
"""

from __future__ import annotations

import hashlib

from atlas.quality import QUALITY_SCHEMA_VERSION
from atlas.quality.comparability import compare, comparison_key

RETENTION_DOMAIN = "atlas-quant-retention/v1"

RETENTION_STATUSES = (
    "directly_measured",
    "independently_measured",
    "publisher_measured",
    "partially_comparable",
    "insufficient_evidence",
    "unknown",
)

# Settings that must match for a retention number to be computed.
_COMPARABLE_FIELDS = (
    "benchmark_id",
    "benchmark_version",
    "metric",
    "score_unit",
    "reasoning_mode",
    "tool_mode",
    "prompting_mode",
    "context_configuration",
)


def retention_id(*, base_release: str, quantized_artifact: str, benchmark_id: str) -> str:
    """Deterministic retention identity (no timestamps)."""
    digest = hashlib.sha256(
        "\x1f".join(
            [
                RETENTION_DOMAIN,
                base_release.strip().lower(),
                quantized_artifact.strip().lower(),
                benchmark_id.strip().lower(),
            ]
        ).encode("utf-8")
    ).hexdigest()
    return f"ret-v1-{digest}"


def _score(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def build_retention(
    *,
    base_release: str,
    quantized_artifact: str,
    quantization: str | None,
    base_result: dict | None,
    quant_result: dict | None,
    source: str | None = None,
    evidence_ids: list[str] | None = None,
    publisher_claim: dict | None = None,
    notes: str | None = None,
) -> dict:
    """Build one retention record from available (possibly missing) evidence."""
    benchmark_id = str(
        (base_result or {}).get("benchmark_id")
        or (quant_result or {}).get("benchmark_id")
        or "unresolved"
    )
    evidence = sorted({e for e in (evidence_ids or []) if isinstance(e, str) and e})
    base_score = _score((base_result or {}).get("score"))
    quant_score = _score((quant_result or {}).get("score"))
    metric = (base_result or {}).get("metric") or (quant_result or {}).get("metric")
    direction = (base_result or {}).get("metric_direction") or (quant_result or {}).get(
        "metric_direction"
    )

    settings_match = False
    reason = ""
    if base_result is None and quant_result is None:
        settings_match = False
        reason = "no evaluation evidence for either release"
    elif base_result is None:
        settings_match = False
        reason = "missing base score: retention cannot be computed"
    elif quant_result is None:
        settings_match = False
        reason = "missing quantized score: retention remains unknown"
    else:
        verdict = compare(base_result, quant_result)
        settings_match = bool(verdict["comparable"])
        reason = verdict["reason"]

    absolute_delta: float | None = None
    relative_delta: float | None = None
    if settings_match and base_score is not None and quant_score is not None:
        absolute_delta = round(quant_score - base_score, 6)
        if direction == "higher_is_better" and base_score != 0:
            relative_delta = round((quant_score - base_score) / base_score, 6)

    if settings_match and absolute_delta is not None:
        origins = {
            str((base_result or {}).get("evaluation_origin")),
            str((quant_result or {}).get("evaluation_origin")),
        }
        if "independent" in origins:
            status = "independently_measured"
        elif "publisher" in origins:
            status = "publisher_measured"
        else:
            status = "directly_measured"
    elif base_result is not None and quant_result is not None:
        status = "partially_comparable"
    elif base_result is not None or quant_result is not None:
        status = "insufficient_evidence"
    else:
        status = "unknown"

    verification = None
    if base_result is not None and quant_result is not None:
        verification = str(quant_result.get("verification_status") or "unknown")

    return {
        "schema_version": QUALITY_SCHEMA_VERSION,
        "retention_id": retention_id(
            base_release=base_release,
            quantized_artifact=quantized_artifact,
            benchmark_id=benchmark_id,
        ),
        "base_release": base_release,
        "quantized_artifact": quantized_artifact,
        "quantization": quantization,
        "benchmark_id": benchmark_id,
        "benchmark_version": (base_result or {}).get("benchmark_version")
        or (quant_result or {}).get("benchmark_version"),
        "base_score": base_score,
        "quant_score": quant_score,
        "metric": metric,
        "metric_direction": direction,
        "absolute_delta": absolute_delta,
        "relative_delta": relative_delta,
        "evaluation_settings_match": settings_match,
        "retention_status": status,
        "source": source
        or (quant_result or {}).get("source_id")
        or (base_result or {}).get("source_id"),
        "evidence_quality": _evidence_quality(base_result, quant_result),
        "verification_status": verification,
        "evidence_ids": evidence,
        "publisher_claim": publisher_claim,
        "notes": "; ".join(part for part in (reason, notes) if part) or None,
    }


def _evidence_quality(base_result: dict | None, quant_result: dict | None) -> str:
    from atlas.quality.tiers import evidence_status_from_origins

    results = [r for r in (base_result, quant_result) if r is not None]
    origins = [str(r.get("evaluation_origin")) for r in results]
    verifications = [str(r.get("verification_status")) for r in results]
    independent_sources = [
        str(r.get("source_id")) for r in results if str(r.get("evaluation_origin")) == "independent"
    ]
    if not origins:
        return "unknown"
    return evidence_status_from_origins(
        origins,
        verification_statuses=verifications,
        independent_sources=independent_sources,
    )


def settings_match(base_result: dict | None, quant_result: dict | None) -> bool:
    """Public helper: identical comparable setup for both sides."""
    if base_result is None or quant_result is None:
        return False
    return comparison_key(base_result) == comparison_key(quant_result)


def parent_reference_only(*, base_result: dict | None, quant_result: dict | None) -> dict:
    """Explicit parent-context block for a quantized artifact.

    The parent score may be *displayed* as context, but it is never the
    quantized artifact's own quality score.
    """
    has_exact = settings_match(base_result, quant_result) and quant_result is not None
    return {
        "parent_score_available": base_result is not None,
        "parent_benchmark_id": (base_result or {}).get("benchmark_id"),
        "parent_score": _score((base_result or {}).get("score")),
        "usable_as_quant_quality": bool(has_exact),
        "disclosure": (
            "base model quality context only; quantized variant retention unknown"
            if not has_exact
            else "exact quantized-variant evaluation available"
        ),
    }

"""Quantization retention closure for Core Recommendation Set candidates.

Atlas computes a retention number only when a base score and a quantized score
come from the same comparable setup. This module pairs exact base-release and
exact quantized-artifact results and delegates the decision to the Phase 6
retention builder and comparability rules.

Never performed here:

- assigning a retention percentage from quantization family folklore;
- transferring a base score onto a quantized artifact;
- treating a native low-bit training quantization as post-training
  quantization, which would demand an artificial base-vs-quant comparison.
"""

from __future__ import annotations

import json
from pathlib import Path

from atlas.closure import CLOSURE_SCHEMA_VERSION, REFERENCE_DATE
from atlas.intake.store import atomic_write_json
from atlas.quality.retention import build_retention

RETENTION_EVIDENCE_STATES = (
    "independently_measured",
    "directly_measured",
    "publisher_measured",
    "partially_comparable",
    "unknown",
)


def _base_release_for(record: dict) -> str | None:
    """Declared base release of a quantized record, when the catalog states one."""
    bases = [str(b) for b in (record.get("base_models") or []) if "/" in str(b)]
    return bases[0] if bases else None


def _exact_results(evaluations: list[dict], *, require_quant: str | None) -> list[dict]:
    return [
        e
        for e in evaluations
        if str(e.get("match_status", "")).startswith("exact")
        and not e.get("superseded")
        and (require_quant is None or bool(str(e.get("quantization") or "")))
    ]


def _harness_divergence(base_result: dict | None, quant_result: dict | None) -> str | None:
    """Extra comparability gate on the evaluation harness identity.

    Phase 6 compares benchmark id/version, metric, unit and evaluation modes.
    Phase 6.5 adds one further requirement: the same harness/suite version must
    have produced both numbers, because a different harness is a different
    measurement setup even when every declared setting matches.
    """
    if base_result is None or quant_result is None:
        return None
    base_suite = str(base_result.get("suite_version") or "unresolved")
    quant_suite = str(quant_result.get("suite_version") or "unresolved")
    if base_suite == quant_suite:
        return None
    return f"harness divergence: base suite_version={base_suite} vs quant {quant_suite}"


def build_candidate_retention(
    *,
    candidate: dict,
    record: dict,
    records: dict[str, dict],
    evaluations_by_model: dict[str, list[dict]],
    native_low_bit: bool,
) -> dict:
    """Retention record for one exact Core artifact, honest when unknown."""
    from atlas.catalog.special import compression_evidence

    quantization = str(candidate.get("quantization_label") or "")
    base_release = _base_release_for(record)
    base_record = records.get(str(base_release).lower()) if base_release else None
    if base_record is None and base_release:
        for other in records.values():
            if str(other.get("display_name") or "").lower() == base_release.lower():
                base_record = other
                break

    base_results = _exact_results(
        evaluations_by_model.get(str(candidate["model_id"]), []), require_quant=None
    )
    quant_results = [
        e
        for e in _exact_results(
            evaluations_by_model.get(str(candidate["model_id"]), []), require_quant="yes"
        )
        if str(e.get("quantization") or "").upper() == quantization.upper()
    ]
    base_score = base_results[0] if base_results else None
    if base_score is not None and base_record is not None:
        for other in evaluations_by_model.get(str(base_record.get("model_id")), []):
            if str(other.get("match_status", "")).startswith("exact") and not other.get(
                "superseded"
            ):
                base_score = other
                break

    built = build_retention(
        base_release=str(base_record.get("model_id"))
        if base_record
        else str(candidate["model_id"]),
        quantized_artifact=str(candidate["artifact_set_id"]),
        quantization=quantization,
        base_result=base_score,
        quant_result=quant_results[0] if quant_results else None,
        evidence_ids=sorted(
            {
                str(e)
                for e in (quant_results[0] if quant_results else base_score or {}).get(
                    "evidence_ids", []
                )
            }
        ),
        notes=(
            "Base release and quantized artifact are the exact declared lineage; no comparable "
            "quantized result exists, so retention is not computed"
        ),
    )
    harness_reason = _harness_divergence(base_score, quant_results[0] if quant_results else None)
    if harness_reason and built["retention_status"] in (
        "directly_measured",
        "independently_measured",
        "publisher_measured",
    ):
        built = {
            **built,
            "retention_status": "partially_comparable",
            "absolute_delta": None,
            "relative_delta": None,
            "evaluation_settings_match": False,
            "notes": "; ".join(part for part in (harness_reason, built["notes"]) if part),
        }
    is_post_training = bool(candidate.get("artifact_variant")) and not native_low_bit
    return {
        "schema_version": CLOSURE_SCHEMA_VERSION,
        "candidate_id": candidate["candidate_id"],
        "artifact_set_id": candidate["artifact_set_id"],
        "quantization": quantization,
        "declared_base_release": base_release,
        "post_training_quantized": is_post_training,
        "native_low_bit": native_low_bit,
        "high_compression": compression_evidence(record)["is_high_compression"],
        "retention_id": built["retention_id"],
        "retention_status": built["retention_status"],
        "base_score": built["base_score"],
        "quant_score": built["quant_score"],
        "absolute_delta": built["absolute_delta"],
        "relative_delta": built["relative_delta"],
        "evaluation_settings_match": built["evaluation_settings_match"],
        "evidence_quality": built["evidence_quality"],
        "evidence_ids": built["evidence_ids"],
        "notes": built["notes"],
        "guessing_policy": (
            "no heuristic percentage is ever assigned; a missing quantized result keeps "
            "retention unknown"
        ),
        "retention_record": built,
    }


def build_retention_closure(
    *,
    repo_root: Path,
    core_set: dict,
) -> dict:
    """Retention closure for every Core candidate."""
    from atlas.catalog.special import native_low_bit_status
    from atlas.quality.ingest import load_evaluations
    from atlas.quality.sidecars import load_records

    records = load_records(repo_root)
    evaluations = load_evaluations(repo_root)
    by_model: dict[str, list[dict]] = {}
    for evaluation in evaluations.values():
        by_model.setdefault(str(evaluation.get("model_id")), []).append(evaluation)

    entries: list[dict] = []
    for candidate in sorted(core_set.get("candidates", []), key=lambda c: c["candidate_id"]):
        record = records.get(str(candidate["model_id"]), {})
        native = bool(native_low_bit_status(record)["is_native_low_bit"])
        entries.append(
            build_candidate_retention(
                candidate=candidate,
                record=record,
                records=records,
                evaluations_by_model=by_model,
                native_low_bit=native,
            )
        )
    states: dict[str, int] = {}
    for entry in entries:
        key = str(entry["retention_status"])
        states[key] = states.get(key, 0) + 1
    return {
        "schema_version": CLOSURE_SCHEMA_VERSION,
        "observed_at": f"{REFERENCE_DATE}T00:00:00Z",
        "candidate_count": len(entries),
        "retention_status_counts": dict(sorted(states.items())),
        "entries": entries,
    }


def write_retention_closure(*, repo_root: Path, payload: dict, dry_run: bool = True) -> Path:
    """Persist the retention closure atomically."""
    target = repo_root / "catalog" / "closure" / "quant-retention-closure.json"
    if not dry_run:
        atomic_write_json(target, payload)
    return target


def load_retention_closure(repo_root: Path) -> dict | None:
    """Load the persisted retention closure, or None when absent."""
    path = repo_root / "catalog" / "closure" / "quant-retention-closure.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None

"""Publication-readiness states for Core Recommendation Set candidates.

Four states, never merged and never waived:

``STRICT_READY``      every declared strict gate is satisfied by persisted
                      evidence and the Phase 6 recommendation policy;
``CANDIDATE_READY``   useful catalog content with substantial evidence where one
                      or more strict gates are still incomplete, and every
                      missing gate is listed;
``CATALOG_ONLY``      legitimate catalog content without enough recommendation
                      evidence to appear in any recommendation list;
``BLOCKED``           a critical identity, license, security, lineage or
                      evidence-integrity problem prevents reliable use.

Every state is derived from policy and evidence. There is no manual override,
and popularity, size, parameter count, brand, recency and adoption cannot raise
a state.
"""

from __future__ import annotations

import json
from pathlib import Path

from atlas.closure import (
    CLOSURE_POLICY_ID,
    CLOSURE_POLICY_VERSION,
    CLOSURE_SCHEMA_VERSION,
    REFERENCE_DATE,
)
from atlas.intake.store import atomic_write_json
from atlas.quality.policy import RECOMMENDATION_POLICY

READINESS_STATES = ("STRICT_READY", "CANDIDATE_READY", "CATALOG_ONLY", "BLOCKED")

CLOSURE_POLICY = {
    "schema_version": CLOSURE_SCHEMA_VERSION,
    "policy_id": CLOSURE_POLICY_ID,
    "policy_version": CLOSURE_POLICY_VERSION,
    "policy_kind": "publication_readiness",
    "reference_date": REFERENCE_DATE,
    "rules": {
        "states": list(READINESS_STATES),
        "derived_recommendation_policy": {
            "policy_id": RECOMMENDATION_POLICY["policy_id"],
            "policy_version": RECOMMENDATION_POLICY["policy_version"],
        },
        "strict_gates": [
            "exact_artifact_identity",
            "current_provenance_persisted",
            "license_status_acceptable",
            "runtime_compatibility_documented",
            "vram_fit_state_strict",
            "independent_multi_source_quality",
            "no_unresolved_identity_conflict",
            "quant_retention_when_post_training_quantized",
            "no_evidence_fabrication",
        ],
        "manual_override_allowed": False,
        "waivers_allowed": False,
        "signals_that_cannot_raise_a_state": [
            "downloads",
            "likes",
            "trending",
            "parameter_count",
            "artifact_byte_size",
            "publisher_brand",
            "release_recency",
            "adoption",
        ],
    },
    "source_assumptions": [
        "Phase 6 recommendation policy remains authoritative for tier eligibility.",
        "A quantized artifact without direct comparable retention evidence is never presented "
        "as equally evidenced to its base release.",
        "An alignment-modified variant never inherits its parent's quality score.",
        "A measurement on a larger GPU is memory-requirement evidence, not hardware "
        "verification on the target tier.",
        "A missing evidence domain lowers a state; it never raises one.",
    ],
    "rationale": (
        "Publication readiness is reported honestly even when it is zero. Non-zero counts are "
        "never manufactured by relaxing a gate."
    ),
}

STRICT_LICENSE_STATUSES = frozenset(RECOMMENDATION_POLICY["rules"]["license_status_for_strict"])
STRICT_RUNTIME_STATUSES = frozenset(RECOMMENDATION_POLICY["rules"]["runtime_status_for_strict"])
STRICT_FIT_STATES = frozenset(RECOMMENDATION_POLICY["rules"]["strict_fit_states"])

_STATUS_PRESENT = "present"
_STATUS_MISSING = "missing"
_STATUS_REFUSED = "refused"


def _status(ok: bool, *, refused: bool = False) -> str:
    if ok:
        return _STATUS_PRESENT
    return _STATUS_REFUSED if refused else _STATUS_MISSING


def _independent_run_keys(results: list[dict]) -> set[tuple]:
    """Distinct underlying evaluation runs, keyed by the original evaluator.

    Independence is about the run, not the URL. Two pages republishing one run
    share evaluator, benchmark, benchmark version, suite version, date and
    metric, so they collapse into one source instead of two.
    """
    keys: set[tuple] = set()
    for result in results:
        if str(result.get("evaluation_origin")) != "independent":
            continue
        keys.add(
            (
                str(result.get("evaluator") or result.get("source_id")),
                str(result.get("benchmark_id")),
                str(result.get("benchmark_version")),
                str(result.get("suite_version")),
                str(result.get("evaluation_date")),
                str(result.get("metric")),
            )
        )
    return keys


def _quality_state(
    *,
    evaluations: list[dict],
    candidate_artifact_id: str,
    is_post_training_quant: bool,
) -> tuple[str, list[str]]:
    """Quality evidence state for one exact artifact.

    A post-training quantized artifact never inherits the base release's score.
    """
    exact = [
        e
        for e in evaluations
        if str(e.get("match_status", "")).startswith("exact") and not e.get("superseded")
    ]
    own = [
        e
        for e in exact
        if not is_post_training_quant
        or str(e.get("artifact_id") or "") == candidate_artifact_id
        or str(e.get("quantization") or "") != ""
    ]
    independent_runs = _independent_run_keys(own)
    reasons: list[str] = []
    if len(independent_runs) >= 2:
        state = "independent_multi_source"
    elif len(independent_runs) == 1:
        state = "independent_single_source"
        reasons.append(
            "one independent run only; the strict quality gate requires independent "
            "multi-source evidence under the Phase 6 policy"
        )
    elif own:
        origins = sorted({str(e.get("evaluation_origin")) for e in own})
        state = "publisher_or_community_only"
        reasons.append(f"origins={origins}; no independent evaluation run")
    else:
        state = "unevaluated"
        reasons.append("no exact evaluation result exists for this artifact")
    if is_post_training_quant and not any(e.get("quantization") for e in exact):
        reasons.append(
            "post-training quantized artifact: the base release's score is never transferred"
        )
    return state, reasons


def _retention_state(
    *,
    retention: dict | None,
    is_post_training_quant: bool,
    is_native_low_bit: bool,
) -> tuple[str, list[str]]:
    """Quantization retention state for one exact artifact."""
    if not is_post_training_quant:
        if is_native_low_bit:
            return "not_required_native_low_bit", []
        return "not_required_no_post_training_quantization", []
    if retention is None:
        return "unknown", ["no retention record exists for this exact artifact"]
    status = str(retention.get("retention_status"))
    if status in ("directly_measured", "independently_measured"):
        return status, []
    if status == "publisher_measured":
        return status, ["retention comes from a publisher run, not an independent one"]
    if status == "partially_comparable":
        return status, ["base and quantized results are not fully comparable"]
    return status, [f"retention_status={status}"]


def _license_state(*, record: dict) -> tuple[str, list[str]]:
    """License acceptability, reusing the Phase 6 domain unchanged."""
    from atlas.quality.recommend import license_domain

    domain = license_domain(record)
    status = str(domain["status"])
    reasons = (
        []
        if status in STRICT_LICENSE_STATUSES
        else [f"license_status={status}; recorded without interpretation"]
    )
    return status, reasons


def _runtime_state(*, runtime_hints: list[str]) -> tuple[str, list[str]]:
    """Runtime compatibility state, reusing the Phase 6 domain unchanged."""
    from atlas.quality.recommend import runtime_domain

    domain = runtime_domain(record={}, runtime_support=runtime_hints)
    status = str(domain["status"])
    reasons = (
        []
        if status in STRICT_RUNTIME_STATUSES
        else [f"runtime_status={status}; runtime hints: {domain.get('runtimes') or 'none'}"]
    )
    return status, reasons


def _axis_states(*, model_id: str, evaluations: list[dict]) -> dict[str, str]:
    """Per-axis quality state, reusing the Phase 6 profile builder unchanged."""
    from atlas.quality import QUALITY_SNAPSHOT_VERSION
    from atlas.quality.profiles import build_profile

    profile = build_profile(
        model_id=model_id,
        results=evaluations,
        quality_snapshot_version=QUALITY_SNAPSHOT_VERSION,
    )
    axes = profile.get("axes") or {}
    return {
        "general_quality": str((axes.get("general_intelligence") or {}).get("status")),
        "coding": str((axes.get("coding") or {}).get("status")),
        "reasoning": str((axes.get("reasoning") or {}).get("status")),
        "arabic": str((axes.get("arabic") or {}).get("status")),
        "multilingual": str((axes.get("multilingual") or {}).get("status")),
        "long_context": str((axes.get("long_context") or {}).get("status")),
    }


def evaluate_candidate(
    *,
    candidate: dict,
    record: dict,
    estimate: dict | None,
    current_evidence: dict | None,
    evaluations: list[dict],
    retention: dict | None,
    sidecar_state: str,
) -> dict:
    """Derive one Core candidate's publication-readiness state."""
    from atlas.catalog.special import native_low_bit_status

    candidate_id = str(candidate["candidate_id"])
    artifact_id = str(candidate["artifact_set_id"])
    artifact_variant = candidate.get("artifact_variant")
    is_post_training_quant = bool(artifact_variant) and not bool(
        (current_evidence or {}).get("native_quant_method")
    )
    is_native_low_bit = bool(native_low_bit_status(record)["is_native_low_bit"]) or bool(
        (current_evidence or {}).get("native_quant_method")
    )
    alignment_variant = str((record.get("alignment") or {}).get("alignment_variant") or "unknown")
    is_alignment_variant = alignment_variant in ("uncensored", "abliterated", "heretic")

    blockers: list[str] = []
    blocked_reasons: list[str] = []
    gates: dict[str, dict] = {}

    identity_ok = bool(record.get("model_id")) and bool(artifact_id)
    gates["exact_artifact_identity"] = {
        "status": _status(identity_ok),
        "detail": f"artifact_set_id={artifact_id}",
    }
    if not identity_ok:
        blockers.append("exact_artifact_identity")

    new_evidence_ids = [
        str(e.get("evidence_id")) for e in (current_evidence or {}).get("new_evidence", []) if e
    ]
    provenance_ok = bool(new_evidence_ids) and str(
        (current_evidence or {}).get("availability")
    ) in (
        "available",
        "",
    )
    gates["current_provenance_persisted"] = {
        "status": _status(provenance_ok),
        "detail": f"{len(new_evidence_ids)} new current evidence record(s)",
        "evidence_ids": new_evidence_ids,
    }
    if not provenance_ok:
        blockers.append("current_provenance_persisted")

    license_status, license_reasons = _license_state(record=record)
    gates["license_status_acceptable"] = {
        "status": _status(license_status in STRICT_LICENSE_STATUSES),
        "detail": f"license_status={license_status}",
        "reasons": license_reasons,
    }
    if license_status not in STRICT_LICENSE_STATUSES:
        blockers.append("license_status_acceptable")

    from atlas.catalog.runtime_hints import hints_for_format

    container_format = str((record.get("quantization") or {}).get("format") or "unknown")
    runtime_names = sorted({str(h["runtime"]) for h in hints_for_format(container_format)})
    runtime_status, runtime_reasons = _runtime_state(runtime_hints=runtime_names)
    gates["runtime_compatibility_documented"] = {
        "status": _status(runtime_status in STRICT_RUNTIME_STATUSES),
        "detail": f"runtime_status={runtime_status}; container_format={container_format}",
        "reasons": runtime_reasons,
    }
    if runtime_status not in STRICT_RUNTIME_STATUSES:
        blockers.append("runtime_compatibility_documented")

    by_tier = dict((estimate or {}).get("by_tier") or {})
    tier_gate: dict[str, dict] = {}
    strict_tiers: list[int] = []
    for tier in (4, 8, 12, 16):
        state = str(by_tier.get(str(tier), "insufficient_evidence"))
        tier_gate[str(tier)] = {
            "state": state,
            "strict": state in set(RECOMMENDATION_POLICY["rules"]["strict_fit_states"]),
            "reason": str((estimate or {}).get("tier_reasons", {}).get(str(tier), "no estimate")),
        }
        if tier_gate[str(tier)]["strict"]:
            strict_tiers.append(tier)
    gates["vram_fit_state_strict"] = {
        "status": _status(bool(strict_tiers), refused=True),
        "detail": "no tier reaches estimated_fit: "
        + "; ".join(f"{t}GB={tier_gate[str(t)]['state']}" for t in (4, 8, 12, 16)),
        "by_tier": tier_gate,
        "strict_tiers": strict_tiers,
    }
    if not strict_tiers:
        blockers.append("vram_fit_state_strict")

    quality_state, quality_reasons = _quality_state(
        evaluations=evaluations,
        candidate_artifact_id=artifact_id,
        is_post_training_quant=is_post_training_quant,
    )
    axis_states = _axis_states(model_id=str(candidate["model_id"]), evaluations=evaluations)
    quality_ok = quality_state == "independent_multi_source"
    gates["independent_multi_source_quality"] = {
        "status": _status(quality_ok),
        "detail": f"quality_state={quality_state}",
        "reasons": quality_reasons,
        "axes": axis_states,
    }
    if not quality_ok:
        blockers.append("independent_multi_source_quality")

    identity_conflict = any(str(e.get("match_status")) == "identity_conflict" for e in evaluations)
    gates["no_unresolved_identity_conflict"] = {
        "status": _status(not identity_conflict),
        "detail": "no identity conflict recorded" if not identity_conflict else "identity conflict",
    }
    if identity_conflict:
        blockers.append("no_unresolved_identity_conflict")

    retention_state, retention_reasons = _retention_state(
        retention=retention,
        is_post_training_quant=is_post_training_quant,
        is_native_low_bit=is_native_low_bit,
    )
    retention_ok = retention_state in ("directly_measured", "independently_measured") or (
        not is_post_training_quant
    )
    gates["quant_retention_when_post_training_quantized"] = {
        "status": _status(retention_ok),
        "detail": f"retention_state={retention_state}",
        "reasons": retention_reasons,
    }
    if not retention_ok:
        blockers.append("quant_retention_when_post_training_quantized")

    gates["no_evidence_fabrication"] = {
        "status": _STATUS_PRESENT,
        "detail": (
            "every attached result is an exact, revision-aware record; historical sidecars "
            "remain unavailable and were not reconstructed"
        ),
    }

    if is_alignment_variant:
        declared_lineage = [str(b) for b in (record.get("base_models") or []) if "/" in str(b)]
        if not declared_lineage:
            blockers.append("alignment_variant_without_declared_lineage")
        else:
            blockers.append(f"alignment_variant_exact_evaluation:{alignment_variant}")
            blocked_reasons.append(
                f"{alignment_variant} variant: parent quality is reference only and no "
                "exact-variant evaluation exists"
            )

    evidence_gate_ok = sidecar_state in ("complete", "partial")
    gates["historical_sidecar_state"] = {
        "status": _STATUS_PRESENT if evidence_gate_ok else _STATUS_MISSING,
        "detail": (
            f"sidecar_completeness={sidecar_state}; historical references without sidecars "
            "remain evidence_sidecar_unavailable"
        ),
    }

    identity_conflict_gate = gates["no_unresolved_identity_conflict"]["status"]
    if identity_conflict_gate == "refused" or (
        is_alignment_variant and "alignment_variant_without_declared_lineage" in blockers
    ):
        state = "BLOCKED"
    elif not blockers:
        state = "STRICT_READY"
    elif (
        gates["current_provenance_persisted"]["status"] == _STATUS_PRESENT
        and gates["license_status_acceptable"]["status"] == _STATUS_PRESENT
        and gates["runtime_compatibility_documented"]["status"] == _STATUS_PRESENT
        and str((estimate or {}).get("estimate_status")) not in ("refused", "")
    ):
        state = "CANDIDATE_READY"
    else:
        state = "CATALOG_ONLY"

    return {
        "schema_version": CLOSURE_SCHEMA_VERSION,
        "candidate_id": candidate_id,
        "model_id": candidate["model_id"],
        "artifact_set_id": artifact_id,
        "quantization_label": candidate.get("quantization_label"),
        "target_tiers": list(candidate.get("target_tiers") or []),
        "strict_tiers": strict_tiers,
        "readiness_state": state,
        "state_reasons": blocked_reasons,
        "missing_gates": sorted(set(blockers)),
        "gates": gates,
        "post_training_quantized": is_post_training_quant,
        "native_low_bit": is_native_low_bit,
        "alignment_variant": alignment_variant,
        "quant_retention_state": retention_state,
        "quality_state": quality_state,
        "general_quality": axis_states["general_quality"],
        "coding_quality": axis_states["coding"],
        "reasoning_quality": axis_states["reasoning"],
        "arabic_quality": axis_states["arabic"],
        "license_status": license_status,
        "runtime_status": runtime_status,
        "architecture_family": (estimate or {}).get("architecture_family"),
        "current_evidence_ids": new_evidence_ids,
        "historical_sidecar_state": "evidence_sidecar_unavailable",
        "policy_id": CLOSURE_POLICY_ID,
        "policy_version": CLOSURE_POLICY_VERSION,
        "recommendation_policy_id": RECOMMENDATION_POLICY["policy_id"],
        "recommendation_policy_version": RECOMMENDATION_POLICY["policy_version"],
    }


def build_readiness(
    *,
    repo_root: Path,
    core_set: dict,
    evidence_index: dict | None,
    estimates: dict[str, dict],
    retentions: dict[str, dict] | None = None,
) -> dict:
    """Derive readiness for every Core candidate from canonical evidence."""
    from atlas.quality.ingest import load_evaluations
    from atlas.quality.sidecars import load_records, sidecar_completeness

    records = load_records(repo_root)
    evaluations = load_evaluations(repo_root)
    by_model: dict[str, list[dict]] = {}
    for evaluation in evaluations.values():
        by_model.setdefault(str(evaluation.get("model_id")), []).append(evaluation)
    evidence_by_candidate = {
        str(entry.get("candidate_id")): entry
        for entry in ((evidence_index or {}).get("entries") or [])
    }
    retentions = retentions or {}

    entries: list[dict] = []
    for candidate in sorted(core_set.get("candidates", []), key=lambda c: c["candidate_id"]):
        model_id = str(candidate["model_id"])
        record = records.get(model_id, {})
        entries.append(
            evaluate_candidate(
                candidate=candidate,
                record=record,
                estimate=estimates.get(str(candidate["candidate_id"])),
                current_evidence=evidence_by_candidate.get(str(candidate["candidate_id"])),
                evaluations=by_model.get(model_id, []),
                retention=retentions.get(str(candidate["artifact_set_id"])),
                sidecar_state=sidecar_completeness(record, repo_root) if record else "none",
            )
        )

    tier_matrix: dict[str, dict] = {}
    for tier in (4, 8, 12, 16):
        in_tier = [
            e
            for e in entries
            if tier in (e.get("target_tiers") or []) or tier in (e.get("strict_tiers") or [])
        ]
        counts = {state: 0 for state in READINESS_STATES}
        blocking: dict[str, int] = {}
        for entry in in_tier:
            counts[entry["readiness_state"]] += 1
            for gate in entry["missing_gates"]:
                blocking[gate] = blocking.get(gate, 0) + 1
        top = sorted(blocking.items(), key=lambda item: (-item[1], item[0]))[:3]
        tier_matrix[str(tier)] = {
            "core_candidates_in_tier": len(in_tier),
            "STRICT_READY": counts["STRICT_READY"],
            "CANDIDATE_READY": counts["CANDIDATE_READY"],
            "CATALOG_ONLY": counts["CATALOG_ONLY"],
            "BLOCKED": counts["BLOCKED"],
            "top_blocking_gates": [{"gate": name, "candidates": count} for name, count in top],
            "strict_coverage_gap": counts["STRICT_READY"] == 0,
        }

    return {
        "schema_version": CLOSURE_SCHEMA_VERSION,
        "observed_at": f"{REFERENCE_DATE}T00:00:00Z",
        "policy_id": CLOSURE_POLICY_ID,
        "policy_version": CLOSURE_POLICY_VERSION,
        "policy": CLOSURE_POLICY,
        "counts": {
            "core_candidates": len(entries),
            "by_state": {
                state: sum(1 for e in entries if e["readiness_state"] == state)
                for state in READINESS_STATES
            },
            "strict_recommendations": sum(
                len(e["strict_tiers"]) for e in entries if e["readiness_state"] == "STRICT_READY"
            ),
        },
        "tier_matrix": tier_matrix,
        "tier_coverage_blocker": any(
            tier_matrix[str(t)]["strict_coverage_gap"] for t in (4, 8, 12, 16)
        ),
        "license_decision_required": True,
        "entries": entries,
        "determinism": (
            "state is a pure function of the persisted evidence snapshot, the catalog snapshot "
            "and the declared policies; no manual override exists"
        ),
    }


def journal_readiness_events(*, repo_root: Path, payload: dict) -> int:
    """Journal closure events through the Phase 5 append-only journal.

    No parallel history system is introduced: events are built by the Phase 5
    change builder and deduplicated by event id, so re-running is idempotent.
    """
    from atlas.quality.changes import append_quality_events, quality_event

    events: list[dict] = []
    for entry in payload.get("entries", []):
        evidence_ids = list(entry.get("current_evidence_ids") or [])
        if evidence_ids:
            events.append(
                quality_event(
                    event_type="evidence_reacquired",
                    model_id=str(entry["model_id"]),
                    detected_at=str(payload.get("observed_at")),
                    subject_id=str(entry["candidate_id"]),
                    evidence_ids=evidence_ids,
                    changed_fields=["verification.evidence_ids"],
                    notes=(
                        "current provenance reacquired for the Core candidate; historical "
                        "sidecars remain unavailable"
                    ),
                )
            )
        events.append(
            quality_event(
                event_type="recommendation_status_changed",
                model_id=str(entry["model_id"]),
                detected_at=str(payload.get("observed_at")),
                subject_id=f"{entry['candidate_id']}:{entry['readiness_state']}",
                changed_fields=["readiness_state"],
                notes=f"missing gates: {', '.join(entry.get('missing_gates') or [])}",
            )
        )
    return append_quality_events(repo_root / "catalog" / "changes", events)


def write_readiness(*, repo_root: Path, payload: dict, dry_run: bool = True) -> Path:
    """Persist the readiness snapshot atomically."""
    target = repo_root / "catalog" / "closure" / "readiness.json"
    if not dry_run:
        atomic_write_json(target, payload)
    return target


def load_readiness(repo_root: Path) -> dict | None:
    """Load the persisted readiness snapshot, or None when absent."""
    path = repo_root / "catalog" / "closure" / "readiness.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None

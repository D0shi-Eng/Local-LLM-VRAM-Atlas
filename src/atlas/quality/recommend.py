"""Recommendation readiness engine (Phase 6).

Strict eligibility requires every domain at once:
QUALITY + VRAM fit + RUNTIME + LICENSE + VARIANT IDENTITY + EVIDENCE QUALITY.

A high-quality model whose VRAM state is insufficient/unsupported/indeterminate
is never presented as a strict tier recommendation. Categories are kept
separate: eligible / candidate / insufficient_evidence / ineligible.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from atlas.quality import QUALITY_SCHEMA_VERSION
from atlas.quality.policy import RECOMMENDATION_POLICY
from atlas.quality.retention import parent_reference_only

# Map Phase 4 alignment classification onto the recommendation domain.
_ALIGNMENT_VARIANTS = ("uncensored", "abliterated", "heretic")

_LICENSE_STATUS = {
    "open_source_ai": "permissive",
    "open_weights_permissive": "permissive",
    "open_weights_restricted": "restricted",
    "source_available": "restricted",
    "proprietary": "proprietary",
    "unclear": "unclear",
}


@dataclass
class RecommendationOutcome:
    """One model/tier recommendation decision."""

    record: dict
    confidence_state: str
    reasons: tuple[str, ...]
    domains: dict
    evidence_ids: tuple[str, ...]
    quant_retention: dict | None = None
    tier_gb: int | None = None
    use_case: str | None = None

    @property
    def eligibility(self) -> str:
        """Categorical eligibility derived from the declared policy."""
        rules = RECOMMENDATION_POLICY["rules"]
        quality = self.domains["quality"]["status"]
        fit = self.domains["vram_fit"]["state"]
        runtime = self.domains["runtime"]["status"]
        license_status = self.domains["license"]["status"]
        identity = self.domains["variant_identity"]["status"]
        evidence = self.domains["evidence_quality"]["status"]

        blocking: list[str] = []
        if fit not in rules["strict_fit_states"]:
            blocking.append(f"vram_fit={fit}")
        if quality not in rules["quality_status_for_strict"]:
            blocking.append(f"quality={quality}")
        if runtime not in rules["runtime_status_for_strict"]:
            blocking.append(f"runtime={runtime}")
        if license_status not in rules["license_status_for_strict"]:
            blocking.append(f"license={license_status}")
        if identity not in rules["variant_identity_for_strict"]:
            blocking.append(f"variant_identity={identity}")
        if evidence not in rules["evidence_quality_for_strict"]:
            blocking.append(f"evidence_quality={evidence}")
        if not blocking:
            return "eligible"
        if fit in rules["never_strict_fit_states"] and fit == "estimated_not_fit":
            return "ineligible"
        if fit in rules["candidate_fit_states"] and quality == "known":
            return "candidate"
        if quality == "unevaluated" and fit in rules["strict_fit_states"]:
            return "candidate"
        return "insufficient_evidence"

    def to_result(self, *, tier_gb: int, use_case: str | None = None) -> dict:
        """Serialize to a recommendation-result record."""
        policy = RECOMMENDATION_POLICY
        return {
            "schema_version": QUALITY_SCHEMA_VERSION,
            "model_id": self.record["model_id"],
            "tier_gb": tier_gb,
            "use_case": use_case,
            "eligibility": self.eligibility,
            "confidence_state": self.confidence_state,
            "reasons": list(self.reasons),
            "domains": self.domains,
            "quant_retention": self.quant_retention,
            "evidence_ids": list(self.evidence_ids),
            "policy_id": policy["policy_id"],
            "policy_version": policy["policy_version"],
        }


def license_domain(record: dict) -> dict:
    """License status for recommendation purposes; restrictions stay visible."""
    license_block = record.get("license") or {}
    openness = str(record.get("openness") or "unclear")
    status = _LICENSE_STATUS.get(openness, "unclear")
    license_id = license_block.get("license_id")
    note = license_block.get("license_notes") or None
    if status == "restricted" and not note:
        note = "license terms require review; Atlas records them without judging"
    return {
        "status": status,
        "license_id": license_id if isinstance(license_id, str) else None,
        "restriction_note": note,
    }


def runtime_domain(record: dict, runtime_support: list[str] | None = None) -> dict:
    """Runtime compatibility domain; 'supported' is not 'documented'."""
    runtimes = sorted({str(r) for r in (runtime_support or []) if str(r).strip()})
    if not runtimes:
        status = "unknown"
    elif len(runtimes) >= 2:
        status = "documented"
    else:
        status = "partial"
    return {"status": status, "runtimes": runtimes}


def quality_domain(profile: dict | None) -> dict:
    """Quality domain from a generated profile (never from popularity)."""
    if profile is None:
        return {
            "status": "unevaluated",
            "evidence_status": "unknown",
            "detail": "no quality profile",
        }
    known_axes = [
        axis
        for axis, block in (profile.get("axes") or {}).items()
        if block.get("status") == "known"
    ]
    if not known_axes:
        status = "unevaluated"
    elif profile.get("evidence_status") in ("independent_multi_source",):
        status = "known"
    else:
        status = "partially_known"
    return {
        "status": status,
        "evidence_status": profile.get("evidence_status"),
        "detail": f"axes with evidence: {', '.join(sorted(known_axes)) or 'none'}",
    }


def evidence_domain(record: dict, repo_root) -> dict:
    """Evidence-quality domain: persisted sidecars vs logical-only references."""
    from atlas.quality.sidecars import sidecar_completeness

    status = sidecar_completeness(record, repo_root)
    mapping = {
        "complete": "complete",
        "partial": "partial",
        "logical_reference_only": "logical_reference_only",
        "none": "missing",
    }
    detail = {
        "complete": "all referenced evidence sidecars persisted",
        "partial": "some referenced evidence sidecars are not persisted",
        "logical_reference_only": (
            "evidence ids are logical references without persisted sidecars "
            "(evidence_sidecar_unavailable)"
        ),
        "none": "no evidence ids referenced",
    }[status]
    return {"status": mapping[status], "detail": detail}


def variant_identity_domain(record: dict, profile: dict | None) -> dict:
    """Variant-identity domain, including alignment-variant independence."""
    alignment = record.get("alignment") or {}
    variant = str(alignment.get("alignment_variant") or "unknown")
    if variant in _ALIGNMENT_VARIANTS:
        # Parent score is context only; an alignment variant needs its own evidence.
        return {
            "status": "exact",
            "detail": (
                f"{variant} variant: exact-variant quality evidence required; "
                "parent score is reference only"
            ),
        }
    verification = (record.get("verification") or {}).get("status")
    if verification in ("independently_verified", "atlas_verified"):
        return {"status": "exact", "detail": "record identity independently verified"}
    if verification in ("publisher_claim", "quantizer_claim"):
        return {"status": "exact", "detail": "record identity from publisher claim"}
    return {"status": "unknown", "detail": f"verification={verification}"}


def evaluate_recommendation(
    *,
    record: dict,
    vram_state: str,
    profile: dict | None,
    repo_root,
    runtime_support: list[str] | None = None,
    base_result: dict | None = None,
    quant_result: dict | None = None,
    is_quantized_artifact: bool = False,
) -> RecommendationOutcome:
    """Compute the recommendation outcome for one record (no tier implied)."""
    reasons: list[str] = []
    evidence_ids: list[str] = []
    quality = quality_domain(profile)
    license_domain_block = license_domain(record)
    runtime = runtime_domain(record, runtime_support)
    identity = variant_identity_domain(record, profile)
    evidence = evidence_domain(record, repo_root)

    alignment = record.get("alignment") or {}
    variant = str(alignment.get("alignment_variant") or "unknown")

    if profile is None:
        reasons.append("no quality profile: quality unevaluated")
    else:
        evidence_ids.extend(
            str(e)
            for block in (profile.get("axes") or {}).values()
            for e in block.get("evaluation_ids", [])
        )
        evidence_ids.extend(
            str(e) for e in (record.get("verification") or {}).get("evidence_ids", [])
        )
        if variant in _ALIGNMENT_VARIANTS:
            reasons.append(f"{variant} variant shown separately; parent quality is reference only")

    if vram_state == "estimated_fit":
        reasons.append("VRAM fit estimated inside tier capacity")
    elif vram_state == "indeterminate_fit":
        reasons.append("VRAM fit indeterminate: tier capacity inside uncertainty range")
    elif vram_state == "insufficient_evidence":
        reasons.append("VRAM upper bound unavailable: fit not established")
    elif vram_state == "unsupported":
        reasons.append("architecture unsupported for VRAM estimation")
    else:
        reasons.append(f"VRAM state {vram_state}")

    if license_domain_block["status"] == "restricted":
        reasons.append(
            f"license restricted ({license_domain_block.get('license_id')}): review terms"
        )
    elif license_domain_block["status"] == "unclear":
        reasons.append("license unclear: recorded, not inferred")
    elif license_domain_block["status"] == "proprietary":
        reasons.append("proprietary license")

    if runtime["status"] == "unknown":
        reasons.append("runtime compatibility unknown")
    elif runtime["status"] == "partial":
        reasons.append(f"runtime evidence limited to {', '.join(runtime['runtimes'])}")
    else:
        reasons.append(f"runtime documented: {', '.join(runtime['runtimes'])}")

    if evidence["status"] != "complete":
        reasons.append(f"evidence quality: {evidence['status']}")

    quant_retention_block = None
    if is_quantized_artifact:
        parent = parent_reference_only(base_result=base_result, quant_result=quant_result)
        quant_retention_block = {
            "status": "unknown" if not parent["usable_as_quant_quality"] else "directly_measured",
            "disclosure": parent["disclosure"],
            "retention_id": None,
        }
        if not parent["usable_as_quant_quality"]:
            reasons.append("quantized artifact: base quality known, retention unknown")
            if evidence_ids and base_result is not None:
                reasons.append(
                    "no exact quantized-variant benchmark: quality not inherited from base"
                )

    confidence_state = _confidence(quality, vram_state, runtime, evidence)
    if not reasons:
        reasons.append("all declared domains satisfied")

    outcome = RecommendationOutcome(
        record=record,
        confidence_state=confidence_state,
        reasons=tuple(reasons),
        domains={
            "quality": quality,
            "vram_fit": {"state": vram_state, "detail": None},
            "runtime": runtime,
            "license": license_domain_block,
            "variant_identity": identity,
            "evidence_quality": evidence,
        },
        evidence_ids=tuple(sorted(set(evidence_ids))),
        quant_retention=quant_retention_block,
    )
    return outcome


def _confidence(quality: dict, vram_state: str, runtime: dict, evidence: dict) -> str:
    """Categorical evidence state, never a calibrated probability."""
    quality_ok = quality["status"] == "known"
    independent = quality.get("evidence_status") in ("independent_multi_source",)
    if (
        quality_ok
        and independent
        and vram_state == "estimated_fit"
        and evidence["status"] == "complete"
    ):
        return "high_evidence"
    if quality["status"] in ("known", "partially_known") and vram_state in (
        "estimated_fit",
        "indeterminate_fit",
    ):
        return "moderate_evidence"
    if quality["status"] in ("known", "partially_known") or vram_state == "estimated_fit":
        return "limited_evidence"
    return "insufficient"


@dataclass
class TierRecommendationReport:
    """Per-tier recommendation readiness split into honest categories."""

    tier_gb: int
    strict: list[dict] = field(default_factory=list)
    candidates: list[dict] = field(default_factory=list)
    insufficient: list[dict] = field(default_factory=list)
    ineligible: list[dict] = field(default_factory=list)
    quality_known_fit_unknown: list[str] = field(default_factory=list)
    fit_known_quality_unknown: list[str] = field(default_factory=list)

    def to_payload(self) -> dict:
        return {
            "tier_gb": self.tier_gb,
            "strict_recommendations": len(self.strict),
            "promising_candidates": len(self.candidates),
            "insufficient_evidence": len(self.insufficient),
            "ineligible": len(self.ineligible),
            "strict": self.strict,
            "candidates": self.candidates,
            "insufficient": self.insufficient,
            "quality_known_fit_unknown": sorted(self.quality_known_fit_unknown),
            "fit_known_quality_unknown": sorted(self.fit_known_quality_unknown),
            "note": (
                "Categories are never merged. Zero strict recommendations is reported honestly "
                "rather than backfilled with weak candidates."
            ),
        }


def build_tier_report(
    *,
    tier_gb: int,
    outcomes: list[tuple[dict, RecommendationOutcome, str]],
) -> TierRecommendationReport:
    """Split per-model outcomes into strict/candidate/insufficient for a tier."""
    report = TierRecommendationReport(tier_gb=tier_gb)
    for record, outcome, vram_state in sorted(outcomes, key=lambda item: item[0]["model_id"]):
        eligibility = outcome.eligibility
        if eligibility == "eligible":
            report.strict.append(outcome.to_result(tier_gb=tier_gb))
        elif eligibility == "candidate":
            report.candidates.append(outcome.to_result(tier_gb=tier_gb))
        elif eligibility == "ineligible":
            report.ineligible.append(outcome.to_result(tier_gb=tier_gb))
        else:
            report.insufficient.append(outcome.to_result(tier_gb=tier_gb))

        quality = outcome.domains["quality"]["status"]
        if quality in ("known", "partially_known") and vram_state in (
            "insufficient_evidence",
            "unsupported",
        ):
            report.quality_known_fit_unknown.append(record["model_id"])
        if quality == "unevaluated" and vram_state in ("estimated_fit", "indeterminate_fit"):
            report.fit_known_quality_unknown.append(record["model_id"])
    return report

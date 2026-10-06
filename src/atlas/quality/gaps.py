"""Quality evidence-gap reporting.

Gaps are a feature, not a failure: this report states exactly which evidence
domains are missing so the absence is never mistaken for a weakness.
"""

from __future__ import annotations

from pathlib import Path

from atlas.quality.ingest import load_evaluations
from atlas.quality.sidecars import load_records, sidecar_completeness

GAP_DEFINITIONS = (
    "missing_independent_quality_evidence",
    "missing_quant_retention_evidence",
    "missing_vram_fit_evidence",
    "missing_runtime_evidence",
    "alignment_variant_unevaluated",
    "arabic_quality_unknown",
    "architecture_unresolved",
    "publisher_only_quality",
)


def build_gap_report(repo_root: Path, *, tier_states: dict[str, dict] | None = None) -> dict:
    """Enumerate evidence gaps across the catalog from canonical records."""
    records = load_records(repo_root)
    evaluations = load_evaluations(repo_root)
    by_model: dict[str, list[dict]] = {}
    for evaluation in evaluations.values():
        by_model.setdefault(str(evaluation.get("model_id")), []).append(evaluation)

    tier_states = tier_states or {}
    gaps: dict[str, list[str]] = {name: [] for name in GAP_DEFINITIONS}

    for model_id, record in sorted(records.items()):
        model_results = by_model.get(model_id, [])
        exact = [
            r
            for r in model_results
            if str(r.get("match_status", "")).startswith("exact") and not r.get("superseded")
        ]
        origins = {str(r.get("evaluation_origin")) for r in exact}
        independent = "independent" in origins
        if not independent:
            gaps["missing_independent_quality_evidence"].append(model_id)

        quant = record.get("quantization") or {}
        quant_family = str(quant.get("quant_family") or "unknown")
        quant_name = quant.get("quant_name")
        if quant_family not in ("unknown", "") or quant_name:
            exact_quant_scores = [r for r in exact if r.get("quantization")]
            if not exact_quant_scores:
                gaps["missing_quant_retention_evidence"].append(model_id)

        states = tier_states.get(model_id, {})
        by_tier = states.get("by_tier", {}) if isinstance(states, dict) else {}
        if by_tier and not any(
            str(by_tier.get(str(tier))) in ("estimated_fit", "indeterminate_fit")
            for tier in (4, 8, 12, 16)
        ):
            gaps["missing_vram_fit_evidence"].append(model_id)

        from atlas.catalog.runtime_hints import hints_for_format

        hints = hints_for_format(str(quant.get("format") or "unknown"))
        if not hints:
            gaps["missing_runtime_evidence"].append(model_id)

        alignment = record.get("alignment") or {}
        variant = str(alignment.get("alignment_variant") or "unknown")
        if variant in ("uncensored", "abliterated", "heretic") and not exact:
            gaps["alignment_variant_unevaluated"].append(model_id)

        if not any("arabic" in str(r.get("benchmark_id", "")) for r in exact):
            gaps["arabic_quality_unknown"].append(model_id)

        if str(record.get("architecture") or "unknown") == "unknown":
            gaps["architecture_unresolved"].append(model_id)

        if origins == {"publisher"} and exact:
            gaps["publisher_only_quality"].append(model_id)

    completeness_counts: dict[str, int] = {}
    for record in records.values():
        status = sidecar_completeness(record, repo_root)
        completeness_counts[status] = completeness_counts.get(status, 0) + 1

    return {
        "model_count": len(records),
        "evaluation_count": len(evaluations),
        "gap_definitions": list(GAP_DEFINITIONS),
        "gaps": {name: sorted(set(models)) for name, models in sorted(gaps.items())},
        "gap_counts": {name: len(set(models)) for name, models in sorted(gaps.items())},
        "evidence_sidecar_completeness": completeness_counts,
        "note": (
            "A missing benchmark is an unevaluated axis, never a failed one. Arabic quality is "
            "unknown unless an Arabic-specific external evaluation exists."
        ),
    }

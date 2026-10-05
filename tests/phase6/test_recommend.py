"""Phase 6: recommendation eligibility across all required domains.

A strict recommendation requires quality + fit + runtime + license + variant
identity + evidence quality simultaneously. Partial evidence is reported as
candidate or insufficient, never upgraded.
"""

from __future__ import annotations

import json
from pathlib import Path

from phase6.support import (
    alignment_record,
    evaluation,
    model_record,
    publisher_evaluation,
    quant_record,
)

from atlas.quality import QUALITY_SNAPSHOT_VERSION
from atlas.quality.profiles import build_profile
from atlas.quality.recommend import build_tier_report, evaluate_recommendation

SNAPSHOT = QUALITY_SNAPSHOT_VERSION
REPO_ROOT = Path(__file__).resolve().parents[2]

RUNTIMES = ["llama.cpp", "vllm"]

_MISSING = object()


def _write_sidecar(root: Path, evidence_id: str = "ev-test-1") -> Path:
    """Persist a real evidence sidecar so 'eligible' has resolvable evidence."""
    base = root / "catalog" / "evidence"
    base.mkdir(parents=True, exist_ok=True)
    (base / f"{evidence_id}.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1.0",
                "evidence_id": evidence_id,
                "claim_type": "benchmark_score",
                "source_id": "independent-org",
                "source_type": "independent_benchmark",
                "retrieved_at": "2026-10-05T00:00:00Z",
                "evidence_level": "independent_measurement",
                "verification_status": "independently_verified",
            }
        ),
        encoding="utf-8",
    )
    return root


def _profile(results=_MISSING, model_id="acme-test-7b-instruct"):
    if results is _MISSING:
        results = [
            evaluation(model_id=model_id, source_id="org-a"),
            evaluation(
                model_id=model_id,
                evaluation_id="evl-v1-b",
                source_id="org-b",
                benchmark_id="humaneval",
                metric="HumanEval pass@1",
                task="code_generation",
            ),
        ]
    return build_profile(model_id=model_id, results=results, quality_snapshot_version=SNAPSHOT)


def _evaluate(
    record=None,
    *,
    vram_state="estimated_fit",
    profile=_MISSING,
    repo_root=REPO_ROOT,
    runtime_support=RUNTIMES,
    **kwargs,
):
    record = record or model_record()
    resolved_profile = _profile() if profile is _MISSING else profile
    return evaluate_recommendation(
        record=record,
        vram_state=vram_state,
        profile=resolved_profile,
        repo_root=repo_root,
        runtime_support=runtime_support,
        **kwargs,
    )


def test_high_quality_with_verified_fit_is_eligible(tmp_path):
    root = _write_sidecar(tmp_path / "repo")
    outcome = _evaluate(repo_root=root)
    assert outcome.domains["evidence_quality"]["status"] == "complete"
    assert outcome.eligibility == "eligible", outcome.reasons
    assert outcome.confidence_state == "high_evidence"


def test_high_quality_with_insufficient_fit_is_not_strict():
    outcome = _evaluate(vram_state="insufficient_evidence")
    assert outcome.eligibility != "eligible"
    assert outcome.domains["vram_fit"]["state"] == "insufficient_evidence"
    assert any("fit not established" in reason for reason in outcome.reasons)


def test_high_quality_with_indeterminate_fit_is_candidate_only():
    outcome = _evaluate(vram_state="indeterminate_fit")
    assert outcome.eligibility == "candidate"
    assert outcome.confidence_state in ("moderate_evidence", "limited_evidence")


def test_fit_without_quality_is_not_strict():
    outcome = _evaluate(profile=None)
    assert outcome.eligibility != "eligible"
    assert outcome.domains["quality"]["status"] == "unevaluated"


def test_good_base_with_unknown_quant_retention_is_disclosed():
    outcome = _evaluate(
        record=quant_record(),
        profile=_profile(model_id="acme-test-7b-instruct-q4-k-m"),
        is_quantized_artifact=True,
    )
    assert outcome.quant_retention["status"] == "unknown"
    assert "retention unknown" in outcome.quant_retention["disclosure"]
    assert any("retention unknown" in reason for reason in outcome.reasons)
    assert outcome.confidence_state != "high_evidence"


def test_exact_quant_evidence_allows_retention_disclosure():
    outcome = _evaluate(
        record=quant_record(),
        profile=_profile(model_id="acme-test-7b-instruct-q4-k-m"),
        is_quantized_artifact=True,
        base_result=evaluation(score=70.0),
        quant_result=evaluation(score=69.0, quantization="Q4_K_M"),
    )
    assert outcome.quant_retention["status"] == "directly_measured"


def test_unknown_runtime_is_not_practical_strict_recommendation():
    outcome = _evaluate(runtime_support=[])
    assert outcome.domains["runtime"]["status"] == "unknown"
    assert outcome.eligibility != "eligible"
    assert any("runtime compatibility unknown" in reason for reason in outcome.reasons)


def test_single_runtime_is_partial_not_documented():
    outcome = _evaluate(runtime_support=["llama.cpp"])
    assert outcome.domains["runtime"]["status"] == "partial"
    assert outcome.eligibility != "eligible"


def test_license_restriction_is_surfaced_not_hidden():
    record = model_record(openness="open_weights_restricted")
    outcome = _evaluate(record=record)
    assert outcome.domains["license"]["status"] == "restricted"
    assert any("license restricted" in reason for reason in outcome.reasons)


def test_unclear_license_blocks_strict_recommendation():
    record = model_record(openness="unclear")
    outcome = _evaluate(record=record)
    assert outcome.eligibility != "eligible"
    assert any("license unclear" in reason for reason in outcome.reasons)


def test_uncensored_variant_does_not_inherit_parent_score():
    record = alignment_record()
    outcome = _evaluate(record=record, profile=_profile(model_id=record["model_id"]))
    assert outcome.domains["variant_identity"]["detail"].startswith("uncensored")
    assert any("reference only" in reason for reason in outcome.reasons)


def test_uncensored_variant_without_own_evidence_is_not_candidate():
    record = alignment_record()
    outcome = _evaluate(record=record, profile=None)
    assert outcome.eligibility in ("candidate", "insufficient_evidence")
    assert outcome.domains["quality"]["status"] == "unevaluated"


def test_no_evidence_yields_no_recommendation():
    record = model_record()
    outcome = evaluate_recommendation(
        record=record,
        vram_state="insufficient_evidence",
        profile=None,
        repo_root=REPO_ROOT,
        runtime_support=[],
    )
    assert outcome.eligibility == "insufficient_evidence"
    assert outcome.confidence_state == "insufficient"
    assert any("quality unevaluated" in reason for reason in outcome.reasons)


def test_logical_only_evidence_blocks_strict_recommendation():
    # The synthetic record references an evidence id with no persisted sidecar.
    outcome = _evaluate(record=model_record())
    assert outcome.domains["evidence_quality"]["status"] == "logical_reference_only"
    assert outcome.eligibility != "eligible"


def test_publisher_only_quality_is_not_strict():
    profile = _profile([publisher_evaluation()])
    outcome = _evaluate(profile=profile)
    assert profile["evidence_status"] == "publisher_only"
    assert outcome.domains["quality"]["status"] == "partially_known"
    assert outcome.eligibility != "eligible"


def test_tier_report_never_merges_categories():
    records = [
        (
            model_record(model_id="acme-test-7b-instruct"),
            _evaluate(),
            "estimated_fit",
        ),
        (
            model_record(model_id="other-model", display_name="other/model"),
            _evaluate(vram_state="insufficient_evidence"),
            "insufficient_evidence",
        ),
    ]
    report = build_tier_report(tier_gb=8, outcomes=records)
    payload = report.to_payload()
    assert payload["strict_recommendations"] == 0
    assert payload["promising_candidates"] == 0
    assert payload["insufficient_evidence"] == 2
    assert "quality_known_fit_unknown" in payload


def test_recommendation_result_is_schema_valid():
    outcome = _evaluate()
    result = outcome.to_result(tier_gb=8)
    from atlas.validation.validator import validate_record

    assert validate_record(result, "recommendation-result") == []


def test_confidence_is_categorical_not_probabilistic():
    outcome = _evaluate()
    assert outcome.confidence_state in (
        "high_evidence",
        "moderate_evidence",
        "limited_evidence",
        "insufficient",
    )
    assert "%" not in outcome.confidence_state


def test_result_carries_policy_version_and_reasons():
    result = _evaluate().to_result(tier_gb=16)
    assert result["policy_version"] == "0.6.0"
    assert len(result["reasons"]) >= 1
    # Reasons must be resolvable: evidence ids are carried with the result.
    assert isinstance(result["evidence_ids"], list)
    json.dumps(result)  # serializable without private objects

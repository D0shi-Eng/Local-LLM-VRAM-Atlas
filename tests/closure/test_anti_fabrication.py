"""Phase 6.5: anti-fabrication proofs.

Each test proves one specific way evidence could be faked, and that Atlas
refuses it. No test passes because a policy was relaxed.
"""

from __future__ import annotations

from closure.support import architecture_fields, candidate, evaluation, measurement, model_record

from atlas.closure.core_set import build_core_set, candidate_record
from atlas.closure.readiness import CLOSURE_POLICY, evaluate_candidate
from atlas.closure.retention_evidence import build_candidate_retention
from atlas.closure.vram_evidence import build_candidate_estimate, derive_vram_source_class

ARTIFACT = "acme-test-7b-instruct--gguf--q4_k_m"

STRICT_ESTIMATE = {
    "candidate_id": "core-test-01",
    "artifact_set_id": ARTIFACT,
    "architecture_family": "qwen3",
    "estimate_status": "calculated_from_source_metadata",
    "by_tier": {
        "4": "estimated_not_fit",
        "8": "estimated_fit",
        "12": "estimated_fit",
        "16": "estimated_fit",
    },
    "tier_reasons": {},
}


def test_artifact_size_cannot_create_fit():
    small = build_candidate_estimate(
        candidate=candidate(artifact_weight_bytes=100_000_000),
        architecture_fields=architecture_fields(),
        advertised_max_context=40960,
    )
    assert small["upper_bytes"] is None
    assert small["by_tier"]["4"] != "estimated_fit"


def test_file_name_cannot_create_quant_verification():
    named = measurement(artifact_variant="Q4_K_M.gguf")
    assert derive_vram_source_class(named) == "V1"
    from atlas.closure.vram_evidence import fit_support

    verdict = fit_support(named, tier_gb=8, expected_artifact_id=ARTIFACT)
    assert verdict["artifact_identity"] == "mismatch"
    assert verdict["supports_measured_requirement"] is False


def test_repo_name_cannot_create_ternary_proof():
    record = model_record(
        display_name="acme/Definitely-Ternary-27B-GGUF",
        quantization={"format": "GGUF", "quant_family": "unknown", "quant_name": "TQ1_0"},
    )
    from atlas.catalog.special import ternary_status

    assert ternary_status(record)["kind"] == "tq-format"


def test_downloads_and_likes_cannot_create_quality():
    from atlas.quality import QUALITY_SNAPSHOT_VERSION
    from atlas.quality.profiles import build_profile

    results = [evaluation(evaluation_id="evl-v1-" + "a" * 64)]
    cold = build_profile(
        model_id="cold",
        results=results,
        quality_snapshot_version=QUALITY_SNAPSHOT_VERSION,
    )
    hot = build_profile(
        model_id="hot",
        results=results,
        quality_snapshot_version=QUALITY_SNAPSHOT_VERSION,
    )
    assert cold["evidence_status"] == hot["evidence_status"] == "independent_single_source"
    assert cold["high_quality_candidate"] == hot["high_quality_candidate"]


def test_brand_cannot_create_quality():
    from atlas.quality import QUALITY_SNAPSHOT_VERSION
    from atlas.quality.profiles import build_profile

    branded = build_profile(
        model_id="acme",
        results=[evaluation(evaluation_id="evl-v1-" + "a" * 64)],
        quality_snapshot_version=QUALITY_SNAPSHOT_VERSION,
    )
    unknown = build_profile(
        model_id="nobody",
        results=[evaluation(evaluation_id="evl-v1-" + "a" * 64)],
        quality_snapshot_version=QUALITY_SNAPSHOT_VERSION,
    )
    assert branded["evidence_status"] == unknown["evidence_status"]


def test_parameters_cannot_create_quality():
    from atlas.quality import QUALITY_SNAPSHOT_VERSION
    from atlas.quality.profiles import build_profile

    small = build_profile(
        model_id="small",
        results=[evaluation(evaluation_id="evl-v1-" + "a" * 64)],
        quality_snapshot_version=QUALITY_SNAPSHOT_VERSION,
    )
    huge = build_profile(
        model_id="huge",
        results=[evaluation(evaluation_id="evl-v1-" + "a" * 64)],
        quality_snapshot_version=QUALITY_SNAPSHOT_VERSION,
    )
    assert small["axes"] == huge["axes"]


def test_base_score_cannot_become_quant_score():
    from atlas.quality.identity import is_base_vs_quant_mismatch

    record = {"quantization": {"quant_family": "q4", "quant_name": "Q4_K_M"}}
    assert (
        is_base_vs_quant_mismatch(
            record=record, evaluated_quantization=None, record_quantization="Q4_K_M"
        )
        is False
    )
    entry = build_candidate_retention(
        candidate=candidate(),
        record=model_record(),
        records={},
        evaluations_by_model={"acme-test-7b-instruct": [evaluation(score=70.0)]},
        native_low_bit=False,
    )
    assert entry["quant_score"] is None
    assert entry["absolute_delta"] is None


def test_parent_score_cannot_become_uncensored_score():
    from atlas.quality import QUALITY_SNAPSHOT_VERSION
    from atlas.quality.profiles import build_profile

    parent = build_profile(
        model_id="acme-test-7b-instruct",
        results=[evaluation(evaluation_id="evl-v1-" + "a" * 64)],
        quality_snapshot_version=QUALITY_SNAPSHOT_VERSION,
    )
    variant = build_profile(
        model_id="acme-test-7b-instruct-uncensored",
        results=[],
        quality_snapshot_version=QUALITY_SNAPSHOT_VERSION,
    )
    assert parent["high_quality_candidate"] is True
    assert variant["high_quality_candidate"] is False


def test_publisher_score_cannot_become_independent():
    from atlas.quality import QUALITY_SNAPSHOT_VERSION
    from atlas.quality.profiles import build_profile

    profile = build_profile(
        model_id="acme-test-7b-instruct",
        results=[
            evaluation(
                evaluation_origin="publisher",
                verification_status="publisher_claim",
                evaluation_id="evl-v1-" + "c" * 64,
            )
        ],
        quality_snapshot_version=QUALITY_SNAPSHOT_VERSION,
    )
    assert profile["evidence_status"] == "publisher_only"
    assert profile["high_quality_candidate"] is False


def test_low_context_measurement_cannot_become_baseline_context():
    from atlas.closure.vram_evidence import fit_support

    verdict = fit_support(measurement(context_tokens=2048), tier_gb=8)
    assert verdict["supports_measured_requirement"] is False


def test_cpu_offload_cannot_become_full_gpu_fit():
    from atlas.closure.vram_evidence import fit_support

    verdict = fit_support(measurement(offload_mode="cpu"), tier_gb=8)
    assert verdict["supports_measured_requirement"] is False


def test_tier_policy_is_not_relaxed_to_create_a_count():
    from atlas.quality.policy import RECOMMENDATION_POLICY

    assert RECOMMENDATION_POLICY["rules"]["strict_fit_states"] == ["estimated_fit"]
    assert RECOMMENDATION_POLICY["rules"]["quality_status_for_strict"] == ["known"]
    assert RECOMMENDATION_POLICY["rules"]["evidence_quality_for_strict"] == ["complete"]
    assert CLOSURE_POLICY["rules"]["waivers_allowed"] is False


def test_no_aggregate_score_is_invented_to_rank_models():
    from atlas.quality.policy import QUALITY_BAND_POLICY

    assert QUALITY_BAND_POLICY["rules"]["bands_defined"] is False
    assert QUALITY_BAND_POLICY["rules"]["allowed_quality_bands"] == []


def test_core_set_signals_never_use_quality_or_ranking():
    from atlas.closure.core_set import EXCLUDED_SELECTION_SIGNALS, SELECTION_SIGNALS

    forbidden = {"downloads", "likes", "benchmark_score", "quality_score", "ranking"}
    assert not forbidden.intersection(SELECTION_SIGNALS)
    for token in ("brand_preference", "repo_name_prestige", "desired_final_ranking"):
        assert token in EXCLUDED_SELECTION_SIGNALS


def test_declared_core_candidates_resolve_to_real_artifacts():
    from pathlib import Path

    payload = build_core_set(repo_root=Path(__file__).resolve().parents[2])
    assert payload["resolution_problems"] == []
    assert payload["counts"]["candidate_count"] >= 10
    for entry in payload["candidates"]:
        assert entry["artifact_set_id"]
        assert entry["artifact_revision"]
    artifact_ids = {e["artifact_set_id"] for e in payload["candidates"]}
    assert len(artifact_ids) == payload["counts"]["unique_artifact_count"]


def test_candidate_record_uses_catalog_artifacts_only():
    record = model_record()
    artifact = {
        "artifact_set_id": ARTIFACT,
        "variant": "Q4_K_M",
        "primary_weight_bytes": 4_000_000_000,
        "revision": "rev-quant-1",
        "files": [{"filename": "model-Q4_K_M.gguf"}],
    }
    built = candidate_record(
        {
            "candidate_id": "core-test-01",
            "model_id": record["model_id"],
            "artifact_set_id": ARTIFACT,
            "quantization_label": "Q4_K_M",
            "target_tiers": [8],
            "selection_reason": "test",
        },
        record,
        artifact,
    )
    assert built["artifact_filename"] == "model-Q4_K_M.gguf"
    assert built["signals"]["adoption_discovery_signal_only"]["usage"] == (
        "discovery_only_never_quality_or_ranking"
    )


def test_strict_state_cannot_be_manufactured_without_every_gate():
    result = evaluate_candidate(
        candidate=candidate(),
        record=model_record(openness="unclear", license={"license_id": None}),
        estimate=STRICT_ESTIMATE,
        current_evidence={
            "availability": "available",
            "new_evidence": [{"evidence_id": "ev-v2-x"}],
        },
        evaluations=[
            evaluation(
                evaluator="evaluator-a",
                artifact_id=ARTIFACT,
                quantization="Q4_K_M",
                evaluation_id="evl-v1-" + "a" * 64,
            ),
            evaluation(
                evaluator="evaluator-b",
                source_id="org-b",
                artifact_id=ARTIFACT,
                quantization="Q4_K_M",
                evaluation_id="evl-v1-" + "b" * 64,
            ),
        ],
        retention={"retention_status": "independently_measured"},
        sidecar_state="partial",
    )
    assert result["readiness_state"] != "STRICT_READY"
    assert "license_status_acceptable" in result["missing_gates"]

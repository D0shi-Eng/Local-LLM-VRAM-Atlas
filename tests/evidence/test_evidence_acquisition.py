"""Evidence-acquisition integrity.

These tests pin the rules that decide whether externally found material is
allowed to influence a recommendation at all: origin honesty, exact identity,
comparable retention, scoped VRAM evidence, and sidecar existence.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from atlas.closure.vram_evidence import derive_vram_source_class, fit_support
from atlas.external.acquisition import (
    COMPARABLE_CONTEXT_CONFIGURATION,
    RUNTIME_SCOPED_EVIDENCE_SOURCE_IDS,
    SOURCES_CONSULTED,
    build_payload,
    prism_quality_class,
    runtime_scoped_evidence_ids,
)
from atlas.quality.comparability import comparison_key
from atlas.quality.retention import build_retention
from atlas.validation.validator import validate_record

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def payload() -> dict:
    from atlas.closure.core_set import load_core_set

    core_set = load_core_set(repo_root=REPO_ROOT) or {}
    return build_payload(
        repo_root=REPO_ROOT,
        core_set=core_set,
        bonsai_discovery={"detected": True, "pid": 1, "port": 8080},
        budget={"requests_used": 0},
    )


# --- origin honesty -------------------------------------------------------


def test_publisher_evidence_is_never_classified_independent():
    assert prism_quality_class() == "Q4"
    assert all(s.source_class in ("Q1", "Q2", "Q3", "Q4", "V2", "V3") for s in SOURCES_CONSULTED)


def test_no_consulted_source_claims_to_yield_independent_evidence(payload):
    yielding = [
        s["source_id"]
        for s in payload["sources"]["sources"]
        if s.get("yields_independent_evidence")
    ]
    # Honest state: the bounded search found no independent machine-readable
    # surface. This assertion exists so the claim cannot be quietly dropped.
    assert yielding == []


def test_every_evaluation_is_publisher_origin_with_evidence(payload):
    assert payload["evaluations"], "the acquisition must persist its publisher results"
    for evaluation in payload["evaluations"]:
        assert evaluation["evaluation_origin"] == "publisher"
        assert evaluation["verification_status"] == "publisher_claim"
        assert evaluation["evidence_ids"]
        assert evaluation["match_status"].startswith("exact")


# --- exact identity -------------------------------------------------------


def test_quoted_publisher_label_is_not_rewritten_into_atlas_vocabulary(payload):
    labels = {p["publisher_label"] for p in payload["evidence_conditions"]["prism_packings"]}
    assert labels == {"PTQ1_0", "PQ2_0"}
    assert "TQ1_0" not in labels


def test_catalog_label_discrepancy_is_recorded_not_silently_repaired(payload):
    findings = {f["finding_id"]: f for f in payload["identity_findings"]}
    assert "identity-01-ternary-packing-label" in findings
    finding = findings["identity-01-ternary-packing-label"]
    assert finding["catalog_artifact_variant"] == "TQ1_0"
    assert finding["action_taken"] == "recorded_only"


# --- retention comparability ----------------------------------------------


def test_retention_sides_share_one_comparable_setup(payload):
    evaluations = {e["model_id"]: e for e in payload["evaluations"]}
    base = evaluations["qwen-qwen3-8-27b"]
    quant = evaluations["prism-ml-ternary-bonsai-2-27b-gguf"]
    assert comparison_key(base) == comparison_key(quant)
    assert base["context_configuration"] == COMPARABLE_CONTEXT_CONFIGURATION


def test_publisher_retention_is_not_promoted_to_independent(payload):
    retentions = payload["retentions"]
    assert retentions, "a comparable base-vs-quant pair must produce a retention record"
    for retention in retentions:
        assert retention["retention_status"] in (
            "publisher_measured",
            "directly_measured",
            "partially_comparable",
        )
        assert retention["retention_status"] != "independently_measured"
        assert retention["base_score"] is not None
        assert retention["quant_score"] is not None


def test_retention_without_a_quantized_side_is_never_computed():
    built = build_retention(
        base_release="a",
        quantized_artifact="b",
        quantization="Q4_K_M",
        base_result={"benchmark_id": "x", "score": 10.0, "metric": "m"},
        quant_result=None,
    )
    assert built["retention_status"] == "insufficient_evidence"
    assert built["absolute_delta"] is None
    assert built["relative_delta"] is None


def test_mismatched_settings_block_a_retention_number():
    left = {
        "benchmark_id": "x",
        "benchmark_version": "v1",
        "metric": "m",
        "score_unit": "percent",
        "reasoning_mode": "thinking",
        "tool_mode": None,
        "prompting_mode": None,
        "context_configuration": "a",
        "score": 10.0,
        "metric_direction": "higher_is_better",
        "evaluation_origin": "publisher",
    }
    right = {**left, "benchmark_version": "v2", "score": 9.0}
    built = build_retention(
        base_release="a",
        quantized_artifact="b",
        quantization="Q4_K_M",
        base_result=left,
        quant_result=right,
    )
    assert built["evaluation_settings_match"] is False
    assert built["absolute_delta"] is None
    assert built["retention_status"] == "partially_comparable"


# --- VRAM evidence scope ---------------------------------------------------


def test_documented_kv_memory_is_stored_as_publisher_measurement(payload):
    assert len(payload["measurements"]) == 2
    for measurement in payload["measurements"]:
        assert derive_vram_source_class(measurement) == "V3"


def test_documented_kv_memory_cannot_support_a_baseline_fit(payload):
    for measurement in payload["measurements"]:
        verdict = fit_support(
            measurement,
            tier_gb=8,
            expected_artifact_id=measurement["artifact_variant"],
        )
        assert verdict["supports_measured_requirement"] is False
        assert verdict["hardware_verification"] == "not_performed_by_atlas"
        assert verdict["reasons"]


def test_artifact_size_alone_never_supports_a_fit():
    verdict = fit_support(
        {
            "model_id": "x",
            "evidence_level": "publisher_measurement",
            "measurement_method": "documented",
            "reported_vram_bytes": 10**6,
            "context_tokens": 8192,
            "offload_mode": "full",
            "runtime_version": "b1",
        },
        tier_gb=8,
    )
    assert verdict["supports_measured_requirement"] is False


# --- sidecars and validation ----------------------------------------------


def test_every_new_evidence_record_conforms_to_the_evidence_schema(payload):
    assert payload["evidence"]
    for record in payload["evidence"]:
        assert validate_record(record, "evidence") == []


def test_every_new_evaluation_conforms_to_the_evaluation_schema(payload):
    for record in payload["evaluations"]:
        assert validate_record(record, "evaluation-result") == []


def test_runtime_scoped_evidence_is_declared_and_owned_by_no_record(payload):
    scoped = runtime_scoped_evidence_ids(payload["evidence"])
    assert len(scoped) == len(RUNTIME_SCOPED_EVIDENCE_SOURCE_IDS)


def test_persisted_sidecars_are_on_disk(payload):
    for record in payload["evidence"]:
        path = REPO_ROOT / "catalog" / "evidence" / f"{record['evidence_id']}.json"
        assert path.is_file(), record["evidence_id"]
        persisted = json.loads(path.read_text(encoding="utf-8"))
        assert persisted["evidence_id"] == record["evidence_id"]


def test_no_runtime_overhead_constant_was_invented(payload):
    finding = payload["runtime_overhead_finding"]
    assert finding["answer"] == "no_published_bound"
    body = json.dumps(finding)
    for token in ("10%", "+500", "+1gb", "typical overhead"):
        assert token not in body.lower()


def test_declared_budget_is_recorded(payload):
    assert payload["sources"]["declared_request_ceiling"] == 300
    assert payload["sources"]["methods_allowed"] == ["GET", "HEAD"]
    assert payload["sources"]["weight_payloads_reachable"] is False
    assert payload["sources"]["redirects_followed"] is False
    assert payload["bonsai_existing_server"]["diagnostic_inference_requests"] == 0

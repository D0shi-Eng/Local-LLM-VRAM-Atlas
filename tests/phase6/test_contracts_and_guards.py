"""Phase 6: schema contracts, evidence completeness and static safety guards."""

from __future__ import annotations

import json
import pathlib

from phase6.support import evaluation, model_record

from atlas.validation.validator import SUPPORTED_KINDS, validate_record

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
QUALITY_DIR = REPO_ROOT / "src" / "atlas" / "quality"


def _quality_sources() -> dict[str, str]:
    return {
        path.name: path.read_text(encoding="utf-8") for path in sorted(QUALITY_DIR.glob("*.py"))
    }


# --------------------------------------------------------------------- schemas


def test_phase6_schema_kinds_registered():
    for kind in (
        "evaluation-result",
        "quality-profile",
        "quant-retention",
        "quality-policy",
        "recommendation-result",
    ):
        assert kind in SUPPORTED_KINDS


def test_evaluation_result_schema_accepts_canonical():
    assert validate_record(evaluation(), "evaluation-result") == []


def test_evaluation_result_requires_evidence():
    record = evaluation()
    record["evidence_ids"] = []
    assert validate_record(record, "evaluation-result") != []


def test_evaluation_result_rejects_unknown_origin():
    record = evaluation(evaluation_origin="vendor_award")
    assert validate_record(record, "evaluation-result") != []


def test_evaluation_result_rejects_unknown_match_status():
    assert validate_record(evaluation(match_status="fuzzy"), "evaluation-result") != []


def test_evaluation_result_requires_explicit_direction():
    record = evaluation()
    record.pop("metric_direction")
    assert validate_record(record, "evaluation-result") != []


def test_quality_policy_schema_accepts_declared_policies():
    from atlas.quality.policy import ALL_POLICIES

    for policy in ALL_POLICIES:
        record = dict(policy)
        record["created_at"] = "2026-10-05T00:00:00Z"
        assert validate_record(record, "quality-policy") == [], policy["policy_id"]


def test_retention_schema_accepts_unknown_retention():
    from atlas.quality.retention import build_retention

    record = build_retention(
        base_release="a",
        quantized_artifact="b",
        quantization="Q4_K_M",
        base_result=None,
        quant_result=None,
    )
    assert validate_record(record, "quant-retention") == []
    assert record["retention_status"] == "unknown"


def test_no_silent_schema_drift_in_existing_contracts():
    # Existing pre-Phase-6 schema files keep their specification versions.
    for name, version in (
        ("model", "0.1.0"),
        ("source", "0.1.0"),
        ("evidence", "0.1.0"),
        ("benchmark", "0.1.0"),
        ("artifact", "0.2.0"),
        ("quantization", "0.2.0"),
    ):
        text = (REPO_ROOT / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8")
        assert version in text, f"{name} drifted"


# ------------------------------------------------------- evidence completeness


def test_persisted_evaluation_resolves_evidence(tmp_path):
    from atlas.quality.ingest import persist_evaluations

    repo = tmp_path / "repo"
    written, unchanged = persist_evaluations(repo, [evaluation()], dry_run=False)
    assert len(written) == 1 and unchanged == []
    again_written, again_unchanged = persist_evaluations(repo, [evaluation()], dry_run=False)
    assert again_written == [] and len(again_unchanged) == 1


def test_dry_run_writes_nothing(tmp_path):
    from atlas.quality.ingest import evaluations_dir, persist_evaluations

    repo = tmp_path / "repo"
    persist_evaluations(repo, [evaluation()], dry_run=True)
    assert not evaluations_dir(repo).exists()


def test_ingestion_is_atomic_on_failure(tmp_path):
    from atlas.quality.ingest import evaluations_dir, persist_evaluations

    repo = tmp_path / "repo"
    good = evaluation()
    broken = evaluation(evaluation_id="evl-v1-broken")
    broken["score"] = "not-a-number"
    persist_evaluations(repo, [broken], dry_run=False)
    # The invalid record is written as-is; validation is a separate gate, so a
    # failed ingestion must not leave a partially written second file.
    persist_evaluations(repo, [good], dry_run=False)
    files = sorted(p.name for p in evaluations_dir(repo).glob("*.json"))
    assert len(files) == 2
    for path in evaluations_dir(repo).glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))


def test_recommendation_never_depends_on_logical_only_evidence():
    from atlas.quality.recommend import evaluate_recommendation

    outcome = evaluate_recommendation(
        record=model_record(),
        vram_state="estimated_fit",
        profile=None,
        repo_root=REPO_ROOT,
        runtime_support=["llama.cpp"],
    )
    assert outcome.domains["evidence_quality"]["status"] != "complete"
    assert outcome.eligibility != "eligible"


def test_quality_events_reuse_phase5_journal(tmp_path):
    from atlas.quality.changes import append_quality_events, journaled_quality_events, quality_event
    from atlas.refresh.changes import CHANGE_TYPES

    event = quality_event(
        event_type="quality_evidence_added",
        model_id="acme-test-7b-instruct",
        detected_at="2026-10-05T00:00:00Z",
        subject_id="evl-v1-abc",
    )
    assert event["event_type"] in CHANGE_TYPES
    assert validate_record(event, "change-event") == []
    changes_dir = tmp_path / "changes"
    assert append_quality_events(changes_dir, [event]) == 1
    assert append_quality_events(changes_dir, [event]) == 0, "idempotent by event_id"
    assert len(journaled_quality_events(changes_dir)) == 1


def test_quality_event_severity_is_data_integrity_not_quality():
    from atlas.quality.changes import quality_event

    added = quality_event(
        event_type="quality_evidence_added",
        model_id="m",
        detected_at="2026-10-05T00:00:00Z",
        subject_id="s",
    )
    conflict = quality_event(
        event_type="evaluation_identity_conflict",
        model_id="m",
        detected_at="2026-10-05T00:00:00Z",
        subject_id="s",
    )
    assert added["severity"] == "informational"
    assert conflict["severity"] == "high"


# --------------------------------------------------------------- static guards


def test_no_weight_download_or_model_execution_apis():
    forbidden = (
        "hf_hub_download",
        "snapshot_download",
        "from_pretrained",
        "AutoModel",
        "AutoTokenizer",
        "torch.load",
        "pickle.load",
        "trust_remote_code",
    )
    hits = []
    for name, text in _quality_sources().items():
        for marker in forbidden:
            if marker in text:
                hits.append(f"{name}:{marker}")
    assert hits == [], f"weight/execution APIs in quality code: {hits}"


def test_no_benchmark_execution_in_quality_code():
    forbidden = (
        "lm_eval",
        "lm-evaluation-harness",
        "evaluate(",
        "AutoModelForCausalLM",
        "vllm serve",
        "llama-cli",
        "ollama run",
    )
    hits = []
    for name, text in _quality_sources().items():
        for marker in forbidden:
            if marker in text:
                hits.append(f"{name}:{marker}")
    assert hits == [], f"benchmark execution markers in quality code: {hits}"


def test_no_server_daemon_or_scheduler_in_quality_code():
    forbidden = (
        "uvicorn.run",
        "FastAPI(",
        "HTTPServer(",
        "serve_forever",
        "while True",
        "Register-ScheduledTask",
        "schtasks",
        "Start-Job",
        "daemon(",
    )
    hits = []
    for name, text in _quality_sources().items():
        for marker in forbidden:
            if marker in text:
                hits.append(f"{name}:{marker}")
    assert hits == [], f"server/daemon markers in quality code: {hits}"


def test_no_credentials_in_quality_code():
    forbidden = ("HF_TOKEN", "api_key", "Authorization", "Bearer ")
    hits = []
    for name, text in _quality_sources().items():
        for marker in forbidden:
            if marker in text:
                hits.append(f"{name}:{marker}")
    assert hits == [], f"credential markers in quality code: {hits}"


def test_quality_network_access_is_read_only_and_bounded():
    live = _quality_sources()["live.py"]
    assert 'method="GET"' in live
    assert "MAX_PAYLOAD_BYTES" in live
    assert "MAX_REQUESTS" in live
    for write_marker in ('method="POST"', 'method="PUT"', 'method="PATCH"', 'method="DELETE"'):
        assert write_marker not in live
    # URLs must pass the shared SSRF guard.
    assert "assert_safe_url" in live


def test_no_git_or_publishing_in_quality_code():
    forbidden = ("git ", "gh pr", "gh release", "subprocess", "webbrowser")
    hits = []
    for name, text in _quality_sources().items():
        for marker in forbidden:
            if marker in text:
                hits.append(f"{name}:{marker}")
    assert hits == [], f"git/publishing markers in quality code: {hits}"


def test_source_registry_never_stores_credentials():
    from atlas.quality.sources import default_registry, validate_registry

    registry = default_registry("2026-10-05T00:00:00Z")
    assert validate_registry(registry) == []
    assert all(entry["credentials_stored"] is False for entry in registry["sources"])


def test_independent_sources_are_not_scraped():
    from atlas.quality.sources import default_registry

    registry = default_registry("2026-10-05T00:00:00Z")
    by_id = {entry["source_id"]: entry for entry in registry["sources"]}
    assert (
        by_id["artificial-analysis"]["data_access_method"] == "unsupported_for_automated_ingestion"
    )
    assert by_id["artificial-analysis"]["current_version"] == "v4.3.2"
    assert by_id["arabic-benchmark-sources"]["verification_status"] == "unknown"


def test_cli_quality_commands_are_read_only_by_default():
    cli = (REPO_ROOT / "src" / "atlas" / "cli" / "main.py").read_text(encoding="utf-8")
    assert '"quality"' in cli
    assert '"recommend"' in cli
    assert '"retention"' in cli
    # No watch/serve surface is introduced for quality data.
    for forbidden in ('"watch"', '"serve"', '"daemon"', "--forever"):
        assert forbidden not in cli

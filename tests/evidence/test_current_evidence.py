"""Current provenance reacquisition integrity.

Historical evidence sidecars are never fabricated, new current evidence is
persisted, historical identifiers survive untouched, revisions stay distinct,
and re-running never duplicates anything.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from builders.candidates import STAMP, FakeHubClient, candidate, model_record

from atlas.closure.current_evidence import (
    AUTHENTICATION_REQUIRED,
    SOURCE_UNAVAILABLE,
    language_model_fields,
    probe_repository,
    reacquire_candidate,
    resolve_base_chain,
    write_current_evidence,
)
from atlas.evidence_ids import generate_evidence_id_v2, is_v2_evidence_id
from atlas.quality.sidecars import sidecar_completeness

LEGACY_EVIDENCE_ID = "acme-test-7b-instruct-ev-license-license-id"


def _client() -> FakeHubClient:
    return FakeHubClient(
        repos={
            "acme/Test-7B-Instruct": {
                "sha": "newsha1111111111111111111111111111111111",
                "lastModified": "2026-09-01T00:00:00+00:00",
                "gated": False,
                "disabled": False,
                "card_data": {"license": "apache-2.0"},
                "config": {"architectures": ["Qwen3ForCausalLM"], "model_type": "qwen3"},
            }
        },
        configs={
            "acme/Test-7B-Instruct": {
                "architectures": ["Qwen3ForCausalLM"],
                "model_type": "qwen3",
                "num_hidden_layers": 36,
                "num_attention_heads": 32,
                "num_key_value_heads": 8,
                "head_dim": 128,
                "max_position_embeddings": 40960,
            }
        },
    )


def _reacquire(client: FakeHubClient | None = None) -> dict:
    return reacquire_candidate(
        candidate=candidate(),
        record=model_record(),
        records_by_repo={},
        client=client or _client(),
    )


def test_historical_missing_sidecar_stays_unavailable(tmp_path: Path):
    record = model_record()
    repo = tmp_path
    (repo / "catalog" / "models").mkdir(parents=True)
    (repo / "catalog" / "evidence").mkdir(parents=True)
    assert sidecar_completeness(record, repo) == "logical_reference_only"


def test_new_current_evidence_has_a_persisted_sidecar(tmp_path: Path):
    repo = tmp_path
    (repo / "catalog" / "models").mkdir(parents=True)
    (repo / "catalog" / "evidence").mkdir(parents=True)
    entry = _reacquire()
    assert entry["new_evidence"], "reacquisition must produce new evidence records"
    outcome = write_current_evidence(repo_root=repo, payload={"entries": [entry]}, dry_run=False)
    assert outcome["index_written"] is True
    for evidence_id in outcome["new_sidecars_written"]:
        sidecar = repo / "catalog" / "evidence" / f"{evidence_id}.json"
        assert sidecar.is_file()
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        assert payload["evidence_id"] == evidence_id
        assert payload["retrieved_at"] == STAMP


def test_historical_evidence_id_is_preserved(tmp_path: Path):
    repo = tmp_path
    (repo / "catalog" / "models").mkdir(parents=True)
    (repo / "catalog" / "evidence").mkdir(parents=True)
    entry = _reacquire()
    outcome = write_current_evidence(repo_root=repo, payload={"entries": [entry]}, dry_run=False)
    new_ids = set(outcome["new_sidecars_written"])
    assert LEGACY_EVIDENCE_ID not in new_ids
    assert not (repo / "evidence" / f"{LEGACY_EVIDENCE_ID}.json").exists()
    record = model_record()
    assert LEGACY_EVIDENCE_ID in record["verification"]["evidence_ids"]


def test_new_evidence_uses_v2_ids_distinct_from_history():
    entry = _reacquire()
    ids = [str(e["evidence_id"]) for e in entry["new_evidence"]]
    assert ids
    for evidence_id in ids:
        assert is_v2_evidence_id(evidence_id)
    assert not any(evidence_id.startswith("acme-test-7b-instruct-ev-") for evidence_id in ids)


def test_new_evidence_is_revision_distinguished():
    first = _reacquire()
    assert first["reacquired_revision"].startswith("newsha")
    other = generate_evidence_id_v2(
        source_id=first["new_evidence"][0]["source_id"],
        repo_id="acme/Test-7B-Instruct",
        resolved_revision="othersha22222222222222222222222222222222",
        claim_type=first["new_evidence"][0]["claim_type"],
        field_path=first["new_evidence"][0]["field_path"],
        artifact_id=None,
    )
    assert other != first["new_evidence"][0]["evidence_id"]


def test_new_current_evidence_does_not_masquerade_as_history():
    entry = _reacquire()
    assert entry["historical_sidecar_state"] == "evidence_sidecar_unavailable"
    assert entry["current_evidence_state"] == "available"
    for record in entry["new_evidence"]:
        assert record["source_id"].endswith("-current-src")
        assert "historical" not in record["notes"].lower()


def test_duplicate_current_evidence_is_deduped(tmp_path: Path):
    repo = tmp_path
    (repo / "catalog" / "models").mkdir(parents=True)
    (repo / "catalog" / "evidence").mkdir(parents=True)
    entry = _reacquire()
    payload = {"entries": [entry, entry]}
    first = write_current_evidence(repo_root=repo, payload=payload, dry_run=False)
    second = write_current_evidence(repo_root=repo, payload=payload, dry_run=False)
    assert len(first["new_sidecars_written"]) == len(set(first["new_sidecars_written"]))
    assert set(second["new_sidecars_unchanged"]) == set(first["new_sidecars_written"])
    assert second["new_sidecars_written"] == []
    files = sorted(p.name for p in (repo / "catalog" / "evidence").glob("*.json"))
    assert len(files) == len(set(files))


def test_unreadable_source_is_recorded_not_substituted():
    client = FakeHubClient(repos={}, configs={})
    probe = probe_repository("acme/Missing", client=client)
    assert probe.status == SOURCE_UNAVAILABLE
    assert probe.config is None


def test_gated_source_is_recorded_as_authentication_required():
    class Gated(FakeHubClient):
        def model_info(self, repo_id: str) -> dict:
            raise type("GatedRepoError", (Exception,), {})("gated repository")

    probe = probe_repository("acme/Gated", client=Gated(repos={}, configs={}))
    assert probe.status == AUTHENTICATION_REQUIRED


def test_declared_base_model_is_followed_and_disclosed():
    client = FakeHubClient(
        repos={
            "acme/Test-7B-GGUF": {"sha": "ggufsha", "config": {}},
            "acme/Test-7B-Base": {"sha": "basesha", "config": {}},
        },
        configs={
            "acme/Test-7B-Base": {
                "architectures": ["Qwen3ForCausalLM"],
                "model_type": "qwen3",
                "num_hidden_layers": 36,
                "num_key_value_heads": 8,
                "head_dim": 128,
                "hidden_size": 4096,
            }
        },
    )
    record = model_record(display_name="acme/Test-7B-GGUF", base_models=["acme/Test-7B-Base"])
    entry = reacquire_candidate(
        candidate=candidate(),
        record=record,
        records_by_repo={},
        client=client,
    )
    assert entry["configuration_evidence_origin"] == "declared_base_model_config"
    assert entry["configuration_repo"] == "acme/Test-7B-Base"
    assert entry["base_model_chain_used"] == ["acme/Test-7B-Base"]


def test_repository_name_is_never_used_as_lineage():
    record = model_record(display_name="acme/Definitely-Llama-3.1-70B-GGUF", base_models=[])
    assert resolve_base_chain(record, {}) == []
    entry = reacquire_candidate(
        candidate=candidate(),
        record=record,
        records_by_repo={},
        client=_client(),
    )
    assert entry["architecture_fields"] == {}
    assert "architecture_cache_inputs_unavailable" in entry["issues"]


def test_multimodal_wrapper_scope_is_disclosed():
    fields = {
        "architectures": ["Qwen3_5ForConditionalGeneration"],
        "vision_config": {"depth": 27},
        "text_config": {
            "num_hidden_layers": 64,
            "num_key_value_heads": 4,
            "head_dim": 256,
            "hidden_size": 5120,
            "max_position_embeddings": 262144,
        },
    }
    language = language_model_fields(fields)
    assert language["num_hidden_layers"] == 64
    assert "vision_config" not in language


def test_request_budget_is_enforced():
    client = FakeHubClient(repos={"acme/Test-7B-Instruct": {"sha": "s", "config": {}}}, configs={})
    budget = {"requests": 0, "bytes": 0}
    from atlas.closure.current_evidence import MAX_REQUESTS

    budget["requests"] = MAX_REQUESTS
    probe = probe_repository("acme/Test-7B-Instruct", client=client, budget=budget)
    assert probe.status == SOURCE_UNAVAILABLE
    assert probe.detail == "request budget exhausted"


@pytest.mark.parametrize("weight_suffix", [".gguf", ".safetensors", ".bin", ".onnx"])
def test_weight_payload_is_never_reachable(weight_suffix: str):
    from atlas.intake.hf_client import assert_not_weight_path_allowed_for_inventory
    from atlas.intake.weight_guard import is_weight_path
    from atlas.security.metadata_fetch import allowed_metadata_url

    assert is_weight_path(f"model{weight_suffix}")
    assert_not_weight_path_allowed_for_inventory(f"model{weight_suffix}")
    assert not allowed_metadata_url(
        f"https://huggingface.co/acme/Test-7B-Instruct/raw/main/model{weight_suffix}"
    )

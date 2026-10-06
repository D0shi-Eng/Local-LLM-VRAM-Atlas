"""Shared offline synthetic record builders for evidence-closure tests.

No network, no model, no GPU, no benchmark execution, no server. Every score
here is fabricated test data whose only purpose is to exercise policy logic.
"""

from __future__ import annotations

STAMP = "2026-10-05T00:00:00Z"

SRC_CONFIG = "https://huggingface.co/acme/Test-7B-Instruct"


class FakeHubClient:
    """Offline stand-in for the anonymous public metadata reader."""

    def __init__(
        self,
        *,
        repos: dict[str, dict] | None = None,
        configs: dict[str, dict] | None = None,
    ):
        self.repos = repos or {}
        self.configs = configs or {}
        self.calls: list[str] = []

    def model_info(self, repo_id: str) -> dict:
        self.calls.append(repo_id)
        if repo_id not in self.repos:
            raise RuntimeError("404: repository not found")
        return dict(self.repos[repo_id])

    def config_for(self, repo_id: str) -> dict:
        self.calls.append(f"{repo_id}:config")
        return dict(self.configs.get(repo_id, {}))


def candidate(**overrides) -> dict:
    """A minimal declared Core candidate with an exact artifact identity."""
    payload = {
        "candidate_id": "core-test-01",
        "model_id": "acme-test-7b-instruct",
        "artifact_set_id": "acme-test-7b-instruct--gguf--q4_k_m",
        "quantization_label": "Q4_K_M",
        "artifact_variant": "Q4_K_M",
        "artifact_weight_bytes": 4_000_000_000,
        "artifact_revision": "rev-quant-1",
        "container_format": "GGUF",
        "target_tiers": [8],
        "alignment_variant": "unknown",
        "license_id": "apache-2.0",
        "signals": {"runtime_relevance_documented": ["llama.cpp"]},
    }
    payload.update(overrides)
    return payload


def model_record(**overrides) -> dict:
    """Minimal canonical-ish model record with a resolvable repo identity."""
    record = {
        "model_id": "acme-test-7b-instruct",
        "display_name": "acme/Test-7B-Instruct",
        "creator": "acme",
        "architecture": "Qwen3ForCausalLM",
        "architecture_type": "dense",
        "openness": "open_weights_permissive",
        "verification": {
            "status": "publisher_claim",
            "evidence_ids": ["acme-test-7b-instruct-ev-license-license-id"],
        },
        "catalog_status": "verified",
        "lifecycle_status": "active",
        "license": {"license_id": "apache-2.0", "verification_status": "publisher_claim"},
        "quantization": {
            "format": "GGUF",
            "quant_family": "q4",
            "quant_name": "Q4_K_M",
            "source_revision": "rev-quant-1",
        },
        "alignment": {"alignment_variant": "unknown"},
        "popularity": {"downloads": 500_000, "likes": 900, "captured_at": STAMP},
        "total_parameters_b": 7.0,
        "base_models": [],
        "release_date": "2025-03-01",
    }
    record.update(overrides)
    return record


def measurement(**overrides) -> dict:
    """A fully configured external VRAM measurement."""
    payload = {
        "schema_version": "0.3.0",
        "measurement_id": "m-001",
        "model_id": "acme-test-7b-instruct",
        "revision": "rev-quant-1",
        "artifact_variant": "acme-test-7b-instruct--gguf--q4_k_m",
        "runtime": "llama.cpp",
        "runtime_version": "b4000",
        "backend": "CUDA",
        "gpu": "RTX 4090",
        "gpu_vram": "24 GiB",
        "driver": "550.54",
        "os": "Windows 11",
        "system_ram": "64 GiB",
        "context_tokens": 8192,
        "batch_or_sequences": 1,
        "kv_format": "fp16",
        "offload_mode": "full",
        "reported_vram_bytes": 6_700_000_000,
        "measurement_stage": "peak",
        "measurement_method": "nvidia_smi",
        "source": "https://example.org/vram-report",
        "evidence_level": "independent_measurement",
        "observed_at": STAMP,
    }
    payload.update(overrides)
    return payload


def evaluation(**overrides) -> dict:
    """Minimal independent evaluation result with explicit identity."""
    payload = {
        "schema_version": "0.6.0",
        "evaluation_id": "evl-v1-" + "0" * 64,
        "model_id": "acme-test-7b-instruct",
        "model_revision": "rev-base-1",
        "artifact_id": None,
        "quantization": None,
        "benchmark_id": "mmlu",
        "benchmark_name": "MMLU",
        "benchmark_version": "v1",
        "suite_version": "harness-1.2",
        "task": "multiple_choice",
        "metric": "MMLU accuracy",
        "metric_direction": "higher_is_better",
        "score": 70.0,
        "score_unit": "percent",
        "reasoning_mode": "non-reasoning",
        "tool_mode": "no_tools",
        "prompting_mode": "zero-shot",
        "context_configuration": "8192",
        "evaluation_origin": "independent",
        "verification_status": "independently_verified",
        "evaluator": "independent-org-a",
        "evaluation_date": "2026-01-10",
        "source_id": "independent-org-a",
        "source_url": "https://example.org/a",
        "source_observed_at": STAMP,
        "evidence_ids": ["ev-current-1"],
        "match_status": "exact",
        "superseded": False,
        "superseded_by": None,
        "notes": None,
    }
    payload.update(overrides)
    return payload


def architecture_fields(**overrides) -> dict:
    """Standard-GQA architecture inputs as a publisher would declare them."""
    fields = {
        "architectures": ["Qwen3ForCausalLM"],
        "model_type": "qwen3",
        "num_hidden_layers": 36,
        "num_attention_heads": 32,
        "num_key_value_heads": 8,
        "head_dim": 128,
        "hidden_size": 4096,
        "max_position_embeddings": 40960,
        "use_sliding_window": False,
    }
    fields.update(overrides)
    return fields

"""Phase 3: canonical architecture resolution from synthetic metadata only."""

from atlas.archinfo.hf_config import resolve_canonical
from atlas.archinfo.normalize import classify_attention, derive_head_dim


def _llama_config(**overrides):
    config = {
        "model_type": "llama",
        "architectures": ["LlamaForCausalLM"],
        "hidden_size": 4096,
        "intermediate_size": 14336,
        "num_hidden_layers": 32,
        "num_attention_heads": 32,
        "num_key_value_heads": 8,
        "vocab_size": 128256,
        "max_position_embeddings": 131072,
        "tie_word_embeddings": False,
    }
    config.update(overrides)
    return config


def test_standard_dense_transformer_resolved():
    record, plan = resolve_canonical(
        config=_llama_config(),
        requested_revision="main",
        resolved_revision="abc123",
        retrieved_at="2026-10-05T00:00:00Z",
    )
    assert record.architecture_family == "llama"
    assert record.model_type == "llama"
    assert record.num_hidden_layers == 32
    assert record.num_key_value_heads == 8
    assert record.head_dim == 128
    assert record.head_dim_source == "calculated"
    assert record.attention_type == "gqa"
    assert record.resolution_status == "resolved"
    assert record.resolved_revision == "abc123"
    assert plan is None


def test_explicit_head_dim_wins_over_calculation():
    record, _ = resolve_canonical(config=_llama_config(head_dim=64))
    assert record.head_dim == 64
    assert record.head_dim_source == "explicit"


def test_calculated_head_dim_marked():
    value, kind = derive_head_dim(4096, 32, None)
    assert (value, kind) == (128, "calculated")
    # Inexact division never calculates.
    assert derive_head_dim(4096, 30, None) == (None, None)
    # Explicit always wins.
    assert derive_head_dim(4096, 32, 64) == (64, "explicit")


def test_attention_kinds():
    assert classify_attention(32, 32) == "mha"
    assert classify_attention(32, 8) == "gqa"
    assert classify_attention(32, 1) == "mqa"
    assert classify_attention(32, None) == "unknown"
    assert classify_attention(None, 8) == "unknown"


def test_mqa_single_kv_head():
    record, _ = resolve_canonical(
        config=_llama_config(num_attention_heads=16, num_key_value_heads=1)
    )
    assert record.attention_type == "mqa"


def test_moe_and_shared_experts():
    config = {
        "model_type": "qwen3_moe",
        "hidden_size": 2048,
        "num_hidden_layers": 48,
        "num_attention_heads": 32,
        "num_key_value_heads": 4,
        "num_experts": 128,
        "num_experts_per_tok": 8,
        "num_shared_experts": 2,
        "moe_intermediate_size": 768,
        "head_dim": 128,
    }
    record, _ = resolve_canonical(config=config)
    assert record.num_experts == 128
    assert record.num_experts_per_token == 8
    assert record.num_shared_experts == 2
    assert record.moe_intermediate_size == 768


def test_sliding_window_resolved():
    record, _ = resolve_canonical(
        config={
            "model_type": "mistral",
            "hidden_size": 4096,
            "num_hidden_layers": 32,
            "num_attention_heads": 32,
            "num_key_value_heads": 8,
            "sliding_window": 4096,
            "max_position_embeddings": 131072,
        }
    )
    assert record.sliding_window == 4096


def test_nested_text_config_boundary():
    config = {
        "model_type": "llama",
        "vision_config": {"hidden_size": 1024, "num_hidden_layers": 24},
        "text_config": dict(_llama_config()),
    }
    record, _ = resolve_canonical(config=config)
    # Language component wins; vision encoder never leaks into LM fields.
    assert record.hidden_size == 4096
    assert record.num_hidden_layers == 32
    assert any("text_config" in warning for warning in record.warnings)


def test_conflicting_sources_preserved():
    record, _ = resolve_canonical(
        config=_llama_config(num_key_value_heads=8),
        gguf_metadata={"llama.attention.head_count_kv": 4},
    )
    assert record.conflict_detected is True
    assert record.conflict_detail is not None
    # First evidence (config tier) wins; GGUF disagreement is preserved.
    assert record.num_key_value_heads == 8


def test_source_precedence_config_beats_card():
    record, _ = resolve_canonical(
        config=_llama_config(num_hidden_layers=32),
        card={"num_hidden_layers": 28},
    )
    assert record.num_hidden_layers == 32
    assert record.conflict_detected is True


def test_revision_provenance_on_fields():
    record, _ = resolve_canonical(
        config=_llama_config(),
        requested_revision="main",
        resolved_revision="deadbeef",
        retrieved_at="2026-10-05T00:00:00Z",
    )
    evidence = record.field_evidence("num_hidden_layers")
    assert evidence is not None
    assert evidence.resolved_revision == "deadbeef"
    assert evidence.retrieved_at == "2026-10-05T00:00:00Z"
    assert record.requested_revision == "main"


def test_missing_fields_partial_not_zero():
    record, _ = resolve_canonical(config={"model_type": "llama", "hidden_size": 4096})
    assert record.num_hidden_layers is None
    assert record.num_key_value_heads is None
    assert record.resolution_status in ("partial", "insufficient_evidence")
    assert "num_hidden_layers" in record.unknown_fields()


def test_empty_metadata_insufficient():
    record, _ = resolve_canonical()
    assert record.resolution_status == "insufficient_evidence"
    assert record.architecture_family == "unknown"


def test_mla_unsupported_path():
    from atlas.archinfo.capabilities import assess_capabilities

    capabilities = assess_capabilities(architecture_family="mla")
    assert capabilities.standard_kv_model == "unsupported"
    assert capabilities.mla_cache_model == "unsupported"


def test_ssm_unsupported_path():
    record, _ = resolve_canonical(
        config={
            "model_type": "mamba",
            "d_model": 2560,
            "n_layer": 64,
            "d_state": 16,
            "d_conv": 4,
            "expand": 2,
            "vocab_size": 50280,
        }
    )
    assert record.state_size == 16
    assert record.resolution_status == "unsupported"


def test_hybrid_refused_as_standard():
    from atlas.archinfo.capabilities import assess_capabilities

    capabilities = assess_capabilities(architecture_family="hybrid")
    assert capabilities.standard_kv_model == "unsupported"


def test_encoder_decoder_refuses_decoder_formula():
    record, _ = resolve_canonical(
        config={
            "model_type": "bart",
            "d_model": 1024,
            "encoder_layers": 12,
            "decoder_layers": 12,
            "is_encoder_decoder": True,
        }
    )
    assert record.is_encoder_decoder is True
    assert record.resolution_status == "unsupported"


def test_custom_remote_architecture_partial():
    record, _ = resolve_canonical(
        config=dict(
            _llama_config(),
            auto_map={"AutoModelForCausalLM": "custom.Model"},
        )
    )
    assert record.custom_remote_architecture is True
    assert record.resolution_status == "partial"


def test_gguf_metadata_maps_canonical_keys():
    record, _ = resolve_canonical(
        gguf_metadata={
            "general.architecture": "llama",
            "llama.embedding_length": 4096,
            "llama.block_count": 32,
            "llama.attention.head_count": 32,
            "llama.attention.head_count_kv": 8,
            "llama.feed_forward_length": 14336,
            "llama.context_length": 131072,
        }
    )
    assert record.architecture_family == "llama"
    assert record.hidden_size == 4096
    assert record.num_hidden_layers == 32
    assert record.num_key_value_heads == 8

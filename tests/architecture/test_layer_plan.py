"""Layer Plan: per-layer truth wins over flattened globals."""

import pytest

from atlas.archinfo.hf_config import resolve_canonical
from atlas.archinfo.layer_plan import attention_layer_count, build_layer_plan


def _heterogeneous_config():
    return {
        "model_type": "llama",
        "hidden_size": 4096,
        "num_hidden_layers": 4,
        "num_attention_heads": 32,
        "num_key_value_heads": 8,
        "head_dim": 128,
        "layers": [
            {
                "layer_type": "attention",
                "attention_present": True,
                "num_attention_heads": 32,
                "num_key_value_heads": 8,
                "head_dim": 128,
            },
            {
                "layer_type": "attention_sliding",
                "attention_present": True,
                "num_attention_heads": 32,
                "num_key_value_heads": 4,
                "head_dim": 128,
                "sliding_window": 1024,
            },
            {"layer_type": "mamba", "attention_present": False},
            {
                "layer_type": "attention",
                "attention_present": True,
                "num_attention_heads": 32,
                "num_key_value_heads": 8,
                "head_dim": 128,
            },
        ],
    }


def test_per_layer_overrides_detected():
    plan = build_layer_plan(_heterogeneous_config())
    assert plan is not None
    assert plan.layer_count == 4
    assert plan.heterogeneous is True
    assert plan.entries[1].num_key_value_heads == 4
    assert plan.entries[2].attention_present is False


def test_uniform_layers_not_heterogeneous():
    config = {
        "model_type": "llama",
        "layers": [
            {
                "attention_present": True,
                "num_key_value_heads": 8,
                "head_dim": 128,
            }
            for _ in range(3)
        ],
    }
    plan = build_layer_plan(config)
    assert plan is not None
    assert plan.heterogeneous is False


def test_absent_per_layer_returns_none():
    assert build_layer_plan({"model_type": "llama", "hidden_size": 4096}) is None
    assert build_layer_plan("not-a-dict") is None


def test_attention_layer_count():
    plan = build_layer_plan(_heterogeneous_config())
    assert plan is not None
    assert attention_layer_count(plan) == 3


def test_canonical_resolution_carries_layer_plan():
    _record, plan = resolve_canonical(config=_heterogeneous_config())
    assert plan is not None
    assert plan.heterogeneous is True


def test_layer_plan_unknown_presence_refuses_kv():
    from atlas.memory.kv_cache import (
        InsufficientCacheEvidenceError,
        estimate_kv_cache_layer_plan,
    )

    plan = build_layer_plan(
        {
            "layers": [
                {"num_key_value_heads": 8, "head_dim": 128},
                {"num_key_value_heads": 8, "head_dim": 128},
            ]
        }
    )
    assert plan is not None
    with pytest.raises(InsufficientCacheEvidenceError):
        estimate_kv_cache_layer_plan(
            plan,
            architecture_family="llama",
            context_tokens=1024,
            bytes_per_element=2.0,
        )

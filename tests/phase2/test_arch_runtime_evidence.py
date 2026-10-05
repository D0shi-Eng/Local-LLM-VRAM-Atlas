"""اختبارات المحلل والملفات والصيغ وفئات الأدلة."""

from atlas.archinfo.resolver import resolve_architecture
from atlas.evidence_classes import EVIDENCE_CLASSES, is_valid_evidence_class, stronger_than
from atlas.memory.architecture import architecture_status, cache_supported
from atlas.memory.calc_profile import ATLAS_TEXT_8K_BASELINE_V1, validate_profile
from atlas.memory.formulas import FORMULA_REGISTRY, formula_ref
from atlas.memory.runtime_profiles import find_runtime_profile, list_runtime_profiles


def test_resolver_evidence_order_and_conflict():
    """المحلل يجمع بترتيب الأدلة ويحفظ التعارض دون إخفاء."""
    info = resolve_architecture(
        hub_metadata={"architecture_family": "llama", "num_layers": 32},
        config_metadata={"num_layers": 28, "num_key_value_heads": 8},
    )
    assert info.architecture_family == "llama"
    assert info.num_layers == 32
    assert info.num_key_value_heads == 8
    assert info.conflict_detected is True
    assert info.conflict_detail is not None


def test_resolver_unknown_refuses_not_guesses():
    """غياب البنية يُسجل unknown ويرفض التخمين من الاسم."""
    info = resolve_architecture()
    assert info.architecture_family == "unknown"
    assert any("unknown" in item for item in info.warnings)


def test_support_matrix_states():
    """المصفوفة تميز المدعوم عن المرفوض صراحة."""
    assert cache_supported("standard_transformer") is True
    assert cache_supported("transformer_gqa") is True
    assert cache_supported("mla") is False
    assert cache_supported("mamba_ssm") is False
    assert cache_supported("hybrid") is False
    assert architecture_status("mamba_ssm")["status"] == "unsupported"


def test_runtime_profiles_have_no_invented_overhead():
    """ملفات runtime موثقة بلا overhead مخترع."""
    profiles = list_runtime_profiles()
    assert len(profiles) >= 3
    for profile in profiles:
        assert profile.known_static_overhead_bytes is None
        assert profile.known_dynamic_overhead_bytes is None
    assert find_runtime_profile("llama.cpp-cuda-full-offload") is not None
    assert find_runtime_profile("no-such-profile") is None


def test_formulas_are_versioned():
    """كل صيغة تحمل هويتها وافتراضاتها."""
    for formula_id in (
        "weight-bpw-v1",
        "standard-kv-v1",
        "quantized-kv-block-v1",
        "sliding-window-kv-v1",
    ):
        ref = formula_ref(formula_id)
        assert ref["formula_id"] == formula_id
        assert ref["formula_version"]
        assert ref["assumptions"]
    assert ATLAS_TEXT_8K_BASELINE_V1.profile_id == "atlas-text-8k-baseline-v1"
    assert validate_profile(ATLAS_TEXT_8K_BASELINE_V1) == []
    assert validate_profile(None) != []


def test_evidence_classes_are_distinct():
    """فئات الأدلة متميزة دون خلط أو درجات ثقة مخترعة."""
    assert "calculated_from_verified_metadata" in EVIDENCE_CLASSES
    assert "filename_inferred" in EVIDENCE_CLASSES
    assert is_valid_evidence_class("estimated") is True
    assert is_valid_evidence_class("confidence_0.92") is False
    assert stronger_than("independently_measured", "publisher_claim") is True


def test_grouping_is_idempotent():
    """إعادة التجميع على نفس المدخلات لا تنتج تكرارًا."""
    from atlas.artifact.grouping import group_siblings

    siblings = [
        {
            "filename": "m-00001-of-00002.gguf",
            "path": "m-00001-of-00002.gguf",
            "extension": ".gguf",
            "source_reported_size_bytes": 5,
        },
        {
            "filename": "m-00002-of-00002.gguf",
            "path": "m-00002-of-00002.gguf",
            "extension": ".gguf",
            "source_reported_size_bytes": 5,
        },
    ]
    first, _, _ = group_siblings(siblings, model_id="m", revision="r")
    second, _, _ = group_siblings(siblings, model_id="m", revision="r")
    assert first == second
    assert FORMULA_REGISTRY, "formula registry must document the estimation formulas"

"""اختبارات النسب: علاقات معلنة وتمييز دقيق للهوية."""

from support import FakeHfApi, make_info

from atlas.intake.hf_client import HuggingFaceSourceClient
from atlas.intake.lineage import classify_identity, normalize_repo_key, resolve_lineage
from atlas.intake.pipeline import IntakePipeline


def test_explicit_base_model_relationship_captured():
    """إعلان base_model في البطاقة يتحول إلى حافة نسب موثقة."""
    edges = resolve_lineage(("org/base-7b",))
    assert len(edges) == 1
    assert edges[0].target == "org/base-7b"
    assert edges[0].source == "model_card_metadata"
    assert edges[0].status == "publisher_declared"


def test_end_to_end_base_models_in_record():
    """النسب المعلن يظهر في السجل المعياري دون ترقية تلقائية."""
    outcome = IntakePipeline(HuggingFaceSourceClient(api=FakeHfApi(info=make_info()))).build(
        "org/quant"
    )
    assert outcome.model_record["base_models"] == ["org/base-7b"]
    assert outcome.model_record["verification"]["status"] == "publisher_claim"


def test_same_family_is_not_treated_as_duplicate():
    """نموذجان من عائلة واحدة ليسا تكرارًا."""
    assert classify_identity("org/qwen-7b", "a" * 40, "other/qwen-14b", "b" * 40) == "same_family"


def test_quantized_variant_relationship_stays_separate():
    """المتغير المكمم علاقة مميزة لا تنهار في هوية القاعدة."""
    assert (
        classify_identity(
            "org/model",
            "a" * 40,
            "quant/shop-model-GGUF",
            "c" * 40,
            relation_hint="quantized_variant",
        )
        == "quantized_variant"
    )


def test_repo_key_normalization_never_destroys_original():
    """المفتاح المطبع للمقارنة فقط والمعرف الأصلي محفوظ في السجل."""
    assert normalize_repo_key("Org/Model-X") == "org/model-x"
    outcome = IntakePipeline(HuggingFaceSourceClient(api=FakeHfApi(info=make_info()))).build(
        "Org/Model-X"
    )
    assert outcome.model_record["display_name"] == "Org/Model-X"

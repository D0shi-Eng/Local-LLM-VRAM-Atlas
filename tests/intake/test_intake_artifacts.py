"""اختبارات المخزون والحماية: أسماء دون تنزيل وحجم لا يعني VRAM."""

import pytest
from support import FakeHfApi, make_info

from atlas.intake.errors import WeightDownloadBlockedError
from atlas.intake.format import bytes_to_gib, round_gib
from atlas.intake.hf_client import HuggingFaceSourceClient
from atlas.intake.pipeline import IntakePipeline
from atlas.intake.weight_guard import assert_not_weight_path, is_weight_path


def _outcome(**overrides):
    """بناء نتيجة استقبال تركيبية بمخزون ملفات متحكم فيه."""
    return IntakePipeline(
        HuggingFaceSourceClient(api=FakeHfApi(info=make_info(**overrides)))
    ).build("org/m")


def test_remote_filename_stored_without_download():
    """اسم الملف البعيد يسجل من البيانات الوصفية دون أي تنزيل."""
    outcome = _outcome()
    quantization = outcome.model_record["quantization"]
    assert quantization["format"] == "GGUF"
    assert quantization["quant_name"] == "Q4_K_M"


def test_remote_size_stored_as_source_metadata():
    """الحجم البعيد يسجل كبيانات مصدر مع عرض GiB مشتق فقط."""
    outcome = _outcome()
    quantization = outcome.model_record["quantization"]
    assert quantization["file_size_bytes"] == 4670000000
    assert quantization["file_size_gib"] == pytest.approx(
        round_gib(bytes_to_gib(4670000000)), rel=1e-9
    )


def test_weight_artifact_download_is_blocked_by_guard():
    """حارس الأوزان يمنع أي مسار تنزيل لصيغ الأوزان المعروفة."""
    for name in (
        "model.gguf",
        "weights.safetensors",
        "pytorch_model.bin",
        "model.onnx",
        "ckpt/model.ckpt",
        "a.pt",
        "b.pth",
    ):
        assert is_weight_path(name) is True
        with pytest.raises(WeightDownloadBlockedError):
            assert_not_weight_path(name)


def test_file_size_never_becomes_vram_claim():
    """حجم الملف لا يتحول أبدًا إلى ادعاء VRAM في السجل المعياري."""
    outcome = _outcome()
    assert "vram" not in outcome.model_record
    assert outcome.model_record.get("quantization", {}).get("file_size_bytes") == 4670000000


def test_gib_helper_uses_binary_divisor():
    """مساعد التحويل يستخدم القاسم الثنائي ولا يخلط GB مع GiB."""
    assert bytes_to_gib(1024**3) == pytest.approx(1.0)
    assert bytes_to_gib(0) == 0.0
    with pytest.raises(ValueError):
        bytes_to_gib(-1)


def test_full_precision_filename_maps_to_bf16_family():
    """اسم الدقة الكاملة يصنف عائلتها دون ادعاء تكميم لاحق."""
    siblings = [
        {"rfilename": "model-bf16.gguf", "size": 40000000000, "lfs": {"oid": "x"}},
        {"rfilename": "model-Q4_K_M.gguf", "size": 12000000000, "lfs": {"oid": "y"}},
    ]
    outcome = _outcome(siblings=siblings)
    quantization = outcome.model_record["quantization"]
    assert quantization["quant_family"] == "bf16"
    assert quantization["quant_name"] == "BF16"
    assert quantization["native_quantization"] is None
    assert quantization["split_files"] is True


def test_mxfp4_filename_maps_to_mxfp4_family():
    """رمز MXFP4 يستخرج من الاسم كاستدلال غير متحقق منه فقط."""
    siblings = [{"rfilename": "model-MXFP4.gguf", "size": 12109565760, "lfs": {"oid": "x"}}]
    outcome = _outcome(siblings=siblings)
    quantization = outcome.model_record["quantization"]
    assert quantization["quant_family"] == "mxfp4"
    assert quantization["quant_name"] == "MXFP4"

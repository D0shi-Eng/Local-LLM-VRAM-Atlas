"""اختبارات كشف التكميم: GGUF/AWQ/GPTQ/EXL2/FP4 والتعارض والتزوير."""

from atlas.quant.detection import (
    detect_from_config,
    detect_from_filename,
    detect_from_tensor_inventory,
    resolve_quantization_evidence,
)


def test_gguf_quant_detection_filename_inferred():
    """كشف GGUF من الاسم يبقى filename_inferred لا verified."""
    detection = detect_from_filename("model-Q4_K_M.gguf")
    assert detection["quant_name"] == "Q4_K_M"
    assert detection["quant_family"] == "q4"
    assert detection["detection_method"] == "filename_inferred"


def test_awq_requires_structured_config():
    """AWQ تحددها structured config (quant_method/bits/group_size)."""
    structured = detect_from_config(
        {
            "quantization_config": {
                "quant_method": "awq",
                "bits": 4,
                "group_size": 128,
                "zero_point": True,
                "backend": "autoawq",
            }
        }
    )
    assert structured["quant_family"] == "awq"
    assert structured["detection_method"] == "source_reported"
    assert structured["quant_config"]["group_size"] == 128
    assert structured["quant_config"]["bits"] == 4


def test_gptq_config_recorded():
    """GPTQ تُسجل بت وgroup وخلفية دون توحيد كل GPTQ-4bit."""
    detection = detect_from_config(
        {
            "quantization_config": {
                "quant_method": "gptq",
                "bits": 4,
                "group_size": 64,
                "backend": "exllamav2",
            }
        }
    )
    assert detection["quant_family"] == "gptq"
    assert detection["quant_config"]["group_size"] == 64
    assert detection["quant_config"]["backend"] == "exllamav2"


def test_exl2_is_independent_family():
    """EXL2 عائلة مستقلة لا تُعامل كQ4."""
    detection = detect_from_filename("model-EXL2_4.0BPW.safetensors")
    assert detection["quant_family"] == "exl2"
    assert detection["quant_family"] != "q4"


def test_mxfp4_nvfp4_distinct_in_detection():
    """MXFP4 وNVFP4 يُكتشفان كعائلتين مختلفتين."""
    mxfp4 = detect_from_filename("model-MXFP4.gguf")
    nvfp4 = detect_from_filename("model-NVFP4.safetensors")
    assert mxfp4["quant_family"] == "mxfp4"
    assert nvfp4["quant_family"] == "nvfp4"
    assert mxfp4["quant_family"] != nvfp4["quant_family"]


def test_filename_spoof_loses_to_structured_evidence():
    """ملف مزيف باسم Q4 مع metadata متعارضة: الاسم لا يفوز."""
    filename_detection = detect_from_filename("fake-model-Q4_K_M.gguf")
    structured = detect_from_config(
        {"quantization_config": {"quant_method": "gptq", "bits": 4, "group_size": 128}}
    )
    resolved = resolve_quantization_evidence(filename_detection, structured)
    assert resolved["quant_family"] == "gptq"
    assert resolved["conflict_detected"] is True
    assert resolved["conflict_detail"] is not None


def test_evidence_conflict_preserved():
    """تعارض الاسم والدليل يُسجل ولا يُختار بصمت."""
    resolved = resolve_quantization_evidence(
        detect_from_filename("model-Q4_K_M.gguf"),
        detect_from_config({"quantization_config": {"quant_method": "awq", "bits": 4}}),
    )
    assert resolved["conflict_detected"] is True


def test_tensor_inventory_mixed_precision():
    """مخزون الموترات يكشف خلط الدقة دون اختزال النموذج لبت واحد."""
    detection = detect_from_tensor_inventory(
        [{"precision": "Q4_K_M"}] * 50 + [{"precision": "Q6_K"}] * 10
    )
    assert detection["mixed_precision"] is True
    assert detection["detection_method"] == "verified_metadata"

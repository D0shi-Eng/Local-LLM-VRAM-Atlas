"""كشف التكميم من أدلة متدرجة مع حفظ التعارض دون اختيار صامت."""

from __future__ import annotations

import re

from atlas.quant.registry import find_entry

# رموز الكم المعيارية المعروفة في أسماء الملفات.
_QUANT_TOKEN = re.compile(
    r"(BF16|FP16|FP32|F32|MXFP4(?:_[A-Z0-9]+)?|NVFP4(?:_[A-Z0-9]+)?|"
    r"AWQ(?:_\w+)?|GPTQ(?:_\w+)?|EXL2(?:_[\d.]+BPW)?|"
    r"Q1(?:_0)?|Q2(?:_K(?:_[A-Z]+)?|_0)?|IQ2(?:_[A-Z]+)?|"
    r"Q3(?:_K(?:_[A-Z]+)?)?|IQ3(?:_[A-Z]+)?|"
    r"Q4(?:_K(?:_[A-Z]+)?|_[01])?|IQ4(?:_[A-Z0-9]+)+|"
    r"Q5(?:_K(?:_[A-Z]+)?|_[01])?|Q6(?:_K(?:_[A-Z]+)?)?|"
    r"Q8(?:_[01]|_K)?|IQ1(?:_[A-Z]+)?|TQ[12](?:_0)?)",
    re.IGNORECASE,
)

_FAMILY_HEADS = {
    "BF16": "bf16",
    "FP16": "f16",
    "FP32": "f32",
    "F32": "f32",
    "MXFP4": "mxfp4",
    "NVFP4": "nvfp4",
    "AWQ": "awq",
    "GPTQ": "gptq",
    "EXL2": "exl2",
    "Q1": "q1",
    "Q2": "q2",
    "IQ2": "iq2",
    "Q3": "q3",
    "IQ3": "iq3",
    "Q4": "q4",
    "IQ4": "iq4",
    "Q5": "q5",
    "Q6": "q6",
    "Q8": "q8",
    "IQ1": "iq1",
    "TQ1": "tq",
    "TQ2": "tq",
}


def _family_from_token(token: str | None) -> str:
    """اشتقاق العائلة من رأس الرمز دون ادعاء دقة الكتلة."""
    if not token:
        return "unknown"
    head = re.split(r"[_-]", token.upper(), maxsplit=1)[0]
    if head.startswith("TQ"):
        return "tq"
    return _FAMILY_HEADS.get(head, "unknown")


def detect_from_filename(filename: str | None) -> dict:
    """كشف التكميم من اسم الملف كإشارة غير متحقق منها فقط."""
    if not filename or not isinstance(filename, str):
        return {
            "quant_name": None,
            "quant_family": "unknown",
            "detection_method": "unknown",
            "registry_id": None,
        }
    match = _QUANT_TOKEN.search(filename.upper())
    if not match:
        return {
            "quant_name": None,
            "quant_family": "unknown",
            "detection_method": "unknown",
            "registry_id": None,
        }
    token = match.group(1).upper()
    entry = find_entry(token)
    return {
        "quant_name": token,
        "quant_family": _family_from_token(token),
        "detection_method": "filename_inferred",
        "registry_id": entry["quantization_id"] if entry else None,
    }


def detect_from_config(config: dict | None) -> dict:
    """كشف AWQ/GPTQ من structured config المعتمدة لا من اسم المستودع."""
    if not isinstance(config, dict) or not config:
        return {
            "quant_name": None,
            "quant_family": "unknown",
            "detection_method": "unknown",
            "registry_id": None,
            "quant_config": None,
        }
    quant_cfg = config.get("quantization_config")
    if not isinstance(quant_cfg, dict):
        quant_cfg = None
    method_raw = None
    bits = None
    group_size = None
    if quant_cfg:
        method_raw = quant_cfg.get("quant_method")
        bits = quant_cfg.get("bits")
        group_size = quant_cfg.get("group_size")
    if not isinstance(method_raw, str) or not method_raw.strip():
        return {
            "quant_name": None,
            "quant_family": "unknown",
            "detection_method": "unknown",
            "registry_id": None,
            "quant_config": None,
        }
    method = method_raw.strip().lower()
    family = "awq" if method == "awq" else "gptq" if method == "gptq" else "unknown"
    if family == "unknown":
        return {
            "quant_name": None,
            "quant_family": "unknown",
            "detection_method": "unknown",
            "registry_id": None,
            "quant_config": None,
        }
    entry = find_entry(family)
    detail = {
        "quant_method": method,
        "bits": bits if isinstance(bits, int) and bits > 0 else None,
        "group_size": group_size if isinstance(group_size, int) and group_size > 0 else None,
        "zero_point": quant_cfg.get("zero_point"),
        "backend": quant_cfg.get("backend"),
    }
    label_bits = f"-{detail['bits']}bit" if detail["bits"] else ""
    return {
        "quant_name": f"{family.upper()}{label_bits}",
        "quant_family": family,
        "detection_method": "source_reported",
        "registry_id": entry["quantization_id"] if entry else None,
        "quant_config": detail,
    }


def detect_from_tensor_inventory(tensor_infos: list[dict] | None) -> dict:
    """اشتقاق توزيع الدقة من مخزون الموترات الموثوق دون تنزيل أوزان."""
    if not isinstance(tensor_infos, list) or not tensor_infos:
        return {
            "quant_name": None,
            "quant_family": "unknown",
            "detection_method": "unknown",
            "registry_id": None,
            "tensor_distribution": None,
            "mixed_precision": None,
        }
    distribution: dict[str, int] = {}
    for item in tensor_infos:
        if not isinstance(item, dict):
            continue
        precision = item.get("precision") or item.get("dtype") or item.get("type")
        if isinstance(precision, str) and precision.strip():
            key = precision.strip().upper()
            distribution[key] = distribution.get(key, 0) + 1
    if not distribution:
        return {
            "quant_name": None,
            "quant_family": "unknown",
            "detection_method": "unknown",
            "registry_id": None,
            "tensor_distribution": None,
            "mixed_precision": None,
        }
    mixed = len(distribution) > 1
    dominant = max(sorted(distribution), key=lambda key: distribution[key])
    entry = find_entry(dominant)
    return {
        "quant_name": dominant,
        "quant_family": _family_from_token(dominant),
        "detection_method": "verified_metadata",
        "registry_id": entry["quantization_id"] if entry else None,
        "tensor_distribution": distribution,
        "mixed_precision": mixed,
    }


def resolve_quantization_evidence(
    filename_detection: dict | None,
    structured_detection: dict | None,
) -> dict:
    """دمج الدليلين مع تسجيل التعارض وعدم ترقية الاستنتاج الاسمي أبدًا."""
    filename_detection = filename_detection or {}
    structured_detection = structured_detection or {}
    structured_method = structured_detection.get("detection_method", "unknown")
    filename_name = filename_detection.get("quant_name")
    structured_name = structured_detection.get("quant_name")
    if structured_method not in ("unknown", None) and structured_name:
        result = dict(structured_detection)
        if filename_name and filename_name != structured_name:
            result["conflict_detected"] = True
            result["conflict_detail"] = (
                f"filename={filename_name!r} vs structured={structured_name!r}"
            )
        else:
            result["conflict_detected"] = False
            result["conflict_detail"] = None
        return result
    result = dict(filename_detection)
    result["conflict_detected"] = False
    result["conflict_detail"] = None
    return result

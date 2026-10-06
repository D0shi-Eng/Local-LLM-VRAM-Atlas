"""حارس الأوزان: منع أي تنزيل لملفات أوزان النماذج بصرامة."""

from __future__ import annotations

from pathlib import PurePosixPath

# لواحق ملفات الأوزان المحظور تنزيلها بصرامة.
WEIGHT_SUFFIXES = frozenset(
    {
        ".gguf",
        ".safetensors",
        ".ckpt",
        ".pt",
        ".pth",
        ".bin",
        ".onnx",
    }
)

# أسماء شائعة لملفات الأوزان دون لاحقة واضحة أحيانًا.
WEIGHT_BASENAMES = frozenset(
    {
        "model.safetensors.index.json",
    }
)


def is_weight_path(path: str) -> bool:
    """فحص ما إذا كان المسار يشير إلى وزن نموذج محظور."""
    if not isinstance(path, str) or not path:
        return False
    name = PurePosixPath(path.strip()).name.lower()
    for suffix in WEIGHT_SUFFIXES:
        if name.endswith(suffix):
            return True
    return name in WEIGHT_BASENAMES


def assert_not_weight_path(path: str) -> None:
    """رفع خطأ دفاعي عند محاولة التعامل مع مسار وزن كقابل للتنزيل."""
    from atlas.intake.errors import WeightDownloadBlockedError

    if is_weight_path(path):
        raise WeightDownloadBlockedError(f"model weight download is forbidden: {path!r}")

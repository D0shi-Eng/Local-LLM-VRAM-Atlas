"""تصنيف الملفات المساعدة: الفصل بين الأوزان والمكونات المرافقة."""

from __future__ import annotations

# أسماء الملفات المساعدة المعروفة التي ليست أوزانًا رئيسية أبدًا.
_TOKENIZER_NAMES = frozenset(
    {
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "merges.txt",
        "vocab.json",
        "tekken.json",
        "chat_template.jinja",
    }
)

_CONFIG_NAMES = frozenset(
    {
        "config.json",
        "generation_config.json",
        "params.json",
        "quantization_config.json",
        "preprocessor_config.json",
        "processor_config.json",
    }
)

_INDEX_SUFFIXES = (".index.json",)

_DOC_SUFFIXES = (".md", ".txt", ".png", ".jpg", ".license", "license")


def classify_auxiliary(filename: str | None) -> str:
    """تصنيف ملف مساعد إلى نوعه دون اعتباره وزنًا رئيسيًا."""
    if not filename or not isinstance(filename, str):
        return "other"
    lowered = filename.strip().lower()
    base = lowered.rsplit("/", 1)[-1]
    if base in _TOKENIZER_NAMES:
        return "tokenizer"
    if base in _CONFIG_NAMES:
        return "config"
    if base == "model.safetensors.index.json" or base.endswith(_INDEX_SUFFIXES):
        return "index"
    if "mmproj" in base:
        return "projector"
    if "imatrix" in base:
        return "imatrix"
    if base.endswith((".gitattributes",)):
        return "metadata"
    if base.endswith(_DOC_SUFFIXES) or base in ("license", "usage_policy"):
        return "docs"
    return "other"


def is_main_weight_candidate(filename: str | None, extension: str | None) -> bool:
    """تحديد ما إذا كان الملف مرشحًا لوزن رئيسي قبل التجميع."""
    if not filename or not isinstance(filename, str):
        return False
    lowered = filename.strip().lower()
    if classify_auxiliary(filename) in (
        "tokenizer",
        "config",
        "index",
        "docs",
        "metadata",
        "imatrix",
    ):
        return False
    if lowered.endswith((".gguf", ".safetensors", ".bin", ".pt", ".pth", ".ckpt", ".onnx")):
        return True
    return False

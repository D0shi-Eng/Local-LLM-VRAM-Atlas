"""حزمة التكميم: السجل النسخي والكشف وحسابات البت لكل وزن."""

from atlas.quant.bpw import effective_bits_per_weight
from atlas.quant.detection import (
    detect_from_config,
    detect_from_filename,
    detect_from_tensor_inventory,
    resolve_quantization_evidence,
)
from atlas.quant.registry import (
    OBSERVED_AT,
    REGISTRY_VERSION,
    SUPPORTED_FAMILIES,
    find_entry,
    get_alias_target,
    list_entries,
    resolve_alias,
)

__all__ = [
    "OBSERVED_AT",
    "REGISTRY_VERSION",
    "SUPPORTED_FAMILIES",
    "effective_bits_per_weight",
    "detect_from_config",
    "detect_from_filename",
    "detect_from_tensor_inventory",
    "resolve_quantization_evidence",
    "find_entry",
    "get_alias_target",
    "list_entries",
    "resolve_alias",
]

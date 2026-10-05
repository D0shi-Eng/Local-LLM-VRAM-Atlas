"""حزمة محلل البنية: ترتيب الأدلة وحفظ التعارض دون تخمين."""

from atlas.archinfo.canonical import (
    CanonicalArchitectureRecord,
    FieldEvidence,
    record_to_dict,
)
from atlas.archinfo.capabilities import ArchitectureCapabilities, assess_capabilities
from atlas.archinfo.gguf import normalize_gguf_metadata
from atlas.archinfo.hf_config import model_info_to_canonical, resolve_canonical
from atlas.archinfo.layer_plan import LayerPlan, LayerPlanEntry, build_layer_plan
from atlas.archinfo.normalize import (
    classify_attention,
    derive_head_dim,
    detect_mla_signals,
    detect_ssm_signals,
)
from atlas.archinfo.resolver import ArchitectureInfo, resolve_architecture

__all__ = [
    "ArchitectureCapabilities",
    "ArchitectureInfo",
    "CanonicalArchitectureRecord",
    "FieldEvidence",
    "LayerPlan",
    "LayerPlanEntry",
    "assess_capabilities",
    "build_layer_plan",
    "classify_attention",
    "derive_head_dim",
    "detect_mla_signals",
    "detect_ssm_signals",
    "model_info_to_canonical",
    "normalize_gguf_metadata",
    "record_to_dict",
    "resolve_architecture",
    "resolve_canonical",
]

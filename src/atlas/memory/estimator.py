"""المقدر الواعي بالأدلة: نطاقات صريحة ورفض صادق عند غياب الدليل."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from atlas.memory.architecture import architecture_status
from atlas.memory.calc_profile import CalculationProfile, validate_profile
from atlas.memory.components import MemoryComponents
from atlas.memory.kv_cache import (
    InsufficientCacheEvidenceError,
    UnsupportedArchitectureError,
    estimate_kv_cache_bytes,
    estimate_kv_cache_layer_plan,
)
from atlas.memory.runtime_profiles import RuntimeMemoryProfile
from atlas.memory.weights import (
    InsufficientWeightEvidenceError,
    MoEActiveParameterMisuseError,
    estimate_resident_weight_bytes,
)

if TYPE_CHECKING:
    from atlas.archinfo.layer_plan import LayerPlan

# حالات التقدير المسموحة؛ measured محظورة دون قياس فعلي.
ESTIMATE_STATUSES = (
    "calculated_from_verified_metadata",
    "calculated_from_source_metadata",
    "estimated",
    "insufficient_evidence",
    "unsupported_architecture_for_estimation",
)


@dataclass(frozen=True)
class MemoryEstimate:
    """نتيجة التقدير: النطاق والدليل والمجهول لا رقم وحيد بلا سياق."""

    estimate_status: str
    evidence_basis: str
    formula_refs: tuple[str, ...] = ()
    calculation_profile_id: str | None = None
    components: MemoryComponents = field(default_factory=MemoryComponents)
    estimated_vram_lower_bytes: int | None = None
    estimated_vram_upper_bytes: int | None = None
    unknown_components: tuple[str, ...] = ()
    unsupported_components: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


def _evidence_basis_for(
    weight_verified: bool,
    arch_verified: bool,
    runtime_known: bool,
) -> tuple[str, str]:
    """اشتقاق الحالة والدليل من جودة المدخلات دون تجميل."""
    if weight_verified and arch_verified and runtime_known:
        return "calculated_from_verified_metadata", "verified architecture and weight inputs"
    if weight_verified and arch_verified:
        return "calculated_from_source_metadata", "source-reported inputs with a known formula"
    return "estimated", "inputs include assumptions recorded alongside"


@dataclass(frozen=True)
class EstimateInputs:
    """مدخلات التقدير الصريحة من أدلة مسماة المصدر."""

    architecture_family: str | None = None
    architecture_verified: bool = False
    total_parameters: int | float | None = None
    active_parameters: int | float | None = None
    total_known: bool = True
    weight_bytes_verified: int | None = None
    weight_verified: bool = False
    effective_bits_per_weight: float | None = None
    num_layers: int | None = None
    num_kv_heads: int | None = None
    num_attention_heads: int | None = None
    head_dim: int | None = None
    kv_bytes_per_element: float | None = None
    kv_block_size: int | None = None
    kv_scale_bytes_per_block: int | None = None
    sliding_window: int | None = None
    advertised_max_context: int | None = None


def estimate_peak_vram(
    estimate_inputs: EstimateInputs,
    calculation_profile: CalculationProfile | None,
    runtime_profile: RuntimeMemoryProfile | None = None,
    *,
    layer_plan: LayerPlan | None = None,
) -> MemoryEstimate:
    """تقدير الذروة كنطاق مع رفض صادق عند المعمارية غير المدعومة."""
    profile_errors = validate_profile(calculation_profile)
    family = (estimate_inputs.architecture_family or "unknown").lower()
    support = architecture_status(family)
    if support.get("status") in ("unsupported",):
        return MemoryEstimate(
            estimate_status="unsupported_architecture_for_estimation",
            evidence_basis=f"architecture {family!r} has no supported cache model",
            formula_refs=(),
            calculation_profile_id=getattr(calculation_profile, "profile_id", None),
            unsupported_components=("kv_or_state_cache_bytes",),
            assumptions=tuple(profile_errors),
            warnings=("calculation refused: no fake number is produced",),
        )
    if profile_errors:
        return MemoryEstimate(
            estimate_status="insufficient_evidence",
            evidence_basis="; ".join(profile_errors),
            calculation_profile_id=None,
            unknown_components=("calculation_profile",),
            warnings=("no VRAM estimate exists without a calculation profile",),
        )
    assert calculation_profile is not None
    context_tokens = calculation_profile.context_tokens
    if (
        estimate_inputs.advertised_max_context is not None
        and estimate_inputs.advertised_max_context < context_tokens
    ):
        return MemoryEstimate(
            estimate_status="insufficient_evidence",
            evidence_basis="model advertises less context than the calculation profile targets",
            calculation_profile_id=calculation_profile.profile_id,
            unknown_components=("kv_or_state_cache_bytes",),
            assumptions=(
                f"advertised_max={estimate_inputs.advertised_max_context} < "
                f"calculation_context={context_tokens}; context is never raised synthetically",
            ),
            warnings=("calculation refused at this profile; use a smaller context profile",),
        )
    warnings: list[str] = []
    unknown: list[str] = []
    # الأوزان المقيمة: البايت الموثق أولًا ثم الحساب من bpw.
    weight_bytes: int | None = estimate_inputs.weight_bytes_verified
    weight_formulas: list[str] = []
    if weight_bytes is None:
        try:
            weight_bytes = estimate_resident_weight_bytes(
                total_parameters=estimate_inputs.total_parameters,
                bits_per_weight=estimate_inputs.effective_bits_per_weight,
                architecture_type="moe" if family == "moe" else "dense",
                active_parameters=estimate_inputs.active_parameters,
                total_known=estimate_inputs.total_known,
            )
            weight_formulas.append("weight-bpw-v1")
        except (InsufficientWeightEvidenceError, MoEActiveParameterMisuseError) as exc:
            return MemoryEstimate(
                estimate_status="insufficient_evidence",
                evidence_basis=str(exc),
                calculation_profile_id=calculation_profile.profile_id,
                unknown_components=("device_weight_bytes",),
                warnings=("weight residency cannot be derived from active parameters",),
            )
    # الكاش: الصيغة القياسية فقط للعائلات المطابقة.
    # مسار Layer Plan: مجموع كل طبقة على حدة دون تسطيح القيم الشاملة.
    kv_formulas = ["standard-kv-v1"]
    if estimate_inputs.kv_block_size is not None:
        kv_formulas = ["quantized-kv-block-v1"]
    if estimate_inputs.sliding_window is not None:
        kv_formulas = ["sliding-window-kv-v1"]
    try:
        if layer_plan is not None:
            kv_bytes = estimate_kv_cache_layer_plan(
                layer_plan,
                architecture_family=family,
                context_tokens=context_tokens,
                bytes_per_element=estimate_inputs.kv_bytes_per_element,
                sequence_count=calculation_profile.sequence_count,
            )
            kv_formulas = ["standard-kv-layer-plan-v1"]
        else:
            kv_bytes = estimate_kv_cache_bytes(
                architecture_family=family,
                num_layers=estimate_inputs.num_layers,
                num_kv_heads=estimate_inputs.num_kv_heads,
                head_dim=estimate_inputs.head_dim,
                context_tokens=context_tokens,
                bytes_per_element=estimate_inputs.kv_bytes_per_element,
                sequence_count=calculation_profile.sequence_count,
                num_attention_heads=estimate_inputs.num_attention_heads,
                sliding_window=estimate_inputs.sliding_window,
                kv_block_size=estimate_inputs.kv_block_size,
                kv_scale_bytes_per_block=estimate_inputs.kv_scale_bytes_per_block,
            )
    except UnsupportedArchitectureError as exc:
        return MemoryEstimate(
            estimate_status="unsupported_architecture_for_estimation",
            evidence_basis=str(exc),
            calculation_profile_id=calculation_profile.profile_id,
            unsupported_components=("kv_or_state_cache_bytes",),
            warnings=("calculation refused: no fake number is produced",),
        )
    except InsufficientCacheEvidenceError as exc:
        return MemoryEstimate(
            estimate_status="insufficient_evidence",
            evidence_basis=str(exc),
            calculation_profile_id=calculation_profile.profile_id,
            unknown_components=("kv_or_state_cache_bytes",),
            warnings=("unknown cache inputs stay unknown, never zero",),
        )
    # النطاق: الأدنى معلومتان فقط، والعلوي يتطلب runtime موثقًا.
    known_sum = int(weight_bytes) + int(kv_bytes)
    runtime_static = (
        runtime_profile.known_static_overhead_bytes if runtime_profile is not None else None
    )
    runtime_dynamic = (
        runtime_profile.known_dynamic_overhead_bytes if runtime_profile is not None else None
    )
    if runtime_static is None or runtime_dynamic is None:
        for item in ("runtime_static_bytes", "runtime_dynamic_bytes"):
            if item not in unknown:
                unknown.append(item)
        if runtime_profile is None:
            warnings.append("runtime profile missing: independent components only, no default")
        else:
            warnings.append("runtime overhead unknown: no reliable upper bound exists")
        status, basis = _evidence_basis_for(
            estimate_inputs.weight_verified,
            estimate_inputs.architecture_verified,
            runtime_known=False,
        )
        components = MemoryComponents(
            device_weight_bytes=int(weight_bytes),
            kv_or_state_cache_bytes=int(kv_bytes),
            unknown_overhead=tuple(unknown),
        )
        return MemoryEstimate(
            estimate_status=status if status != "estimated" else "estimated",
            evidence_basis=basis,
            formula_refs=tuple(weight_formulas + kv_formulas),
            calculation_profile_id=calculation_profile.profile_id,
            components=components,
            estimated_vram_lower_bytes=known_sum,
            estimated_vram_upper_bytes=None,
            unknown_components=tuple(unknown),
            assumptions=(
                "lower bound covers resident weights plus cache only; "
                "upper bound unavailable without measured runtime overhead",
            ),
            warnings=tuple(warnings),
        )
    total = known_sum + int(runtime_static) + int(runtime_dynamic)
    status, basis = _evidence_basis_for(
        estimate_inputs.weight_verified,
        estimate_inputs.architecture_verified,
        runtime_known=True,
    )
    components = MemoryComponents(
        device_weight_bytes=int(weight_bytes),
        kv_or_state_cache_bytes=int(kv_bytes),
        runtime_static_bytes=int(runtime_static),
        runtime_dynamic_bytes=int(runtime_dynamic),
    )
    return MemoryEstimate(
        estimate_status=status,
        evidence_basis=basis,
        formula_refs=tuple(weight_formulas + kv_formulas),
        calculation_profile_id=calculation_profile.profile_id,
        components=components,
        estimated_vram_lower_bytes=total,
        estimated_vram_upper_bytes=total,
        unknown_components=(),
        warnings=tuple(warnings),
    )

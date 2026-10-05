"""Canonical architecture record: every critical field carries its provenance.

Zero-weight rule: values come from bounded public metadata only, never from
downloaded weights, executed models, or agent memory of famous models.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Evidence tiers, strongest first. Filename inference never overrides structure.
EVIDENCE_TIERS = (
    "tier_a_structured",
    "tier_b_card",
    "tier_c_derivative",
    "tier_d_filename",
    "calculated",
    "unknown",
)

# Canonical integer fields of the architecture record.
INT_FIELDS = (
    "hidden_size",
    "intermediate_size",
    "num_hidden_layers",
    "num_attention_heads",
    "num_key_value_heads",
    "vocab_size",
    "max_position_embeddings",
    "sliding_window",
    "num_experts",
    "num_experts_per_token",
    "num_shared_experts",
    "moe_intermediate_size",
)

# Canonical text/flag fields (non-integer).
TEXT_FIELDS = (
    "architecture_family",
    "model_type",
    "attention_pattern",
    "attention_type",
    "head_dim_source",
)

# Resolution outcomes: full, partial, unsupported, insufficient_evidence.
RESOLUTION_STATES = (
    "resolved",
    "partial",
    "unsupported",
    "insufficient_evidence",
)


@dataclass(frozen=True)
class FieldEvidence:
    """Provenance of one canonical field; calculated values say so explicitly."""

    value: object
    source: str
    evidence_class: str
    resolved_revision: str | None = None
    retrieved_at: str | None = None
    inference_method: str | None = None
    conflict: bool = False
    conflict_detail: str | None = None

    def is_calculated(self) -> bool:
        """Whether this value was derived mathematically rather than reported."""
        return self.evidence_class == "calculated" or self.inference_method is not None


@dataclass(frozen=True)
class CanonicalArchitectureRecord:
    """Normalized architecture facts with per-field evidence and revision."""

    architecture_family: str = "unknown"
    model_type: str | None = None
    architectures: tuple[str, ...] = ()
    hidden_size: int | None = None
    intermediate_size: int | None = None
    num_hidden_layers: int | None = None
    num_attention_heads: int | None = None
    num_key_value_heads: int | None = None
    head_dim: int | None = None
    head_dim_source: str | None = None
    vocab_size: int | None = None
    max_position_embeddings: int | None = None
    sliding_window: int | None = None
    attention_pattern: str | None = None
    attention_type: str | None = None
    layer_types: tuple[str, ...] = ()
    is_encoder_decoder: bool | None = None
    tie_word_embeddings: bool | None = None
    num_experts: int | None = None
    num_experts_per_token: int | None = None
    num_shared_experts: int | None = None
    moe_intermediate_size: int | None = None
    moe_layer_pattern: str | None = None
    state_size: int | None = None
    conv_kernel: int | None = None
    expand_factor: float | None = None
    ssm_layer_pattern: str | None = None
    mla_info: str | None = None
    custom_remote_architecture: bool = False
    requested_revision: str | None = None
    resolved_revision: str | None = None
    retrieved_at: str | None = None
    evidence: dict[str, FieldEvidence] | None = None
    conflict_detected: bool = False
    conflict_detail: str | None = None
    resolution_status: str = "insufficient_evidence"
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def field_evidence(self, name: str) -> FieldEvidence | None:
        """Return the provenance of one field, or None when unrecorded."""
        if not self.evidence:
            return None
        return self.evidence.get(name)

    def known_fields(self) -> tuple[str, ...]:
        """Names of canonical fields holding a non-None value."""
        names: list[str] = []
        for name in (
            *INT_FIELDS,
            "model_type",
            "head_dim",
            "attention_pattern",
            "attention_type",
            "is_encoder_decoder",
            "tie_word_embeddings",
            "moe_layer_pattern",
            "state_size",
            "conv_kernel",
            "expand_factor",
            "ssm_layer_pattern",
            "mla_info",
        ):
            if getattr(self, name, None) is not None:
                names.append(name)
        return tuple(names)

    def unknown_fields(self) -> tuple[str, ...]:
        """Names of canonical fields still unknown (never zero)."""
        return tuple(
            name
            for name in (
                *INT_FIELDS,
                "model_type",
                "head_dim",
                "is_encoder_decoder",
            )
            if getattr(self, name, None) is None
        )


def record_to_dict(record: CanonicalArchitectureRecord) -> dict:
    """Convert a canonical record to a JSON-safe dict for schema validation."""
    evidence_dict = {}
    for name, item in (record.evidence or {}).items():
        evidence_dict[name] = {
            "value": item.value,
            "source": item.source,
            "evidence_class": item.evidence_class,
            "resolved_revision": item.resolved_revision,
            "retrieved_at": item.retrieved_at,
            "inference_method": item.inference_method,
            "conflict": item.conflict,
            "conflict_detail": item.conflict_detail,
        }
    return {
        "schema_version": "0.3.0",
        "architecture_family": record.architecture_family,
        "model_type": record.model_type,
        "architectures": list(record.architectures),
        "hidden_size": record.hidden_size,
        "intermediate_size": record.intermediate_size,
        "num_hidden_layers": record.num_hidden_layers,
        "num_attention_heads": record.num_attention_heads,
        "num_key_value_heads": record.num_key_value_heads,
        "head_dim": record.head_dim,
        "head_dim_source": record.head_dim_source,
        "vocab_size": record.vocab_size,
        "max_position_embeddings": record.max_position_embeddings,
        "sliding_window": record.sliding_window,
        "attention_pattern": record.attention_pattern,
        "attention_type": record.attention_type,
        "layer_types": list(record.layer_types),
        "is_encoder_decoder": record.is_encoder_decoder,
        "tie_word_embeddings": record.tie_word_embeddings,
        "num_experts": record.num_experts,
        "num_experts_per_token": record.num_experts_per_token,
        "num_shared_experts": record.num_shared_experts,
        "moe_intermediate_size": record.moe_intermediate_size,
        "moe_layer_pattern": record.moe_layer_pattern,
        "state_size": record.state_size,
        "conv_kernel": record.conv_kernel,
        "expand_factor": record.expand_factor,
        "ssm_layer_pattern": record.ssm_layer_pattern,
        "mla_info": record.mla_info,
        "custom_remote_architecture": record.custom_remote_architecture,
        "requested_revision": record.requested_revision,
        "resolved_revision": record.resolved_revision,
        "retrieved_at": record.retrieved_at,
        "conflict_detected": record.conflict_detected,
        "conflict_detail": record.conflict_detail,
        "resolution_status": record.resolution_status,
        "warnings": list(record.warnings),
    }

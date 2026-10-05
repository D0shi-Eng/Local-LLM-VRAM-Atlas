"""Runtime capability records: source/version-aware, knowledge only.

Every record comes from official runtime documentation observed at a stated
date. Documentation states compatibility; it is never VRAM measurement
evidence, and no performance numbers (tokens/sec, latency) are collected.
Runtimes are never installed or executed in this phase.
"""

from __future__ import annotations

from dataclasses import dataclass

# Explicit support states; an old blog post never becomes current official.
SUPPORT_STATUSES = (
    "official",
    "documented",
    "experimental",
    "deprecated",
    "unsupported",
    "unknown",
)


@dataclass(frozen=True)
class RuntimeCapability:
    """One compatibility claim: runtime + version + backend + artifact + arch."""

    runtime: str
    runtime_version_or_revision: str | None
    backend: str | None
    platform: str | None
    artifact_format: str | None
    quantization_family: str | None
    architecture_family: str | None
    hardware_requirement: str | None
    support_status: str
    source: str
    observed_at: str
    notes: str | None = None

    def capability_id(self) -> str:
        """Stable identifier for this claim (no ranking, no score)."""
        parts = [
            self.runtime,
            self.runtime_version_or_revision or "unversioned",
            self.backend or "any-backend",
            self.artifact_format or "any-format",
            self.architecture_family or "any-arch",
        ]
        return "/".join(part.replace(" ", "-").lower() for part in parts)


# Knowledge observed 2026-10-05 from official project documentation.
# Each entry records what the docs state and what remains unknown.
_KNOWLEDGE: tuple[RuntimeCapability, ...] = (
    RuntimeCapability(
        runtime="llama.cpp",
        runtime_version_or_revision="docs-observed-2026-10-05",
        backend="CUDA",
        platform="Windows",
        artifact_format="GGUF",
        quantization_family="GGML quant types (Q4_K_M and family)",
        architecture_family="standard Transformer families incl. llama/mistral/qwen",
        hardware_requirement="CUDA-capable NVIDIA GPU; VRAM need is workload-specific",
        support_status="documented",
        source="https://github.com/ggml-org/llama.cpp",
        observed_at="2026-10-05T00:00:00Z",
        notes="Compatibility evidence only; not VRAM measurement. "
        "KV-cache quantization modes exist; overhead stays unmeasured.",
    ),
    RuntimeCapability(
        runtime="llama.cpp",
        runtime_version_or_revision="docs-observed-2026-10-05",
        backend="Vulkan",
        platform="Windows",
        artifact_format="GGUF",
        quantization_family="GGML quant types",
        architecture_family="standard Transformer families",
        hardware_requirement="Vulkan-capable GPU",
        support_status="documented",
        source="https://github.com/ggml-org/llama.cpp",
        observed_at="2026-10-05T00:00:00Z",
        notes="Backend-specific support; CUDA facts never imply Vulkan facts.",
    ),
    RuntimeCapability(
        runtime="ExLlamaV2",
        runtime_version_or_revision="docs-observed-2026-10-05",
        backend="CUDA",
        platform="Windows",
        artifact_format="EXL2",
        quantization_family="EXL2 mixed-precision",
        architecture_family="llama-family dense models",
        hardware_requirement="CUDA-capable NVIDIA GPU",
        support_status="documented",
        source="https://github.com/turboderp/exllamav2",
        observed_at="2026-10-05T00:00:00Z",
        notes="EXL2 weights load per measured quantization plan; "
        "MoE support is version-dependent and stays unknown here.",
    ),
    RuntimeCapability(
        runtime="Transformers",
        runtime_version_or_revision="docs-observed-2026-10-05",
        backend="CUDA",
        platform="Windows",
        artifact_format="Safetensors",
        quantization_family="AWQ/GPTQ/bitsandbytes (integration-gated)",
        architecture_family="documented Transformers model types",
        hardware_requirement="CUDA-capable GPU; method-dependent",
        support_status="documented",
        source="https://huggingface.co/docs/transformers/quantization_overview",
        observed_at="2026-10-05T00:00:00Z",
        notes="Quantization support varies per integration; AWQ/GPTQ/EXL2/MLX "
        "are independent families, never synonyms.",
    ),
    RuntimeCapability(
        runtime="TensorRT-LLM",
        runtime_version_or_revision="docs-observed-2026-10-05",
        backend="CUDA",
        platform="Linux/Windows",
        artifact_format="engine checkpoints",
        quantization_family="NVFP4/MXFP4/FP8 (recipe-dependent)",
        architecture_family="recipe-supported dense models",
        hardware_requirement="Recent NVIDIA datacenter/consumer GPUs per recipe",
        support_status="experimental",
        source="https://github.com/NVIDIA/TensorRT-LLM",
        observed_at="2026-10-05T00:00:00Z",
        notes="FP4 kept distinct from MXFP4/NVFP4; engine recipes decide support.",
    ),
    RuntimeCapability(
        runtime="MLX-LM",
        runtime_version_or_revision="docs-observed-2026-10-05",
        backend="unified memory",
        platform="macOS",
        artifact_format="MLX",
        quantization_family="MLX quantization",
        architecture_family="ported model types",
        hardware_requirement="Apple Silicon unified memory (not discrete VRAM)",
        support_status="documented",
        source="https://github.com/ml-explore/mlx-lm",
        observed_at="2026-10-05T00:00:00Z",
        notes="Unified-memory model differs from discrete GPUs; "
        "device/host split is not a VRAM fit claim.",
    ),
)


def list_capabilities() -> list[RuntimeCapability]:
    """Return all researched runtime capabilities (researched set only)."""
    return list(_KNOWLEDGE)


def get_capability(capability_id: str) -> RuntimeCapability | None:
    """Look up one capability by its stable id, or None."""
    if not isinstance(capability_id, str):
        return None
    for capability in _KNOWLEDGE:
        if capability.capability_id() == capability_id.strip().lower():
            return capability
    return None

"""Runtime compatibility hints.

Versioned and sourced. Never infers "works everywhere" from a filename.
Hints map container/quant families to documented runtime capabilities;
each hint cites the runtime knowledge source and observed date.
"""

from __future__ import annotations

RUNTIME_KNOWLEDGE_SOURCE = "atlas.runtimes.knowledge docs-observed-2026-10-05"
OBSERVED_AT = "2026-10-05T00:00:00Z"

# Conservative format -> runtime hints. Statuses mirror knowledge base.
_FORMAT_HINTS: dict[str, list[dict]] = {
    "GGUF": [
        {
            "runtime": "llama.cpp",
            "support_status": "documented",
            "note": "GGUF container is documented for llama.cpp; "
            "per-quant/arch support is version-dependent",
        },
        {
            "runtime": "Ollama",
            "support_status": "unknown",
            "note": "Ollama consumes GGUF-family models; version/arch matrix not verified here",
        },
        {
            "runtime": "LM Studio",
            "support_status": "unknown",
            "note": "LM Studio consumes GGUF-family models; version/arch matrix not verified here",
        },
    ],
    "safetensors": [
        {
            "runtime": "Transformers",
            "support_status": "documented",
            "note": "Safetensors checkpoints load in Transformers; "
            "AWQ/GPTQ paths are integration-gated per docs",
        },
    ],
    "EXL2": [
        {
            "runtime": "ExLlamaV2",
            "support_status": "documented",
            "note": "EXL2 weights are bound to the ExLlamaV2 runtime per project docs",
        },
    ],
    "AWQ": [
        {
            "runtime": "Transformers",
            "support_status": "documented",
            "note": "AWQ is an independent family; support varies per integration",
        },
    ],
    "GPTQ": [
        {
            "runtime": "Transformers",
            "support_status": "documented",
            "note": "GPTQ is an independent family; support varies per integration",
        },
    ],
    "MLX": [
        {
            "runtime": "MLX-LM",
            "support_status": "documented",
            "note": "MLX weights target Apple Silicon unified memory, not discrete VRAM",
        },
    ],
}


def hints_for_format(container_format: str) -> list[dict]:
    """Return versioned runtime hints for a container format."""
    key = (container_format or "unknown").strip()
    base = list(_FORMAT_HINTS.get(key, []))
    out = []
    for h in base:
        out.append(
            {
                "runtime": h["runtime"],
                "support_status": h["support_status"],
                "note": h["note"],
                "source": RUNTIME_KNOWLEDGE_SOURCE,
                "observed_at": OBSERVED_AT,
            }
        )
    if not out:
        out.append(
            {
                "runtime": "unknown",
                "support_status": "unknown",
                "note": f"No documented runtime mapping for format {key!r}; stays unknown",
                "source": RUNTIME_KNOWLEDGE_SOURCE,
                "observed_at": OBSERVED_AT,
            }
        )
    return out

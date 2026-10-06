"""Core Recommendation Set: a bounded, neutrally selected evidence-closure set.

Selection is declared data plus recomputed neutral eligibility signals. The
declared signals are:

- relevance to a target VRAM tier (artifact weight footprint against nominal
  tier capacity -- a *relevance* signal, never a fit verdict);
- current availability (lifecycle active, revision resolved);
- known local inference format (container format with runtime hints);
- architecture support (Atlas canonical KV family supports the standard cache
  equation, or explicitly refuses);
- metadata completeness (identity/license/parameters/context/artifact);
- runtime relevance (documented runtime hints for the container format);
- special low-bit relevance (native low-bit / ternary / high compression);
- adoption as a *discovery* signal only, never a quality or ranking signal.

Signals explicitly excluded from selection: brand preference, repo-name
prestige, personal preference, desired final ranking, benchmark scores and
any expectation of the resulting readiness state.
"""

from __future__ import annotations

import json
from pathlib import Path

from atlas.closure import CLOSURE_SCHEMA_VERSION, CORE_SET_VERSION, REFERENCE_DATE
from atlas.intake.store import atomic_write_json
from atlas.quality.sidecars import load_records
from atlas.vram.tiers import SUPPORTED_TIERS_GB, tier_capacity_bytes

CORE_SET_POLICY_ID = "atlas-core-recommendation-set"
CORE_SET_POLICY_VERSION = CORE_SET_VERSION

SELECTION_SIGNALS = (
    "tier_relevance",
    "current_availability",
    "known_local_inference_format",
    "architecture_support",
    "metadata_completeness",
    "runtime_relevance",
    "special_low_bit_relevance",
    "adoption_as_discovery_signal_only",
)

EXCLUDED_SELECTION_SIGNALS = (
    "brand_preference",
    "repo_name_prestige",
    "personal_preference",
    "desired_final_ranking",
    "benchmark_score_expectation",
    "popularity_as_quality",
    "parameter_count_as_quality",
    "recency_as_quality",
)

# Declared candidates. artifact_set_id is mandatory: a quantized
# recommendation means one exact artifact, never "Qwen 8B".
DECLARED_CORE_CANDIDATES: tuple[dict, ...] = (
    {
        "candidate_id": "core-4g-01-qwen3-0-6b",
        "model_id": "qwen-qwen3-0-6b",
        "artifact_set_id": "qwen-qwen3-0-6b--safetensors--model.safetensors",
        "quantization_label": "bf16",
        "target_tiers": [4],
        "selection_reason": (
            "smallest released dense Qwen3 checkpoint in the catalog; exercises the 4GB tier "
            "with a resolvable standard-GQA architecture"
        ),
    },
    {
        "candidate_id": "core-4g-02-bitnet-native",
        "model_id": "microsoft-bitnet-b1-58-2b-4t",
        "artifact_set_id": "microsoft-bitnet-b1-58-2b-4t--safetensors--model.safetensors",
        "quantization_label": "native_1.58bit",
        "target_tiers": [4],
        "selection_reason": (
            "native low-bit training architecture in the catalog; relevant to the 4GB tier "
            "and to native-low-bit handling"
        ),
    },
    {
        "candidate_id": "core-4g-03-bitnet-gguf-i2s",
        "model_id": "microsoft-bitnet-b1-58-2b-4t-gguf",
        "artifact_set_id": "microsoft-bitnet-b1-58-2b-4t-gguf--gguf--ggml-model-i2_s.gguf",
        "quantization_label": "unlabeled_gguf_variant",
        "target_tiers": [4],
        "selection_reason": (
            "GGUF packaging of a native low-bit model; included to verify whether an "
            "unlabeled artifact variant can carry exact artifact identity"
        ),
    },
    {
        "candidate_id": "core-4g-04-qwen2-5-7b-iq3xs",
        "model_id": "bartowski-qwen2-5-7b-instruct-gguf",
        "artifact_set_id": (
            "bartowski-qwen2-5-7b-instruct-gguf--gguf--qwen2.5-7b-instruct-gguf--iq3_xs"
        ),
        "quantization_label": "IQ3_XS",
        "target_tiers": [4],
        "selection_reason": (
            "7B instruct model at a sub-4GiB low-bit artifact; tests whether 4GB tier "
            "relevance survives exact artifact accounting"
        ),
    },
    {
        "candidate_id": "core-4g-05-qwen3-8b-q2k",
        "model_id": "quantfactory-qwen3-8b-gguf",
        "artifact_set_id": "quantfactory-qwen3-8b-gguf--gguf--qwen3-8b-gguf--q2_k",
        "quantization_label": "Q2_K",
        "target_tiers": [4],
        "selection_reason": (
            "8B base-model GGUF at an extreme low-bit artifact; 4GB-tier relevance and "
            "high-compression evidence"
        ),
    },
    {
        "candidate_id": "core-4g-06-tinyllama-1-1b",
        "model_id": "tinyllama-tinyllama-1-1b-chat-v1-0",
        "artifact_set_id": "tinyllama-tinyllama-1-1b-chat-v1-0--safetensors--model.safetensors",
        "quantization_label": "bf16",
        "target_tiers": [4],
        "selection_reason": (
            "smallest chat release in the catalog with a resolvable architecture; included "
            "to test the Atlas context baseline against a 2K-context model"
        ),
    },
    {
        "candidate_id": "core-8g-01-qwen2-5-7b-q4km",
        "model_id": "bartowski-qwen2-5-7b-instruct-gguf",
        "artifact_set_id": (
            "bartowski-qwen2-5-7b-instruct-gguf--gguf--qwen2.5-7b-instruct-gguf--q4_k_m"
        ),
        "quantization_label": "Q4_K_M",
        "target_tiers": [8],
        "selection_reason": (
            "most-referenced 7B GGUF artifact shape in the catalog; canonical 8GB-tier "
            "quantized recommendation target"
        ),
    },
    {
        "candidate_id": "core-8g-02-qwen3-8b-q4km",
        "model_id": "quantfactory-qwen3-8b-gguf",
        "artifact_set_id": "quantfactory-qwen3-8b-gguf--gguf--qwen3-8b-gguf--q4_k_m",
        "quantization_label": "Q4_K_M",
        "target_tiers": [8],
        "selection_reason": (
            "8B release at the same quantization family as core-8g-01, from a different "
            "packager; enables artifact-vs-quantizer separation"
        ),
    },
    {
        "candidate_id": "core-8g-03-qwen3-4b-instruct-2507",
        "model_id": "qwen-qwen3-4b-instruct-2507",
        "artifact_set_id": "qwen-qwen3-4b-instruct-2507--safetensors--model.safetensors",
        "quantization_label": "bf16",
        "target_tiers": [8],
        "selection_reason": (
            "current-generation 4B instruct release whose declared checkpoint is close to "
            "the 8GB tier capacity; tests boundary honesty"
        ),
    },
    {
        "candidate_id": "core-8g-04-phi-3-mini-4k",
        "model_id": "microsoft-phi-3-mini-4k-instruct",
        "artifact_set_id": "microsoft-phi-3-mini-4k-instruct--safetensors--model.safetensors",
        "quantization_label": "bf16",
        "target_tiers": [8],
        "selection_reason": (
            "permissively licensed 3.8B release with a declared context shorter than the "
            "Atlas baseline; included to prove context incompatibility is reported, not hidden"
        ),
    },
    {
        "candidate_id": "core-8g-05-ternary-bonsai-tq1",
        "model_id": "prism-ml-ternary-bonsai-2-27b-gguf",
        "artifact_set_id": (
            "prism-ml-ternary-bonsai-2-27b-gguf--gguf--ternary-bonsai-2-27b-p.gguf--tq1_0"
        ),
        "quantization_label": "TQ1_0",
        "target_tiers": [8],
        "selection_reason": (
            "ternary TQ-format artifact; special low-bit relevance for the 8GB tier"
        ),
    },
    {
        "candidate_id": "core-8g-06-llama31-lexi-uncensored-q4",
        "model_id": "orenguteng-llama-3-1-8b-lexi-uncensored-gguf",
        "artifact_set_id": (
            "orenguteng-llama-3-1-8b-lexi-uncensored-gguf--gguf--"
            "llama-3.1-8b-lexi-uncensored-gguf--q4"
        ),
        "quantization_label": "Q4",
        "target_tiers": [8],
        "selection_reason": (
            "alignment-modified (uncensored) variant; proves a parent score is never "
            "inherited by the variant"
        ),
    },
    {
        "candidate_id": "core-12g-01-qwen3-8b-q6k",
        "model_id": "quantfactory-qwen3-8b-gguf",
        "artifact_set_id": "quantfactory-qwen3-8b-gguf--gguf--qwen3-8b-gguf--q6_k",
        "quantization_label": "Q6_K",
        "target_tiers": [12],
        "selection_reason": (
            "high-fidelity low-bit artifact of the same 8B release as core-8g-02; gives the "
            "12GB tier a same-release quantization comparison"
        ),
    },
    {
        "candidate_id": "core-12g-02-qwen38-27b-iq3s",
        "model_id": "unsloth-qwen3-8-27b-gguf",
        "artifact_set_id": "unsloth-qwen3-8-27b-gguf--gguf--qwen3.8-27b-ud-gguf--iq3_s",
        "quantization_label": "IQ3_S",
        "target_tiers": [12],
        "selection_reason": (
            "27B-class MoE release at a sub-12GiB artifact; 12GB-tier relevance for a "
            "mixture-of-experts release"
        ),
    },
    {
        "candidate_id": "core-12g-03-gpt-oss-20b-mxfp4-gguf",
        "model_id": "bartowski-openai-gpt-oss-20b-gguf",
        "artifact_set_id": (
            "bartowski-openai-gpt-oss-20b-gguf--gguf--openai_gpt-oss-20b-gguf--mxfp4"
        ),
        "quantization_label": "MXFP_4",
        "target_tiers": [12],
        "selection_reason": (
            "repackaged native-4-bit release whose catalog license record is unresolved; "
            "included to verify the license gate blocks strict status"
        ),
    },
    {
        "candidate_id": "core-16g-01-gpt-oss-20b-native",
        "model_id": "openai-gpt-oss-20b",
        "artifact_set_id": "openai-gpt-oss-20b--safetensors--original/model.safetensors",
        "quantization_label": "native_mxfp4",
        "target_tiers": [16],
        "selection_reason": (
            "official natively 4-bit release with heterogeneous attention layer types; "
            "16GB-tier reference point and a native-low-bit (non-post-training) case"
        ),
    },
    {
        "candidate_id": "core-16g-02-qwen3-coder-30b-q3km",
        "model_id": "unsloth-qwen3-coder-30b-a3b-instruct-gguf",
        "artifact_set_id": (
            "unsloth-qwen3-coder-30b-a3b-instruct-gguf--gguf--"
            "qwen3-coder-30b-a3b-instruct-gguf--q3_k_m"
        ),
        "quantization_label": "Q3_K_M",
        "target_tiers": [16],
        "selection_reason": (
            "code-specialized 30B-class MoE release at a 16GB-tier artifact; coding use-case "
            "relevance"
        ),
    },
    {
        "candidate_id": "core-16g-03-qwen3-8b",
        "model_id": "qwen-qwen3-8b",
        "artifact_set_id": "qwen-qwen3-8b--safetensors--model.safetensors",
        "quantization_label": "bf16",
        "target_tiers": [16],
        "selection_reason": (
            "8B release at native precision; 16GB-tier relevance with no post-training "
            "quantization, so no base-vs-quant retention is required"
        ),
    },
    {
        "candidate_id": "core-8g-07-ternary-heretic-tq1",
        "model_id": "os-software-ternary-bonsai-2-27b-uncensored-heretic-gguf",
        "artifact_set_id": (
            "os-software-ternary-bonsai-2-27b-uncensored-heretic-gguf--gguf--"
            "ternary-bonsai-2-27b-uncensored-heretic-p.gguf--tq1_0"
        ),
        "quantization_label": "TQ1_0",
        "target_tiers": [8, 16],
        "selection_reason": (
            "intersection of a ternary release and a heretic alignment modification; "
            "non-blocking unevaluated-alignment case"
        ),
    },
)


def closure_dir(repo_root: Path) -> Path:
    """Canonical closure output directory."""
    return repo_root / "catalog" / "closure"


def core_set_path(repo_root: Path) -> Path:
    """Canonical Core Recommendation Set location."""
    return closure_dir(repo_root) / "core-recommendation-set.json"


def load_artifacts(repo_root: Path) -> dict[str, dict]:
    """Load canonical artifact records keyed by artifact_set_id."""
    base = repo_root / "catalog" / "artifacts"
    out: dict[str, dict] = {}
    if not base.is_dir():
        return out
    for path in sorted(base.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        artifact_id = record.get("artifact_set_id")
        if isinstance(artifact_id, str) and artifact_id:
            out[artifact_id] = record
    return out


def _weight_relevant_tiers(weight_bytes: int | None) -> list[int]:
    """Tiers where the artifact's weights alone fit nominal capacity.

    This is a *selection relevance* signal computed from artifact size only.
    It is never a fit verdict: the classifier still requires an upper bound.
    """
    if not isinstance(weight_bytes, int) or weight_bytes <= 0:
        return []
    return [tier for tier in SUPPORTED_TIERS_GB if weight_bytes <= tier_capacity_bytes(tier)]


def _metadata_completeness(record: dict, artifact: dict) -> list[str]:
    """Critical metadata fields present for one exact artifact."""
    quant = record.get("quantization") or {}
    license_block = record.get("license") or {}
    ctx = record.get("context_length") or {}
    checks = {
        "license_id": bool(license_block.get("license_id")),
        "openness": record.get("openness") not in (None, "", "unknown"),
        "architecture": str(record.get("architecture") or "unknown") != "unknown",
        "total_parameters_b": isinstance(record.get("total_parameters_b"), (int, float)),
        "advertised_context": isinstance(ctx.get("advertised_max"), int),
        "resolved_revision": bool(quant.get("source_revision")),
        "artifact_revision": bool(artifact.get("revision")),
        "artifact_weight_bytes": isinstance(artifact.get("primary_weight_bytes"), int),
        "artifact_variant": bool(artifact.get("variant")),
    }
    return sorted(name for name, present in checks.items() if present)


def _architecture_support_signal(record: dict) -> str:
    """Neutral architecture-support signal from the canonical record."""
    from atlas.archinfo.capabilities import assess_capabilities

    family = str(record.get("architecture") or "unknown").strip().lower()
    if family == "unknown":
        return "unresolved"
    caps = assess_capabilities(architecture_family=family)
    if caps.standard_kv_model == "supported":
        return "standard_kv_supported"
    if caps.standard_kv_model == "unsupported":
        return "refused_by_atlas"
    return "unknown"


def _special_low_bit_signal(record: dict, artifact: dict) -> str:
    """Special low-bit relevance derived from structured catalog evidence."""
    from atlas.catalog.special import (
        compression_evidence,
        native_low_bit_status,
        ternary_status,
    )

    if native_low_bit_status(record)["is_native_low_bit"]:
        return "native_low_bit"
    kind = ternary_status(record)["kind"]
    if kind != "not-ternary":
        return kind
    if compression_evidence(record)["is_high_compression"]:
        return "high_compression"
    if artifact.get("variant"):
        return "post_training_quant"
    return "native_precision"


def candidate_record(declared: dict, record: dict, artifact: dict) -> dict:
    """Build one Core candidate with recomputed neutral eligibility signals."""
    from atlas.catalog.runtime_hints import hints_for_format

    quant = record.get("quantization") or {}
    hints = hints_for_format(str(quant.get("format") or "unknown"))
    documented = sorted(
        {str(h["runtime"]) for h in hints if h.get("support_status") == "documented"}
    )
    weight_bytes = artifact.get("primary_weight_bytes")
    alignment = record.get("alignment") or {}
    return {
        "schema_version": CLOSURE_SCHEMA_VERSION,
        "candidate_id": declared["candidate_id"],
        "model_id": declared["model_id"],
        "artifact_set_id": declared["artifact_set_id"],
        "quantization_label": declared["quantization_label"],
        "artifact_variant": artifact.get("variant"),
        "artifact_filename": next(
            (
                f.get("filename")
                for f in (artifact.get("files") or [])
                if isinstance(f, dict) and f.get("filename")
            ),
            None,
        ),
        "artifact_weight_bytes": weight_bytes,
        "artifact_revision": artifact.get("revision"),
        "container_format": quant.get("format"),
        "target_tiers": list(declared["target_tiers"]),
        "alignment_variant": alignment.get("alignment_variant"),
        "license_id": (record.get("license") or {}).get("license_id"),
        "openness": record.get("openness"),
        "catalog_architecture": record.get("architecture"),
        "selection_reason": declared["selection_reason"],
        "signals": {
            "tier_relevance_by_weight_only": _weight_relevant_tiers(weight_bytes),
            "current_availability": str(record.get("lifecycle_status") or "unknown"),
            "known_local_inference_format": str(quant.get("format") or "unknown"),
            "architecture_support": _architecture_support_signal(record),
            "metadata_completeness": _metadata_completeness(record, artifact),
            "runtime_relevance_documented": documented,
            "special_low_bit_relevance": _special_low_bit_signal(record, artifact),
            "adoption_discovery_signal_only": {
                "downloads": (record.get("popularity") or {}).get("downloads"),
                "likes": (record.get("popularity") or {}).get("likes"),
                "usage": "discovery_only_never_quality_or_ranking",
            },
        },
    }


def build_core_set(*, repo_root: Path) -> dict:
    """Recompute the declared Core Recommendation Set from canonical data."""
    records = load_records(repo_root)
    artifacts = load_artifacts(repo_root)
    candidates: list[dict] = []
    problems: list[dict] = []
    for declared in DECLARED_CORE_CANDIDATES:
        record = records.get(str(declared["model_id"]))
        artifact = artifacts.get(str(declared["artifact_set_id"]))
        if record is None:
            problems.append(
                {
                    "candidate_id": declared["candidate_id"],
                    "reason": "model_record_absent_from_catalog",
                    "model_id": declared["model_id"],
                }
            )
            continue
        if artifact is None:
            problems.append(
                {
                    "candidate_id": declared["candidate_id"],
                    "reason": "artifact_set_absent_from_catalog",
                    "artifact_set_id": declared["artifact_set_id"],
                }
            )
            continue
        candidates.append(candidate_record(declared, record, artifact))

    tier_counts: dict[str, int] = {str(tier): 0 for tier in SUPPORTED_TIERS_GB}
    for candidate in candidates:
        for tier in candidate["target_tiers"]:
            tier_counts[str(tier)] += 1
    unique_models = sorted({str(c["model_id"]) for c in candidates})
    unique_artifacts = sorted({str(c["artifact_set_id"]) for c in candidates})
    return {
        "schema_version": CLOSURE_SCHEMA_VERSION,
        "set_version": CORE_SET_VERSION,
        "policy_id": CORE_SET_POLICY_ID,
        "policy_version": CORE_SET_POLICY_VERSION,
        "reference_date": REFERENCE_DATE,
        "purpose": (
            "bounded evidence-closure set for the 4/8/12/16GB tiers; members are "
            "candidates for evidence work, not winners"
        ),
        "selection_signals": list(SELECTION_SIGNALS),
        "excluded_selection_signals": list(EXCLUDED_SELECTION_SIGNALS),
        "counts": {
            "candidate_count": len(candidates),
            "unique_model_count": len(unique_models),
            "unique_artifact_count": len(unique_artifacts),
            "per_tier_declared": tier_counts,
        },
        "unique_model_ids": unique_models,
        "unique_artifact_set_ids": unique_artifacts,
        "candidates": candidates,
        "resolution_problems": problems,
        "determinism": (
            "candidates and signals are recomputed from canonical catalog records; the "
            "declaration order is stable and no field depends on wall-clock time"
        ),
    }


def write_core_set(*, repo_root: Path, dry_run: bool = True) -> tuple[dict, Path]:
    """Materialize the Core Recommendation Set (dry-run by default)."""
    payload = build_core_set(repo_root=repo_root)
    target = core_set_path(repo_root)
    if not dry_run:
        atomic_write_json(target, payload)
    return payload, target


def load_core_set(*, repo_root: Path) -> dict | None:
    """Load a persisted Core Recommendation Set, or None when absent."""
    path = core_set_path(repo_root)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None

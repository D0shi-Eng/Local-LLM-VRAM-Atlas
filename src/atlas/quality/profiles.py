"""Multi-axis quality profiles (Phase 6).

Deterministic: the same evidence snapshot yields the same profile. No
timestamps enter profile identity. Missing axes stay ``unknown`` and are
never averaged as zero. Raw cross-metric aggregation (MMLU + Elo + pass@k)
is refused outright.
"""

from __future__ import annotations

import hashlib
import re

from atlas.quality import QUALITY_POLICY_ID, QUALITY_SCHEMA_VERSION
from atlas.quality.comparability import compare
from atlas.quality.tiers import evidence_status_from_origins, is_independent_status

PROFILE_DOMAIN = "atlas-quality-profile/v1"

# Declared capability axes. An axis is only emitted when evidence exists for
# it; no axis is ever synthesized.
AXES = (
    "general_intelligence",
    "reasoning",
    "coding",
    "agentic_tool_use",
    "instruction_following",
    "knowledge",
    "long_context",
    "multilingual",
    "arabic",
    "multimodal",
    "non_hallucination",
    "safety_refusal_behavior",
    "professional_tasks",
)

# Axis inference from explicit benchmark/task evidence only.
_AXIS_BY_BENCHMARK: dict[str, tuple[str, ...]] = {
    "mmlu": ("general_intelligence", "knowledge"),
    "mmlu-pro": ("general_intelligence", "knowledge"),
    "mmlu-redux": ("general_intelligence",),
    "gpqa": ("reasoning", "knowledge"),
    "gpqa-diamond": ("reasoning", "knowledge"),
    "hle": ("reasoning", "knowledge"),
    "aime": ("reasoning",),
    "math-500": ("reasoning",),
    "cnmo-2024": ("reasoning",),
    "drop": ("reasoning",),
    "hellaswag": ("general_intelligence",),
    "arc": ("general_intelligence",),
    "piqa": ("general_intelligence",),
    "winogrande": ("general_intelligence",),
    "commonsenseqa": ("general_intelligence",),
    "opbookqa": ("general_intelligence",),
    "openbookqa": ("general_intelligence",),
    "triviaqa": ("knowledge",),
    "simpleqa": ("knowledge", "non_hallucination"),
    "bbh": ("reasoning",),
    "gsm8k": ("reasoning",),
    "humaneval": ("coding",),
    "mbpp": ("coding",),
    "livecodebench": ("coding",),
    "codeforces": ("coding", "reasoning"),
    "swe-verified": ("coding", "agentic_tool_use"),
    "ifeval": ("instruction_following",),
    "mt-bench": ("instruction_following",),
    "taubench": ("agentic_tool_use",),
    "tau-bench": ("agentic_tool_use",),
    "terminal-bench": ("agentic_tool_use", "coding"),
    "aider-polyglot": ("coding",),
    "mgsm": ("reasoning", "multilingual"),
    "c-eval": ("general_intelligence", "multilingual"),
    "cluewsc": ("general_intelligence", "multilingual"),
    "simpleevals-ar": ("arabic",),
    "global-mmlu-lite": ("multilingual",),
    "arabic": ("arabic",),
    "long-context": ("long_context",),
    "aa-lcr": ("long_context",),
    "mlcr-aa": ("long_context",),
    "mMMU-pro".lower(): ("multimodal",),
    "ifbench": ("instruction_following",),
}

# Refusal behaviour is never folded into general capability.
_REFUSAL_BENCHMARKS = frozenset({"refusalbench", "or-bench", "xstest"})


def _matches(haystack: str, token: str) -> bool:
    """Word-boundary match so 'mmlu' never matches inside another metric name."""
    return re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", haystack) is not None


def axis_for_result(result: dict) -> tuple[str, ...]:
    """Axes supported by one evaluation result (explicit mapping only).

    The benchmark identity is matched first; the task label is consulted only
    when the benchmark id carries no mapping, so a generic metric string can
    never pull a result into an unrelated axis.
    """
    benchmark_id = str(result.get("benchmark_id") or "").strip().lower()
    task = str(result.get("task") or "").strip().lower()
    matched: list[str] = []
    for token, axes in _AXIS_BY_BENCHMARK.items():
        if _matches(benchmark_id, token) or _matches(task, token):
            matched.extend(axes)
    if not matched:
        for token, axes in _AXIS_BY_BENCHMARK.items():
            if _matches(str(result.get("metric") or "").strip().lower(), token):
                matched.extend(axes)
    for token in _REFUSAL_BENCHMARKS:
        if _matches(benchmark_id, token) or _matches(task, token):
            matched.append("safety_refusal_behavior")
    # Preserve declared axis order, no duplicates.
    return tuple(axis for axis in AXES if axis in set(matched))


def _profile_id(model_id: str, evaluation_ids: list[str], policy_version: str) -> str:
    digest = hashlib.sha256(
        "\x1f".join(
            [
                PROFILE_DOMAIN,
                model_id.strip().lower(),
                policy_version.strip(),
                *sorted(evaluation_ids),
            ]
        ).encode("utf-8")
    ).hexdigest()
    return f"qp-v1-{digest}"


def build_profile(
    *,
    model_id: str,
    results: list[dict],
    quality_snapshot_version: str,
    policy_id: str = QUALITY_POLICY_ID,
    policy_version: str = "0.6.0",
) -> dict:
    """Build the multi-axis profile for one model from its evaluations.

    Only exact-match results count as profile evidence. Conflicting
    evaluations surface as an axis note rather than being hidden, and
    disagreements between independent sources are exposed, not averaged away.
    """
    usable = [r for r in results if str(r.get("match_status", "")).startswith("exact")]
    superseded = [r for r in usable if r.get("superseded")]

    axes: dict[str, dict] = {}
    for result in usable:
        if result.get("superseded"):
            continue
        for axis in axis_for_result(result):
            block = axes.setdefault(axis, {"status": "known", "evaluation_ids": []})
            block["evaluation_ids"].append(str(result.get("evaluation_id")))

    # Detect intra-axis source disagreement (same benchmark+version, different score).
    disagreements: list[str] = []
    for axis, block in axes.items():
        groups: dict[tuple, dict[str, float]] = {}
        for result in usable:
            if result.get("superseded"):
                continue
            if axis not in axis_for_result(result):
                continue
            key = (
                str(result.get("benchmark_id")),
                str(result.get("benchmark_version")),
                str(result.get("metric")),
                str(result.get("score_unit")),
                str(result.get("reasoning_mode")),
            )
            score = result.get("score")
            if not isinstance(score, (int, float)):
                continue
            groups.setdefault(key, {})[str(result.get("source_id"))] = float(score)
        for key, by_source in sorted(groups.items()):
            values = sorted(by_source.values())
            if len(values) > 1 and (values[-1] - values[0]) > 0:
                disagreements.append(
                    f"{axis}: {key[0]} v{key[1]} {key[2]} reported {len(values)} "
                    f"different values across sources"
                )
        block["evaluation_ids"] = sorted(set(block["evaluation_ids"]))

    for block in axes.values():
        if block["evaluation_ids"]:
            block["status"] = "known"
    for axis in AXES:
        axes.setdefault(axis, {"status": "unknown", "evaluation_ids": []})

    for note in disagreements:
        target = note.split(":", 1)[0].strip()
        if target in axes:
            axes[target]["note"] = note

    origins = [str(r.get("evaluation_origin")) for r in usable if not r.get("superseded")]
    verifications = [str(r.get("verification_status")) for r in usable if not r.get("superseded")]
    independent_sources = [
        str(r.get("source_id"))
        for r in usable
        if not r.get("superseded") and str(r.get("evaluation_origin")) == "independent"
    ]
    evidence_status = evidence_status_from_origins(
        origins,
        verification_statuses=verifications,
        independent_sources=independent_sources,
    )

    hqc, rationale = _high_quality_candidate(
        axes=axes, evidence_status=evidence_status, usable=usable, superseded=superseded
    )

    return {
        "schema_version": QUALITY_SCHEMA_VERSION,
        "profile_id": _profile_id(
            model_id, [str(r.get("evaluation_id")) for r in usable], policy_version
        ),
        "model_id": model_id,
        "quality_snapshot_version": quality_snapshot_version,
        "policy_id": policy_id,
        "policy_version": policy_version,
        "axes": axes,
        "evidence_status": evidence_status,
        "high_quality_candidate": hqc,
        "high_quality_rationale": rationale,
    }


def _high_quality_candidate(
    *,
    axes: dict[str, dict],
    evidence_status: str,
    usable: list[dict],
    superseded: list[dict],
) -> tuple[bool | None, str | None]:
    """Policy-defined eligibility: never popular, large, new or official."""
    if not usable:
        return False, "no exact-match evaluation evidence"
    known = [axis for axis, block in axes.items() if block.get("status") == "known"]
    if not known:
        return False, "no capability axis has defensible evidence"
    if not is_independent_status(evidence_status):
        return False, f"evidence status {evidence_status} is below the independent threshold"
    if any(str(r.get("match_status")) == "identity_conflict" for r in usable):
        return False, "unresolved identity conflict present"
    if superseded:
        return False, "superseded evaluation evidence present"
    return True, (
        f"independent evidence on {len(known)} axis/axes "
        f"({', '.join(sorted(known)[:4])}); popularity, size, recency and brand excluded"
    )


def aggregate_axis_scores(*, results: list[dict]) -> dict:
    """Refuse raw cross-metric aggregation; expose per-metric values only.

    Averaging MMLU accuracy, Elo and pass@k has no defined meaning, so Atlas
    does not do it. Within one benchmark+version+metric population a ranking is
    still available (see comparability.rank_within_benchmark).
    """
    by_metric: dict[str, dict] = {}
    for result in results:
        metric = str(result.get("metric"))
        by_metric.setdefault(metric, {"values": [], "benchmark_ids": set()})
        by_metric[metric]["values"].append(result.get("score"))
        by_metric[metric]["benchmark_ids"].add(str(result.get("benchmark_id")))
    return {
        "aggregation": "refused",
        "reason": "raw metrics across benchmarks are not comparable; no weighted average defined",
        "per_metric": {
            metric: {
                "values": block["values"],
                "benchmark_ids": sorted(block["benchmark_ids"]),
            }
            for metric, block in sorted(by_metric.items())
        },
    }


def source_disagreements(results: list[dict]) -> list[str]:
    """Report independent sources that disagree (never cherry-picked)."""
    notes: list[str] = []
    groups: dict[tuple, dict[str, float]] = {}
    for result in results:
        key = (
            str(result.get("model_id")),
            str(result.get("benchmark_id")),
            str(result.get("benchmark_version")),
            str(result.get("metric")),
        )
        score = result.get("score")
        if isinstance(score, (int, float)):
            groups.setdefault(key, {})[str(result.get("source_id"))] = float(score)
    for key, by_source in sorted(groups.items()):
        if len(by_source) > 1:
            values = sorted(by_source.values())
            if values[-1] != values[0]:
                notes.append(
                    f"{key[0]} {key[1]} v{key[2]} {key[3]}: "
                    + ", ".join(f"{src}={val}" for src, val in sorted(by_source.items()))
                )
    return notes


def comparability_audit(left: dict, right: dict) -> dict:
    """Thin re-export so views can explain profile-level comparability."""
    return compare(left, right)

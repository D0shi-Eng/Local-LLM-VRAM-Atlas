"""Benchmark identity, version handling and comparability rules.

Two results are only comparable when *everything that changes the score* is
identical: benchmark id and version, metric and unit, reasoning mode, tool
mode, prompting mode and context configuration. Anything unknown blocks the
comparison instead of being assumed equal.
"""

from __future__ import annotations

# Fields that must match before two scores may be compared.
COMPARABILITY_FIELDS = (
    "benchmark_id",
    "benchmark_version",
    "metric",
    "score_unit",
    "reasoning_mode",
    "tool_mode",
    "prompting_mode",
    "context_configuration",
)

# Settings whose mismatch blocks comparison outright (vs. degrades it).
MATERIAL_FIELDS = (
    "benchmark_version",
    "metric",
    "score_unit",
    "reasoning_mode",
    "tool_mode",
)


def _normalized(value: object) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, str):
        text = value.strip().lower()
        return text if text else "unknown"
    return str(value)


def comparison_key(result: dict) -> tuple[str, ...]:
    """Exact comparable-setting key for one evaluation result."""
    return tuple(_normalized(result.get(field)) for field in COMPARABILITY_FIELDS)


def is_comparable(left: dict, right: dict) -> bool:
    """True only when both results share the full comparable setup."""
    return comparison_key(left) == comparison_key(right)


def compare(left: dict, right: dict) -> dict:
    """Explain whether two results may be compared, and why not.

    Returns ``comparable``, the differing fields, and whether any differing
    field is material (benchmark version, metric, unit, reasoning/tool mode).
    """
    differing = [
        field
        for field in COMPARABILITY_FIELDS
        if _normalized(left.get(field)) != _normalized(right.get(field))
    ]
    material = [field for field in differing if field in MATERIAL_FIELDS]
    return {
        "comparable": not differing,
        "differing_fields": differing,
        "material_differences": material,
        "reason": (
            "identical benchmark version, metric, unit and evaluation settings"
            if not differing
            else "materially different settings: " + ", ".join(differing)
        ),
    }


def rank_within_benchmark(results: list[dict]) -> dict[str, dict]:
    """Rank results inside one exact benchmark+version+mode population.

    Only results with identical comparability keys participate. A population of
    one yields no rank (a single result is not a ranking). Population size and raw
    scores are preserved; nothing is normalized across metrics.
    """
    grouped: dict[tuple[str, ...], list[dict]] = {}
    for result in results:
        if result.get("superseded"):
            continue
        grouped.setdefault(comparison_key(result), []).append(result)

    ranked: dict[str, dict] = {}
    for group in grouped.values():
        direction = _normalized(group[0].get("metric_direction"))
        higher_is_better = direction != "lower_is_better"

        def sort_key(item: dict, *, higher: bool = higher_is_better) -> tuple[float, str]:
            score = item.get("score")
            value = float(score) if isinstance(score, (int, float)) else float("-inf")
            # Stable, deterministic tie-break on evaluation_id.
            return (-value if higher else value, str(item.get("evaluation_id")))

        ordered = sorted(group, key=sort_key)
        population = len(ordered)
        if population < 2:
            # A single result is not a ranking: there is nothing to compare it to.
            continue
        for index, item in enumerate(ordered, start=1):
            ranked[str(item.get("evaluation_id"))] = {
                "benchmark_id": item.get("benchmark_id"),
                "benchmark_version": item.get("benchmark_version"),
                "metric": item.get("metric"),
                "metric_direction": item.get("metric_direction"),
                "raw_score": item.get("score"),
                "rank": index,
                "population_size": population,
                "percentile": _percentile(index, population),
            }
    return ranked


def _percentile(rank: int, population: int) -> float | None:
    """Documented percentile: ties share the best rank, population is explicit."""
    if population <= 0:
        return None
    return round((population - rank + 1) / population, 4)


PERCENTILE_RULES = (
    "population = exact comparable setup (benchmark id + version + metric + unit + modes)",
    "ties share the best rank achieved in that population",
    "percentile = (population - rank + 1) / population, higher is better",
    "missing or superseded results are excluded from the population, never counted as zero",
    "computed by Atlas; not attributed to the source unless the source provides it",
)

"""Declared quality-evidence ingestion set (Phase 6).

Rows below are transcribed from public, publisher-published result tables that
were read live at the reference date. Each row keeps its raw metric, its
decoding/prompting context and its source; Atlas adds no score of its own.

Only flagships with an exact, unambiguous identity are included. Popularity,
size, recency and publisher brand are never fields here.
"""

from __future__ import annotations

# Evaluation date is not invented: publisher cards do not state one, so the
# field stays None (unknown) and freshness is expressed via supersession.
OBSERVED_AT = "2026-10-05T00:00:00Z"

DECLARED_RESULTS: list[dict] = [
    # ---------------------------------------------------------------- DeepSeek-R1
    {
        "repo_id": "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
        "model_id": "deepseek-ai-deepseek-r1-distill-qwen-7b",
        "source_id": "deepseek-r1-repo-report",
        "source_url": "https://github.com/deepseek-ai/DeepSeek-R1",
        "evaluator": "DeepSeek-AI",
        "evaluation_origin": "publisher",
        "verification_status": "publisher_claim",
        "prompting_mode": "no system prompt (publisher recommendation)",
        "context_configuration": "max generation length 32768 tokens",
        "reasoning_mode": "reasoning",
        "rows": [
            {
                "benchmark_name": "AIME 2024",
                "benchmark_id": "aime-2024",
                "benchmark_version": "2024",
                "task": "competition_math",
                "metric": "AIME 2024 pass@1",
                "metric_direction": "higher_is_better",
                "score": 55.5,
                "score_unit": "percent",
            },
            {
                "benchmark_name": "AIME 2024 (cons@64)",
                "benchmark_id": "aime-2024-cons64",
                "benchmark_version": "2024",
                "task": "competition_math",
                "metric": "AIME 2024 cons@64",
                "metric_direction": "higher_is_better",
                "score": 83.3,
                "score_unit": "percent",
            },
            {
                "benchmark_name": "MATH-500",
                "benchmark_id": "math-500",
                "task": "competition_math",
                "metric": "MATH-500 pass@1",
                "metric_direction": "higher_is_better",
                "score": 92.8,
                "score_unit": "percent",
            },
            {
                "benchmark_name": "GPQA Diamond",
                "benchmark_id": "gpqa-diamond",
                "task": "graduate_science_qa",
                "metric": "GPQA Diamond pass@1",
                "metric_direction": "higher_is_better",
                "score": 49.1,
                "score_unit": "percent",
            },
            {
                "benchmark_name": "LiveCodeBench",
                "benchmark_id": "livecodebench",
                "task": "code_generation",
                "metric": "LiveCodeBench pass@1",
                "metric_direction": "higher_is_better",
                "score": 37.6,
                "score_unit": "percent",
            },
            {
                "benchmark_name": "Codeforces",
                "benchmark_id": "codeforces",
                "task": "competitive_programming",
                "metric": "Codeforces rating",
                "metric_direction": "higher_is_better",
                "score": 1189.0,
                "score_unit": "elo_rating",
            },
        ],
        "decoding_note": (
            "Publisher states temperature 0.6, top-p 0.95 and 64 samples per query for "
            "pass@1 estimation."
        ),
    },
    # ---------------------------------------------------------------- SmolLM2
    {
        "repo_id": "HuggingFaceTB/SmolLM2-1.7B-Instruct",
        "model_id": "huggingfacetb-smollm2-1-7b-instruct",
        "source_id": "smollm2-model-card",
        "source_url": "https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct",
        "evaluator": "HuggingFaceTB",
        "evaluation_origin": "publisher",
        "verification_status": "publisher_claim",
        "prompting_mode": "lighteval, zero-shot unless stated",
        "reasoning_mode": "non-reasoning",
        "rows": [
            {
                "benchmark_name": "IFEval (Average prompt/inst)",
                "benchmark_id": "ifeval",
                "task": "instruction_following",
                "metric": "IFEval average prompt/instruction strict accuracy",
                "metric_direction": "higher_is_better",
                "score": 56.7,
                "score_unit": "percent",
            },
            {
                "benchmark_name": "MMLU-Pro (MCF)",
                "benchmark_id": "mmlu-pro",
                "task": "multiple_choice",
                "metric": "MMLU-Pro multiple-choice factor accuracy",
                "metric_direction": "higher_is_better",
                "score": 19.3,
                "score_unit": "percent",
            },
            {
                "benchmark_name": "BBH (3-shot)",
                "benchmark_id": "bbh",
                "benchmark_version": "3-shot",
                "task": "reasoning",
                "metric": "BBH 3-shot accuracy",
                "metric_direction": "higher_is_better",
                "score": 32.2,
                "score_unit": "percent",
            },
            {
                "benchmark_name": "GSM8K (5-shot)",
                "benchmark_id": "gsm8k",
                "benchmark_version": "5-shot",
                "task": "grade_school_math",
                "metric": "GSM8K 5-shot accuracy",
                "metric_direction": "higher_is_better",
                "score": 48.2,
                "score_unit": "percent",
            },
            {
                "benchmark_name": "HellaSwag",
                "benchmark_id": "hellaswag",
                "task": "commonsense_completion",
                "metric": "HellaSwag accuracy",
                "metric_direction": "higher_is_better",
                "score": 66.1,
                "score_unit": "percent",
            },
            {
                "benchmark_name": "MT-Bench",
                "benchmark_id": "mt-bench",
                "task": "open_ended_chat",
                "metric": "MT-Bench judge score",
                "metric_direction": "higher_is_better",
                "score": 6.13,
                "score_unit": "judge_score_1_10",
            },
        ],
        "decoding_note": "Publisher states lighteval harness; shot count is part of comparability.",
    },
    # ---------------------------------------------------------------- phi-4
    {
        "repo_id": "microsoft/phi-4",
        "model_id": "microsoft-phi-4",
        "source_id": "phi4-model-card",
        "source_url": "https://huggingface.co/microsoft/phi-4",
        "evaluator": "Microsoft Research",
        "evaluation_origin": "publisher",
        "verification_status": "publisher_claim",
        "prompting_mode": "simple-evals",
        "reasoning_mode": "non-reasoning",
        "rows": [
            {
                "benchmark_name": "MMLU",
                "benchmark_id": "mmlu",
                "task": "multiple_choice",
                "metric": "MMLU accuracy",
                "metric_direction": "higher_is_better",
                "score": 84.8,
                "score_unit": "percent",
            },
            {
                "benchmark_name": "GPQA",
                "benchmark_id": "gpqa",
                "task": "graduate_science_qa",
                "metric": "GPQA accuracy",
                "metric_direction": "higher_is_better",
                "score": 56.1,
                "score_unit": "percent",
            },
            {
                "benchmark_name": "MATH",
                "benchmark_id": "math",
                "task": "competition_math",
                "metric": "MATH accuracy",
                "metric_direction": "higher_is_better",
                "score": 80.4,
                "score_unit": "percent",
            },
            {
                "benchmark_name": "HumanEval",
                "benchmark_id": "humaneval",
                "task": "code_generation",
                "metric": "HumanEval pass@1",
                "metric_direction": "higher_is_better",
                "score": 82.6,
                "score_unit": "percent",
            },
            {
                "benchmark_name": "MGSM",
                "benchmark_id": "mgsm",
                "task": "multilingual_math",
                "metric": "MGSM accuracy",
                "metric_direction": "higher_is_better",
                "score": 80.6,
                "score_unit": "percent",
            },
            {
                "benchmark_name": "DROP",
                "benchmark_id": "drop",
                "task": "reading_comprehension",
                "metric": "DROP F1",
                "metric_direction": "higher_is_better",
                "score": 75.5,
                "score_unit": "f1_points",
            },
            {
                "benchmark_name": "SimpleQA",
                "benchmark_id": "simpleqa",
                "task": "short_form_factual",
                "metric": "SimpleQA correct",
                "metric_direction": "higher_is_better",
                "score": 3.0,
                "score_unit": "percent",
            },
        ],
        "decoding_note": (
            "Publisher notes some simple-evals scores differ from third-party figures because of "
            "formatting requirements; recorded as an explicit source-conflict signal."
        ),
    },
]


def claims(evidence_ids_by_model: dict[str, list[str]]) -> list[dict]:
    """Flatten declared results into ingestion claims with evidence ids."""
    out: list[dict] = []
    for group in DECLARED_RESULTS:
        evidence_ids = list(evidence_ids_by_model.get(str(group["model_id"]), []))
        for row in group["rows"]:
            claim = {
                "repo_id": group["repo_id"],
                "model_id": group["model_id"],
                "source_id": group["source_id"],
                "source_url": group["source_url"],
                "evaluator": group["evaluator"],
                "evaluation_origin": group["evaluation_origin"],
                "verification_status": group["verification_status"],
                "prompting_mode": group.get("prompting_mode"),
                "reasoning_mode": group.get("reasoning_mode"),
                "context_configuration": group.get("context_configuration"),
                "evaluation_date": None,
                "notes": group.get("decoding_note"),
            }
            claim.update(row)
            if evidence_ids:
                claim["evidence_ids"] = [evidence_ids[0]]
            out.append(claim)
    return out

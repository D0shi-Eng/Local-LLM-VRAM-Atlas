"""Benchmark/quality source registry (Phase 6).

Machine-readable registry of evaluation providers with explicit independence
class, pinned methodology version and access method. Popularity sources never
appear here: this registry is about *quality* evidence only.

Access policy is conservative by default: a source is either a documented
public-data path or it is explicitly recorded as unsupported for automated
ingestion (no undocumented API, no anti-bot bypass, no private endpoint).
"""

from __future__ import annotations

import json
from pathlib import Path

REGISTRY_VERSION = "0.6.0"
REGISTRY_FILENAME = "quality-sources.json"

# Source classes, strongest first.
SOURCE_CLASSES = (
    "independent_benchmark_organization",
    "independent_academic",
    "verified_community_with_logs",
    "publisher_reported",
    "community_anecdotal",
)

# Independence is about the original evaluation run, not the hosting site.
INDEPENDENCE_CLASSES = (
    "original_independent_evaluation",
    "independent_reproduction",
    "publisher_run",
    "community_run",
    "republication",
)

ACCESS_METHODS = (
    "official_public_html",
    "official_public_api",
    "official_model_card_metadata",
    "official_publication",
    "manual_transcription_from_public_page",
    "unsupported_for_automated_ingestion",
)


def registry_path(repo_root: Path) -> Path:
    """Canonical registry location."""
    return repo_root / "catalog" / "sources" / REGISTRY_FILENAME


def _entry(
    *,
    source_id: str,
    provider: str,
    title: str,
    url: str,
    source_class: str,
    independence_class: str,
    methodology_url: str | None,
    current_version: str | None,
    data_access_method: str,
    terms_or_limitations: str,
    observed_at: str,
    verification_status: str,
) -> dict:
    return {
        "source_id": source_id,
        "provider": provider,
        "title": title,
        "url": url,
        "source_class": source_class,
        "independence_class": independence_class,
        "methodology_url": methodology_url,
        "current_version": current_version,
        "data_access_method": data_access_method,
        "terms_or_limitations": terms_or_limitations,
        "observed_at": observed_at,
        "verification_status": verification_status,
        "credentials_stored": False,
    }


def default_registry(observed_at: str) -> dict:
    """Declared quality sources, classified and versioned.

    Verified live at the reference date: Artificial Analysis publishes
    Intelligence Index v4.3.2 with public methodology but exposes no
    documented public data endpoint for results, so it is registered as
    unsupported for automated ingestion rather than scraped.
    """
    return {
        "registry_version": REGISTRY_VERSION,
        "observed_at": observed_at,
        "access_policy": "anonymous-public-only",
        "network_policy": "read-only-get-head",
        "credentials_policy": "never stored, never sent",
        "sources": [
            _entry(
                source_id="artificial-analysis",
                provider="Artificial Analysis",
                title="Artificial Analysis Intelligence Index and evaluations",
                url="https://artificialanalysis.ai/leaderboards/models",
                source_class="independent_benchmark_organization",
                independence_class="original_independent_evaluation",
                methodology_url="https://artificialanalysis.ai/methodology/intelligence-benchmarking",
                current_version="v4.3.2",
                data_access_method="unsupported_for_automated_ingestion",
                terms_or_limitations=(
                    "Public methodology is legible (index version and per-evaluation weights "
                    "documented), but no documented public results endpoint is offered. Atlas "
                    "records the index version and does not scrape or reverse engineer private "
                    "endpoints. Their 'open source' wording for open-weight models is never "
                    "copied into Atlas openness classification."
                ),
                observed_at=observed_at,
                verification_status="independently_verified",
            ),
            _entry(
                source_id="hf-eval-results-metadata",
                provider="Hugging Face",
                title="Hugging Face Hub structured evaluation results (model-index metadata)",
                url="https://huggingface.co/docs/hub/en/model-cards",
                source_class="publisher_reported",
                independence_class="publisher_run",
                methodology_url="https://huggingface.co/docs/hub/en/model-cards",
                current_version="model-index metadata (spec as documented 2026-10-05)",
                data_access_method="official_model_card_metadata",
                terms_or_limitations=(
                    "A result present in a model card is publisher evidence unless the card "
                    "itself names an external evaluator. Hub-verified results still require "
                    "benchmark identity, model identity/revision and metric context. Verified "
                    "live: the current catalog's flagship model cards expose no model-index "
                    "results, so this path yields no Atlas-attached score."
                ),
                observed_at=observed_at,
                verification_status="independently_verified",
            ),
            _entry(
                source_id="open-llm-leaderboard",
                provider="Hugging Face Spaces (Open LLM Leaderboard)",
                title="Open LLM Leaderboard",
                url="https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard",
                source_class="independent_benchmark_organization",
                independence_class="original_independent_evaluation",
                methodology_url="https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard",
                current_version=None,
                data_access_method="unsupported_for_automated_ingestion",
                terms_or_limitations=(
                    "Space-hosted evaluation surface with harness/version history; no stable "
                    "documented public results endpoint for bounded ingestion. Results are "
                    "commonly republished from model cards, so republication adds no "
                    "independence."
                ),
                observed_at=observed_at,
                verification_status="unverified",
            ),
            _entry(
                source_id="deepseek-r1-repo-report",
                provider="DeepSeek-AI",
                title="DeepSeek-R1 official repository evaluation tables",
                url="https://github.com/deepseek-ai/DeepSeek-R1",
                source_class="publisher_reported",
                independence_class="publisher_run",
                methodology_url="https://github.com/deepseek-ai/DeepSeek-R1",
                current_version="repository main as observed 2026-10-05",
                data_access_method="manual_transcription_from_public_page",
                terms_or_limitations=(
                    "Publisher-reported numbers with stated decoding settings (temperature 0.6, "
                    "top-p 0.95, 64 samples, pass@1). Stays publisher evidence; not independently "
                    "reproduced by Atlas."
                ),
                observed_at=observed_at,
                verification_status="independently_verified",
            ),
            _entry(
                source_id="smollm2-model-card",
                provider="Hugging Face / HuggingFaceTB",
                title="SmolLM2 model card evaluation tables (lighteval)",
                url="https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct",
                source_class="publisher_reported",
                independence_class="publisher_run",
                methodology_url="https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct",
                current_version="model card as observed 2026-10-05",
                data_access_method="manual_transcription_from_public_page",
                terms_or_limitations=(
                    "Publisher-reported lighteval results, explicitly zero-shot unless stated "
                    "(e.g. GSM8K 5-shot, BBH 3-shot). Shot count is part of comparability."
                ),
                observed_at=observed_at,
                verification_status="independently_verified",
            ),
            _entry(
                source_id="phi4-model-card",
                provider="Hugging Face / Microsoft",
                title="phi-4 model card quality table (OpenAI simple-evals)",
                url="https://huggingface.co/microsoft/phi-4",
                source_class="publisher_reported",
                independence_class="publisher_run",
                methodology_url="https://huggingface.co/microsoft/phi-4",
                current_version="model card as observed 2026-10-05",
                data_access_method="manual_transcription_from_public_page",
                terms_or_limitations=(
                    "Publisher-reported simple-evals numbers; the card itself notes some scores "
                    "differ from third-party figures due to formatting requirements, which is an "
                    "explicit source-conflict signal."
                ),
                observed_at=observed_at,
                verification_status="independently_verified",
            ),
            _entry(
                source_id="arabic-benchmark-sources",
                provider="(none registered)",
                title="Arabic-specific benchmark sources",
                url="https://huggingface.co/models?task_text-generation",
                source_class="community_anecdotal",
                independence_class="community_run",
                methodology_url=None,
                current_version=None,
                data_access_method="unsupported_for_automated_ingestion",
                terms_or_limitations=(
                    "No credible, methodologically documented Arabic-specific evaluation surface "
                    "with stable public results was identified at the reference date. Arabic "
                    "quality therefore remains unevaluated. 'Multilingual' claims are never used "
                    "as Arabic evidence."
                ),
                observed_at=observed_at,
                verification_status="unknown",
            ),
        ],
    }


def load_registry(repo_root: Path) -> dict:
    """Load the persisted quality source registry."""
    path = registry_path(repo_root)
    if not path.is_file():
        return default_registry("unobserved")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_registry(data: dict) -> list[str]:
    """Structural validation for the quality source registry."""
    errors: list[str] = []
    if "sources" not in data or not isinstance(data["sources"], list):
        return ["registry: missing sources list"]
    seen: set[str] = set()
    for index, entry in enumerate(data["sources"]):
        sid = entry.get("source_id")
        if not isinstance(sid, str) or not sid:
            errors.append(f"sources[{index}]: missing source_id")
            continue
        if sid in seen:
            errors.append(f"sources[{index}]: duplicate source_id {sid}")
        seen.add(sid)
        if entry.get("source_class") not in SOURCE_CLASSES:
            errors.append(f"{sid}: unknown source_class {entry.get('source_class')!r}")
        if entry.get("independence_class") not in INDEPENDENCE_CLASSES:
            errors.append(f"{sid}: unknown independence_class {entry.get('independence_class')!r}")
        if entry.get("data_access_method") not in ACCESS_METHODS:
            errors.append(f"{sid}: unknown data_access_method {entry.get('data_access_method')!r}")
        if entry.get("credentials_stored"):
            errors.append(f"{sid}: credentials must never be stored")
    return errors

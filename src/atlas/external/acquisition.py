"""Evidence acquisition: normalize, plan, validate, apply.

Every fact persisted here was read during a bounded, anonymous, GET-only search
and is recorded with its source URL, the observation date, the source revision
where the source exposes one, and the exact conditions under which it holds.

Rules this module enforces structurally:

- a publisher number is stored as ``evaluation_origin = publisher`` with
  ``verification_status = publisher_claim``. It is never relabelled independent,
  and two pages showing one run are one evaluation (Gate 21, 22).
- an identity that does not resolve exactly is stored as a *rejection*, never as
  a result (Gate 23).
- a runtime memory fact is stored as a documented observation with its scope. No
  constant is invented, and a value that exists for one backend/quantization/
  context scope is never generalised (Gate 30, 32, 35, 36).
- a measurement on hardware other than the target tier is stored as
  measured-requirement evidence and never as target-tier verification (Gate 29).
- nothing here writes a canonical record unless ``dry_run`` is false, and the
  write path is atomic and idempotent (Gate 37, 38, 60, 64).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from atlas.closure import CLOSURE_SCHEMA_VERSION, REFERENCE_DATE
from atlas.external.fetch import (
    QUALITY_SOURCE_CLASSES,
    classify_quality_source,
    source_registry_snapshot,
)
from atlas.intake.store import atomic_write_json

ACQUISITION_SCHEMA_VERSION = "0.1.0"
OBSERVED_AT = f"{REFERENCE_DATE}T00:00:00Z"

#: Bounded research budget actually consumed by external acquisition (Gate 57).
DECLARED_REQUEST_CEILING = 300
DECLARED_BYTE_CEILING = 8 * 1024 * 1024

#: Evidence that describes a runtime or a method rather than one release has no
#: single owning model record. Such a sidecar is intentionally unreferenced by a
#: model record's verification block, and the sidecar audit counts it as an
#: orphan. The count is declared here so the audit invariant can stay exact and
#: no unexplained orphan can appear.
RUNTIME_SCOPED_EVIDENCE_SOURCE_IDS: tuple[str, ...] = ("llamacpp-documentation",)


def runtime_scoped_evidence_ids(evidence: list[dict]) -> list[str]:
    """Ids of evidence deliberately owned by no model record."""
    return sorted(
        str(record["evidence_id"])
        for record in evidence
        if str(record.get("source_id")) in RUNTIME_SCOPED_EVIDENCE_SOURCE_IDS
    )


#: Which canonical model record owns each external evidence source.
EVIDENCE_OWNER_BY_SOURCE_ID: dict[str, str] = {
    "prism-ml-bonsai-card": "prism-ml-ternary-bonsai-2-27b-gguf",
    "os-software-heretic-card": "os-software-ternary-bonsai-2-27b-uncensored-heretic-gguf",
    "bonsai-demo-documentation": "prism-ml-ternary-bonsai-2-27b-gguf",
}


@dataclass(frozen=True)
class SourceObservation:
    """One public page actually read, with the class it can support."""

    source_id: str
    provider: str
    url: str
    source_class: str
    independence_class: str
    access_method: str
    reached: bool
    http_status: int
    outcome: str
    yields_independent_evidence: bool
    note: str


@dataclass(frozen=True)
class PublisherBenchmarkRow:
    """One numeric cell of a publisher's own benchmark table.

    ``variant_label`` is the publisher's exact label for the tested build; it is
    never rewritten into Atlas's own vocabulary.
    """

    benchmark_id: str
    benchmark_name: str
    variant_label: str
    score: float
    score_unit: str = "percent"


# ---------------------------------------------------------------------------
# 1. Publisher benchmark evidence (PrismML / Ternary-Bonsai-2-27B model card)
# ---------------------------------------------------------------------------

PRISM_CARD_URL = "https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf"
PRISM_CARD_RAW = "https://huggingface.co/prism-ml/Ternary-Bonsai-2-27B-gguf/raw/main/README.md"

PRISM_HARNESS = {
    "evaluation_suite": "EvalScope",
    "serving_stack": "vLLM",
    "hardware": "NVIDIA H100",
    "conditions": "identical infrastructure, decoding and scoring",
    "reasoning_mode": "thinking",
    "variants": {
        "Qwen3.8-27B FP16": {"true_bpw": 16.0, "footprint": "54 GB", "thinking_avg": 86.32},
        "Qwen3.8-27B UD-Q4_K_XL": {"true_bpw": 5.2, "footprint": "17.6 GB", "thinking_avg": 85.18},
        "Qwen3.8-27B IQ2_XXS": {"true_bpw": 2.16, "footprint": "7.27 GB", "thinking_avg": 72.59},
        "Bonsai 2 27B": {"true_bpw": 1.72, "footprint": "5.95 GB", "thinking_avg": 84.78},
    },
}

#: Per-benchmark table, verbatim from the publisher card. Thinking mode.
PRISM_FULL_RESULTS: tuple[tuple[str, str, float, float, float, float], ...] = (
    # benchmark_id, benchmark_name, FP16, UD-Q4_K_XL, IQ2_XXS, Bonsai 2 27B
    ("mmlu-redux", "MMLU-Redux", 91.46, 93.35, 88.93, 89.09),
    ("musr", "MuSR", 79.63, 73.01, 66.99, 70.63),
    ("gsm8k", "GSM8K", 97.19, 96.66, 89.90, 96.66),
    ("math-500", "MATH-500", 99.80, 99.40, 84.60, 98.80),
    ("aime25", "AIME25", 96.67, 92.91, 66.67, 95.00),
    ("aime26", "AIME26", 94.58, 93.00, 57.50, 95.83),
    ("humaneval-plus", "HumanEval+", 93.29, 95.73, 91.46, 95.12),
    ("mbpp-plus", "MBPP+", 83.86, 83.86, 78.89, 83.07),
    ("livecodebench", "LiveCodeBench", 90.05, 87.96, 56.40, 90.07),
    ("ifeval", "IFEval", 91.50, 88.83, 84.03, 91.31),
    ("ifbench-prompt-loose", "IFBench (prompt-loose)", 71.00, 65.65, 53.76, 74.00),
    ("bfcl-v3", "BFCL v3", 76.74, 75.05, 70.28, 74.92),
    ("mmmu-pro", "MMMU-Pro", 81.73, 81.73, 65.19, 75.49),
    ("ocr-bench-v2", "OCR Bench v2", 60.99, 65.45, 61.70, 56.88),
)

PRISM_VARIANT_COLUMN = {
    "Qwen3.8-27B FP16": "fp16",
    "Qwen3.8-27B UD-Q4_K_XL": "UD-Q4_K_XL",
    "Qwen3.8-27B IQ2_XXS": "IQ2_XXS",
    "Bonsai 2 27B": "ternary_g128_PTQ1_0",
}

#: Comparable-setting string shared by *both* sides of the retention comparison.
#: Comparability requires every setting that can move a score to be identical, so
#: this must not carry artifact-specific wording.
COMPARABLE_CONTEXT_CONFIGURATION = (
    "prism-ml-card-14b-thinking-mode; EvalScope+vLLM; NVIDIA H100; identical infrastructure, "
    "decoding and scoring; card min_p=0.0"
)

#: Publisher's declared packing identity, verbatim (exact artifact matching).
PRISM_PACKINGS: tuple[dict, ...] = (
    {
        "publisher_label": "PTQ1_0",
        "description": "dense trits",
        "true_bits_per_weight": 1.75,
        "publisher_stated_size": "5.95 GB",
        "declared_filestem": "Ternary-Bonsai-2-27B-PTQ1_0.gguf",
    },
    {
        "publisher_label": "PQ2_0",
        "description": "each trit in a 2-bit slot",
        "true_bits_per_weight": 2.13,
        "publisher_stated_size": "7.21 GB",
        "declared_filestem": "Ternary-Bonsai-2-27B-PQ2_0.gguf",
    },
)

#: Publisher's own runtime-compatibility statement for these artifacts.
PRISM_RUNTIME_STATEMENT = (
    "Stock llama.cpp will not run these files. It rejects PQ2_0 and PTQ1_0 as unknown types, "
    "and it loads Q2_0 without any warning and produces garbage, because it has no Hadamard "
    "activation runtime. A binary from the PrismML-Eng/llama.cpp fork is required."
)

# ---------------------------------------------------------------------------
# 2. Publisher local-validation evidence (OS-Software heretic variant card)
# ---------------------------------------------------------------------------

OS_CARD_URL = "https://huggingface.co/OS-Software/Ternary-Bonsai-2-27B-Uncensored-Heretic-GGUF"
OS_CARD_RAW = f"{OS_CARD_URL}/raw/main/README.md"

OS_LOCAL_VALIDATION = {
    "harness": (
        "publisher local validation; perplexity measured with a 512-token context over 4,080 "
        "English and 3,570 Japanese scored tokens; functional checks covered arithmetic, JSON, "
        "translation and reading comprehension"
    ),
    "wikitext2_perplexity": {"PQ2_0": 10.1460, "PTQ1_0": 10.1435},
    "harmless_alpaca_ja_perplexity": {"PQ2_0": 16.7833, "PTQ1_0": 16.7744},
    "functional_checks_passed": {"PQ2_0": "16/16", "PTQ1_0": "16/16"},
    "kl_divergence_vs_original": 0.0135,
    "refusals": {"variant": "0/100", "original": "95/100"},
    "self_disclosure": "These are small local tests, not a comprehensive benchmark.",
}

# ---------------------------------------------------------------------------
# 3. Documented runtime memory behaviour (Bonsai-demo / KV-CACHE.md)
# ---------------------------------------------------------------------------

BONSAI_DEMO_URL = "https://github.com/PrismML-Eng/Bonsai-demo"
KV_CACHE_URL = "https://raw.githubusercontent.com/PrismML-Eng/Bonsai-demo/main/KV-CACHE.md"

KV_DOCUMENTED = {
    "kv_fp16_bytes_per_token": 64 * 1024,
    "kv_q4_0_bytes_per_token": 18 * 1024,
    "kv_reduction_factor_claim": "roughly 3.5x",
    "context_tokens_in_example": 100_000,
    "kv_fp16_bytes_at_example_context": int(6.3 * 1024**3),
    "kv_q4_0_bytes_at_example_context": int(1.8 * 1024**3),
    "runtime": "llama.cpp (PrismML-Eng fork)",
    "backend": "CUDA",
    "kv_dtype_baseline": "fp16",
    "kv_dtype_alternative": "q4_0",
    "flash_attention_required_for_quantized_kv": True,
    "architecture_note": (
        "The 27B is a hybrid-attention backbone (~75% linear / ~25% full attention); the publisher "
        "states the hybrid attention already keeps the cache small. A per-token KV rate is "
        "therefore not the standard full-attention KV equation and is not interchangeable with it."
    ),
    "source_statement": (
        "BONSAI_KV4=1 stores the KV cache in Q4_0 (4-bit) instead of FP16, cutting KV memory "
        "roughly 3.5x: from 64 KiB per token to about 18 KiB per token on the 27B, so a "
        "100K-token context needs about 1.8 GiB instead of 6.3 GiB."
    ),
}

# ---------------------------------------------------------------------------
# 4. Runtime overhead: documented negative result (llama.cpp own documentation)
# ---------------------------------------------------------------------------

LLAMACPP_BUILD_DOC = "https://raw.githubusercontent.com/ggml-org/llama.cpp/master/docs/build.md"
LLAMACPP_REPO = "https://github.com/ggml-org/llama.cpp"

LLAMACPP_OVERHEAD_FINDING = {
    "question": (
        "Does llama.cpp publish a static and dynamic GPU-memory overhead figure that Atlas could "
        "use as a documented upper bound for a weight+KV estimate?"
    ),
    "answer": "no_published_bound",
    "evidence": (
        "llama.cpp's own build documentation shows the backend reporting its device allocations at "
        "runtime, for one specific backend and model: 'llm_load_tensors: CANN model buffer size = "
        "13313.00 MiB' and 'llama_new_context_with_model: CANN compute buffer size = 1260.81 MiB'. "
        "The compute buffer is therefore a backend-specific, model-specific, runtime-reported"
        "value. "
        "The documentation states no bound, no maximum and no constant for it, and the backend "
        "directory documentation contains no CUDA memory-budget page."
    ),
    "consequence": (
        "A universal llama.cpp overhead constant would be a fabrication. Atlas keeps "
        "known_static_overhead_bytes and known_dynamic_overhead_bytes absent, so the estimate"
        "upper "
        "bound stays absent and the tier verdict stays insufficient_evidence rather than a"
        "guessed fit."
    ),
    "scope_limits": [
        "The quoted figure is the CANN backend, not CUDA; it is recorded as evidence that the "
        "quantity exists and is runtime-reported, never as a CUDA overhead value.",
        "No GPU was used by Atlas and no CUDA context was created at any point.",
    ],
}

# ---------------------------------------------------------------------------
# 5. Sources actually consulted
# ---------------------------------------------------------------------------

SOURCES_CONSULTED: tuple[SourceObservation, ...] = (
    SourceObservation(
        source_id="aider-polyglot",
        provider="Aider",
        url="https://aider.chat/docs/leaderboards/",
        source_class="Q3",
        independence_class="original_independent_evaluation",
        access_method="public_html_and_published_yml",
        reached=True,
        http_status=200,
        outcome=(
            "Retrieved the published polyglot results data file. It now contains only "
            "frontier API-served models; no local, quantized or open-weight GGUF variant of any "
            "Core candidate is present."
        ),
        yields_independent_evidence=False,
        note="Exhausted: 69 entries, 0 exact-artifact matches for the Core set.",
    ),
    SourceObservation(
        source_id="livebench",
        provider="LiveBench",
        url="https://livebench.ai/",
        source_class="Q1",
        independence_class="original_independent_evaluation",
        access_method="public_site",
        reached=True,
        http_status=200,
        outcome=(
            "The public site is a client-rendered single-page application returning 1,066 bytes of "
            "shell HTML; no results are present in the served document. Results are published only "
            "as Hugging Face datasets, which this project must not download."
        ),
        yields_independent_evidence=False,
        note=(
            "Unavailable within bounded search. No private endpoint was probed and no protection "
            "was circumvented."
        ),
    ),
    SourceObservation(
        source_id="artificial-analysis",
        provider="Artificial Analysis",
        url="https://artificialanalysis.ai/leaderboards/models",
        source_class="Q1",
        independence_class="original_independent_evaluation",
        access_method="public_site",
        reached=True,
        http_status=200,
        outcome=(
            "Returns a Next.js application shell truncated at the byte cap with no server-rendered "
            "model results. A model sub-page path probed once returned HTTP 404. Results are"
            "loaded "
            "client-side from an endpoint Atlas does not use."
        ),
        yields_independent_evidence=False,
        note=(
            "Confirms the quality-source registry note. The internal data endpoint is not "
            "a documented public surface and was deliberately not used."
        ),
    ),
    SourceObservation(
        source_id="opencompass-rank",
        provider="OpenCompass / VLMEvalKit",
        url="https://rank.opencompass.org.cn/leaderboard-llm-v2",
        source_class="Q1",
        independence_class="original_independent_evaluation",
        access_method="public_site",
        reached=True,
        http_status=200,
        outcome=(
            "Reached the canonical host after the site issued a documented redirect from "
            "opencompass.org.cn, which Atlas refuses to follow. The response is a 4,748-byte "
            "single-page-application shell with no server-rendered rows."
        ),
        yields_independent_evidence=False,
        note="No documented public results endpoint. Redirect handling recorded, not bypassed.",
    ),
    SourceObservation(
        source_id="prism-ml-bonsai-card",
        provider="Prism ML",
        url=PRISM_CARD_RAW,
        source_class="Q4",
        independence_class="publisher_run",
        access_method="manual_transcription_from_public_page",
        reached=True,
        http_status=200,
        outcome=(
            "Publisher model card with a full 14-benchmark thinking-mode table under one declared "
            "harness (EvalScope + vLLM on NVIDIA H100) spanning the FP16 base and three quantized "
            "or low-bit variants, plus declared packing identity and memory figures."
        ),
        yields_independent_evidence=False,
        note=(
            "Highest-value source found. Publisher evidence only: it cannot satisfy the "
            "independent-multi-source quality gate, but it does produce comparable base-vs-quant "
            "retention under one harness."
        ),
    ),
    SourceObservation(
        source_id="os-software-heretic-card",
        provider="OS-Software",
        url=OS_CARD_RAW,
        source_class="Q4",
        independence_class="publisher_run",
        access_method="manual_transcription_from_public_page",
        reached=True,
        http_status=200,
        outcome=(
            "Publisher card with a local-validation table (WikiText-2 and harmless_alpaca_ja "
            "perplexity per packing, 16/16 functional checks) and a KL divergence against the "
            "original release."
        ),
        yields_independent_evidence=False,
        note=(
            "Publisher evidence for an alignment-modified variant; parent quality stays "
            "reference only."
        ),
    ),
    SourceObservation(
        source_id="bartowski-qwen2-5-7b-instruct-card",
        provider="Bartowski",
        url="https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/raw/main/README.md",
        source_class="Q4",
        independence_class="publisher_run",
        access_method="manual_transcription_from_public_page",
        reached=True,
        http_status=200,
        outcome=(
            "The card lists every packing with a prose quality adjective and a size, and states"
            "the "
            "imatrix calibration dataset. It publishes no numeric metric, no benchmark identity"
            "and "
            "no harness."
        ),
        yields_independent_evidence=False,
        note=(
            "Rejected as retention evidence: prose quality labels are not a benchmark result "
            "(Gate 32)."
        ),
    ),
    SourceObservation(
        source_id="quantfactory-qwen3-8b-card",
        provider="QuantFactory",
        url="https://huggingface.co/QuantFactory/Qwen3-8B-GGUF/raw/main/README.md",
        source_class="Q4",
        independence_class="publisher_run",
        access_method="manual_transcription_from_public_page",
        reached=True,
        http_status=200,
        outcome="No quantization quality table and no per-packing benchmark of any kind.",
        yields_independent_evidence=False,
        note="Nothing to ingest; recorded so the absence is not mistaken for an unfinished search.",
    ),
    SourceObservation(
        source_id="unsloth-qwen3-coder-30b-card",
        provider="Unsloth",
        url="https://huggingface.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/raw/main/README.md",
        source_class="Q4",
        independence_class="publisher_run",
        access_method="manual_transcription_from_public_page",
        reached=True,
        http_status=200,
        outcome=(
            "Defers benchmark evaluation and hardware requirements to the Qwen blog and GitHub "
            "repository rather than publishing them on the card."
        ),
        yields_independent_evidence=False,
        note="No exact-artifact result reachable within the per-candidate budget.",
    ),
    SourceObservation(
        source_id="llamacpp-documentation",
        provider="llama.cpp / ggml-org",
        url=LLAMACPP_BUILD_DOC,
        source_class="V2",
        independence_class="official_runtime_vendor",
        access_method="manual_transcription_from_public_page",
        reached=True,
        http_status=200,
        outcome=(
            "Official build documentation with a backend-specific, model-specific runtime-reported "
            "device buffer report (CANN). The backend documentation directory contains no CUDA "
            "memory-budget page and no documented overhead bound."
        ),
        yields_independent_evidence=False,
        note=(
            "Decisive for the runtime-overhead gate: the quantity exists but no bound is"
            "published, "
            "so no constant may be assumed."
        ),
    ),
    SourceObservation(
        source_id="bonsai-demo-documentation",
        provider="Prism ML (Bonsai-demo)",
        url=KV_CACHE_URL,
        source_class="V3",
        independence_class="publisher_run",
        access_method="manual_transcription_from_public_page",
        reached=True,
        http_status=200,
        outcome=(
            "Documents KV-cache memory per token for FP16 and Q4_0 on the 27B hybrid-attention "
            "backbone, the llama.cpp flags that produce them, and the optional CPU residency of "
            "the vision projector."
        ),
        yields_independent_evidence=False,
        note=(
            "Real external memory evidence with an explicit scope. It is not a baseline-context "
            "fit measurement and is stored with that limitation attached."
        ),
    ),
    SourceObservation(
        source_id="prism-ml-bonsai-whitepaper",
        provider="Prism ML (Bonsai-demo)",
        url="https://raw.githubusercontent.com/PrismML-Eng/Bonsai-demo/main/bonsai-2-27b-whitepaper.pdf",
        source_class="Q4",
        independence_class="publisher_run",
        access_method="public_pdf_binary_unparsed",
        reached=True,
        http_status=200,
        outcome=(
            "Retrieved (366,237 bytes) but not parsed: no PDF text-extraction library is available "
            "to this environment, and installing one is outside a bounded evidence run."
        ),
        yields_independent_evidence=False,
        note=(
            "Not ingested. The model card already carries the same benchmark table in legible"
            "form, "
            "so no claim depends on the PDF."
        ),
    ),
)


@dataclass
class AcquisitionPayload:
    """Everything acquisition intends to persist, before anything is written."""

    evidence: list[dict] = field(default_factory=list)
    evidence_conditions: dict = field(default_factory=dict)
    evaluations: list[dict] = field(default_factory=list)
    skipped_evaluations: list[dict] = field(default_factory=list)
    retentions: list[dict] = field(default_factory=list)
    measurements: list[dict] = field(default_factory=list)
    runtime_finding: dict = field(default_factory=dict)
    identity_findings: list[dict] = field(default_factory=list)
    sources: dict = field(default_factory=dict)
    bonsai_discovery: dict = field(default_factory=dict)
    budget: dict = field(default_factory=dict)

    def to_payload(self) -> dict:
        return {
            "schema_version": ACQUISITION_SCHEMA_VERSION,
            "observed_at": OBSERVED_AT,
            "evidence_count": len(self.evidence),
            "evidence": self.evidence,
            "evidence_conditions": self.evidence_conditions,
            "evaluations": self.evaluations,
            "skipped_evaluations": self.skipped_evaluations,
            "retentions": self.retentions,
            "measurements": self.measurements,
            "runtime_overhead_finding": self.runtime_finding,
            "identity_findings": self.identity_findings,
            "sources": self.sources,
            "bonsai_existing_server": self.bonsai_discovery,
            "budget": self.budget,
        }


def _evidence_id(
    *, source_id: str, claim_type: str, field_path: str, artifact_id: str | None
) -> str:
    from atlas.evidence_ids import generate_evidence_id_v2

    return generate_evidence_id_v2(
        source_id=source_id,
        repo_id=source_id,
        resolved_revision=REFERENCE_DATE,
        claim_type=claim_type,
        field_path=field_path,
        artifact_id=artifact_id,
    )


def _evidence_record(
    *,
    evidence_id: str,
    claim_type: str,
    field_path: str,
    source_id: str,
    source_type: str,
    source_url: str,
    publisher: str,
    notes: str,
    evidence_level: str,
    source_revision: str | None = None,
    verification_status: str = "independently_verified",
) -> dict:
    """Build one persisted sidecar that conforms to ``evidence.schema.json``.

    The contract is closed (``additionalProperties: false``), so the source
    revision, the methodology version and the machine-readable conditions are
    carried inside ``notes`` rather than as new fields. The same structured data
    is persisted verbatim alongside this sidecar under
    ``catalog/closure/external/`` so nothing is lost to the schema.
    """
    provenance = [
        f"methodology_version={ACQUISITION_SCHEMA_VERSION}",
        f"source_revision={source_revision or 'unresolved'}",
        "identity_status=exact_repository_identity_with_disclosed_artifact_label",
    ]
    body = "; ".join(part for part in (notes.strip(), " | ".join(provenance)) if part)
    return {
        "schema_version": "0.1.0",
        "evidence_id": evidence_id,
        "claim_type": claim_type,
        "field_path": field_path,
        "source_id": source_id,
        "source_type": source_type,
        "source_url": source_url,
        "retrieved_at": OBSERVED_AT,
        "publisher": publisher,
        "evidence_level": evidence_level,
        "verification_status": verification_status,
        "notes": body[:2000],
    }


def prism_quality_class() -> str:
    """Q-class of the PrismML benchmark table: publisher, never independent."""
    return classify_quality_source(
        provider="Prism ML",
        evaluator="Prism ML (EvalScope + vLLM, NVIDIA H100)",
        independence_class="publisher_run",
        evaluator_is_publisher=True,
    )


def build_payload(*, repo_root: Path, core_set: dict, bonsai_discovery: dict, budget: dict) -> dict:
    """Assemble the acquisition payload from verified observations.

    Nothing is written here. The caller validates, then applies.
    """
    from atlas.quality.ingest import normalize_evaluation
    from atlas.quality.retention import build_retention
    from atlas.quality.sidecars import load_records

    records = load_records(repo_root)
    by_model = {str(c["candidate_id"]): c for c in core_set.get("candidates", [])}
    payload = AcquisitionPayload()

    # -- evidence sidecars -------------------------------------------------
    arch_evidence_id = _evidence_id(
        source_id="prism-ml-bonsai-card",
        claim_type="architecture_property",
        field_path="architecture.packaging_identity",
        artifact_id=by_model["core-8g-05-ternary-bonsai-tq1"]["artifact_set_id"],
    )
    payload.evidence.append(
        _evidence_record(
            evidence_id=arch_evidence_id,
            claim_type="quantization_property",
            field_path="quantization.packaging_identity",
            source_id="prism-ml-bonsai-card",
            source_type="official_repo",
            source_url=PRISM_CARD_URL,
            publisher="prism-ml",
            evidence_level="publisher_claim",
            verification_status="publisher_claim",
            source_revision="b072e1d3b35a0a630cece372c2127528e0994386",
            notes=(
                "Publisher-declared packing identity. Exactly two packings exist: PTQ1_0 (dense "
                "trits, 1.75 bits/weight, 5.95 GB, file stem Ternary-Bonsai-2-27B-PTQ1_0.gguf) and "
                "PQ2_0 (each trit in a 2-bit slot, 2.13 bits/weight, 7.21 GB, file stem "
                "Ternary-Bonsai-2-27B-PQ2_0.gguf). Ternary g128 with a blockwise Hadamard rotation "
                "folded into the stored weights; 1.72 bits/weight for the language model as a "
                "whole; derived from Qwen3.8-27B, 64 blocks, ~75% linear / ~25% full attention; "
                "262K context inherited from the base model. DISCREPANCY: the catalog labels this "
                "artifact variant 'TQ1_0', a label the publisher does not use, while the catalog's "
                "own artifact_weight_bytes 5946648928 matches the stated PTQ1_0 packing. "
                "RUNTIME: stock llama.cpp rejects PQ2_0 and PTQ1_0 as unknown types and loads Q2_0 "
                "without warning while producing garbage, because it has no Hadamard activation "
                "runtime; the PrismML-Eng/llama.cpp fork is required."
            ),
        )
    )

    bench_evidence_id = _evidence_id(
        source_id="prism-ml-bonsai-card",
        claim_type="quality_benchmark_table",
        field_path="quality.benchmark_table",
        artifact_id=None,
    )
    payload.evidence.append(
        _evidence_record(
            evidence_id=bench_evidence_id,
            claim_type="benchmark_score",
            field_path="quality.benchmark_table",
            source_id="prism-ml-bonsai-card",
            source_type="official_repo",
            source_url=PRISM_CARD_URL,
            publisher="prism-ml",
            evidence_level="publisher_claim",
            verification_status="publisher_claim",
            source_revision="b072e1d3b35a0a630cece372c2127528e0994386",
            notes=(
                "Publisher-reported 14-benchmark thinking-mode table under one declared harness: "
                "EvalScope + vLLM on NVIDIA H100, identical infrastructure, decoding and scoring. "
                "14-benchmark thinking averages: Qwen3.8-27B FP16 (16.0 bpw, 54 GB) 86.32; "
                "UD-Q4_K_XL (5.2 bpw, 17.6 GB) 85.18; IQ2_XXS (2.16 bpw, 7.27 GB) 72.59; "
                "Bonsai 2 27B ternary g128 (1.72 bpw, 5.95 GB) 84.78. Per-benchmark rows "
                "(FP16 / UD-Q4_K_XL / IQ2_XXS / Bonsai 2 27B): MMLU-Redux 91.46/93.35/88.93/89.09; "
                "MuSR 79.63/73.01/66.99/70.63; GSM8K 97.19/96.66/89.90/96.66; "
                "MATH-500 99.80/99.40/84.60/98.80; AIME25 96.67/92.91/66.67/95.00; "
                "AIME26 94.58/93.00/57.50/95.83; HumanEval+ 93.29/95.73/91.46/95.12; "
                "MBPP+ 83.86/83.86/78.89/83.07; LiveCodeBench 90.05/87.96/56.40/90.07; "
                "IFEval 91.50/88.83/84.03/91.31; IFBench prompt-loose 71.00/65.65/53.76/74.00; "
                "BFCL v3 76.74/75.05/70.28/74.92; MMMU-Pro 81.73/81.73/65.19/75.49; "
                "OCR Bench v2 60.99/65.45/61.70/56.88. Publisher claim, therefore Q4: it can never "
                "satisfy an independent-multi-source quality gate and is not relabelled"
                "independent "
                "anywhere in Atlas. It does provide one harness under which the base and low-bit "
                "sides are directly comparable, which is what a retention computation requires,"
                "and "
                "it is the extreme-compression investigation: a genuine sub-2-bit build "
                "scored under the same suite as the FP16 reference."
            ),
        )
    )

    os_evidence_id = _evidence_id(
        source_id="os-software-heretic-card",
        claim_type="quality_benchmark_table",
        field_path="quality.local_validation",
        artifact_id=by_model["core-8g-07-ternary-heretic-tq1"]["artifact_set_id"],
    )
    payload.evidence.append(
        _evidence_record(
            evidence_id=os_evidence_id,
            claim_type="benchmark_score",
            field_path="quality.local_validation",
            source_id="os-software-heretic-card",
            source_type="official_repo",
            source_url=OS_CARD_URL,
            publisher="OS-Software",
            evidence_level="publisher_claim",
            verification_status="publisher_claim",
            source_revision="5ab50fd49410941a8d4f97912303b1c7d458ffa2",
            notes=(
                "Publisher local-validation table for the heretic variant. Perplexity measured"
                "with "
                "a 512-token context over 4,080 English and 3,570 Japanese scored tokens; "
                "functional checks covered arithmetic, JSON, translation and reading"
                "comprehension. "
                "WikiText-2 test perplexity: PQ2_0 10.1460, PTQ1_0 10.1435. harmless_alpaca_ja"
                "test "
                "perplexity: PQ2_0 16.7833, PTQ1_0 16.7744. Functional checks passed 16/16 for"
                "both "
                "packings. KL divergence against the original release 0.0135; refusals 0/100 "
                "versus 95/100 for the original. The publisher states these are small local tests, "
                "not a comprehensive benchmark, and that long-context and vision behaviour were"
                "not "
                "evaluated. The alignment modification baked a rank-128 Heretic LoRA into 34 "
                "matrices of the PQ2_0 model, an approximate ternary-code merge rather than a "
                "floating-point LoRA merge."
            ),
        )
    )

    kv_evidence_id = _evidence_id(
        source_id="bonsai-demo-documentation",
        claim_type="runtime_memory_profile",
        field_path="runtime.kv_cache_bytes_per_token",
        artifact_id=by_model["core-8g-05-ternary-bonsai-tq1"]["artifact_set_id"],
    )
    payload.evidence.append(
        _evidence_record(
            evidence_id=kv_evidence_id,
            claim_type="vram_requirement",
            field_path="vram.kv_cache_bytes_per_token",
            source_id="bonsai-demo-documentation",
            source_type="official_docs",
            source_url=BONSAI_DEMO_URL,
            publisher="Prism ML",
            evidence_level="publisher_claim",
            verification_status="publisher_claim",
            notes=(
                "Documented KV-cache memory for the 27B hybrid-attention backbone on the PrismML "
                "llama.cpp fork: 64 KiB per token in FP16 and about 18 KiB per token in Q4_0, so a "
                "100K-token context needs about 6.3 GiB instead of about 1.8 GiB, a documented "
                "roughly 3.5x reduction. Q4_0 requires flash attention, which the documented"
                "scripts "
                "already enable, and is passed as --cache-type-k q4_0 --cache-type-v q4_0. SCOPE "
                "LIMITS: the 100K example context is not the Atlas 8192-token text baseline; the "
                "figures are KV-cache allocations, not a full-device peak; no GPU model, driver, "
                "batch state or offload state is published for them; and because the backbone is "
                "~75% linear attention this per-token rate is NOT the standard full-attention KV "
                "equation and is never substituted for it. The publisher separately documents an "
                "optional system-RAM residency for the vision projector (--no-mmproj-offload) to "
                "free VRAM on tight cards."
            ),
        )
    )

    overhead_evidence_id = _evidence_id(
        source_id="llamacpp-documentation",
        claim_type="runtime_support",
        field_path="runtime.compute_buffer_bound",
        artifact_id=None,
    )
    payload.evidence.append(
        _evidence_record(
            evidence_id=overhead_evidence_id,
            claim_type="runtime_support",
            field_path="runtime.compute_buffer_bound",
            source_id="llamacpp-documentation",
            source_type="official_docs",
            source_url=LLAMACPP_REPO,
            publisher="ggml-org",
            evidence_level="publisher_claim",
            verification_status="independently_verified",
            notes=(
                "Question: does llama.cpp publish a static and dynamic GPU-memory overhead figure "
                "Atlas could use as a documented upper bound for a weight+KV estimate? ANSWER: no "
                "published bound. llama.cpp's own build documentation shows the backend reporting "
                "its device allocations at runtime for one specific backend and model: "
                "'llm_load_tensors: CANN model buffer size = 13313.00 MiB' and "
                "'llama_new_context_with_model: CANN compute buffer size = 1260.81 MiB'. The "
                "compute buffer is therefore a backend-specific, model-specific, runtime-reported "
                "value, and the documentation states no bound, maximum or constant for it; the "
                "backend documentation directory contains no CUDA memory-budget page. The quoted "
                "figure is the CANN backend, not CUDA, and is recorded only as evidence that the "
                "quantity exists and is runtime-reported, never as a CUDA overhead value. "
                "CONSEQUENCE: a universal llama.cpp overhead constant would be a fabrication, so "
                "Atlas keeps known_static_overhead_bytes and known_dynamic_overhead_bytes absent "
                "and the estimate upper bound stays absent. No GPU was used and no CUDA context"
                "was "
                "created."
            ),
        )
    )

    payload.evidence_conditions = {
        "prism_packings": [dict(p) for p in PRISM_PACKINGS],
        "prism_runtime_statement": PRISM_RUNTIME_STATEMENT,
        "prism_quality_source_class": prism_quality_class(),
        "prism_harness": dict(PRISM_HARNESS),
        "prism_variant_columns": dict(PRISM_VARIANT_COLUMN),
        "prism_per_benchmark": [
            {
                "benchmark_id": row[0],
                "benchmark_name": row[1],
                "fp16": row[2],
                "ud_q4_k_xl": row[3],
                "iq2_xxs": row[4],
                "bonsai_2_27b": row[5],
            }
            for row in PRISM_FULL_RESULTS
        ],
        "os_local_validation": dict(OS_LOCAL_VALIDATION),
        "kv_documented": dict(KV_DOCUMENTED),
        "llamacpp_overhead_finding": dict(LLAMACPP_OVERHEAD_FINDING),
    }

    # -- publisher evaluation results -------------------------------------
    prism_record = records.get("prism-ml-ternary-bonsai-2-27b-gguf")
    qwen_base_record = records.get("qwen-qwen3-8-27b")
    bonsai_avg = PRISM_HARNESS["variants"]["Bonsai 2 27B"]["thinking_avg"]
    fp16_avg = PRISM_HARNESS["variants"]["Qwen3.8-27B FP16"]["thinking_avg"]

    def _aggregate(record: dict | None, model_id: str, score: float, notes: str) -> dict | None:
        if record is None:
            payload.skipped_evaluations.append(
                {
                    "model_id": model_id,
                    "reason": "catalog_record_absent",
                    "note": "no canonical catalog record; nothing is attached",
                }
            )
            return None
        result = normalize_evaluation(
            record=record,
            evaluated_repo_id=record["display_name"],
            evaluated_revision=(record.get("quantization") or {}).get("source_revision"),
            benchmark_name="Prism ML 14-benchmark thinking-mode suite",
            benchmark_id="prism-ml-14b-thinking-average",
            benchmark_version="card-as-observed-2026-10-05",
            suite_version="EvalScope+vLLM-h100",
            task="multi_domain_reasoning_coding_instruction_agentic_vision",
            metric="thinking_mode_average_14_benchmarks",
            metric_direction="higher_is_better",
            score=score,
            score_unit="percent",
            evaluation_origin="publisher",
            verification_status="publisher_claim",
            source_id="prism-ml-bonsai-card",
            source_url=PRISM_CARD_URL,
            evaluator="Prism ML (EvalScope + vLLM, NVIDIA H100)",
            evaluation_date=None,
            reasoning_mode="thinking",
            tool_mode="tool_calling_in_suite_bfcl_v3",
            prompting_mode="publisher_declared_identical_decoding",
            context_configuration=COMPARABLE_CONTEXT_CONFIGURATION,
            quantization=None,
            artifact_id=(
                by_model["core-8g-05-ternary-bonsai-tq1"]["artifact_set_id"]
                if model_id == "prism-ml-ternary-bonsai-2-27b-gguf"
                else None
            ),
            evidence_ids=[bench_evidence_id],
            source_observed_at=OBSERVED_AT,
            notes=notes,
        )
        if result is None:
            payload.skipped_evaluations.append(
                {"model_id": model_id, "reason": "identity_did_not_resolve_exactly"}
            )
        return result

    agg_bonsai = _aggregate(
        prism_record,
        "prism-ml-ternary-bonsai-2-27b-gguf",
        bonsai_avg,
        (
            "Publisher-reported aggregate. The card's 'Bonsai 2 27B' row is the 5.95 GB ternary "
            "g128 PTQ1_0 packing, which is the artifact of Core candidate core-8g-05; the 7.21 GB "
            "PQ2_0 packing is reported separately by the same publisher. Both sides of this "
            "comparison come from one publisher run, so it is Q4 publisher evidence."
        ),
    )
    agg_fp16 = _aggregate(
        qwen_base_record,
        "qwen-qwen3-8-27b",
        fp16_avg,
        (
            "FP16 reference row of the same publisher table, used only as the comparable base side "
            "of a retention computation. It is not attached as the quality of any quantized "
            "artifact."
        ),
    )
    for result in (agg_bonsai, agg_fp16):
        if result is not None:
            payload.evaluations.append(result)

    # -- retention ---------------------------------------------------------
    if agg_bonsai is not None and agg_fp16 is not None:
        retention = build_retention(
            base_release="qwen-qwen3-8-27b",
            quantized_artifact=by_model["core-8g-05-ternary-bonsai-tq1"]["artifact_set_id"],
            quantization="PTQ1_0",
            base_result=agg_fp16,
            quant_result=agg_bonsai,
            source="prism-ml-bonsai-card",
            evidence_ids=[bench_evidence_id, arch_evidence_id],
            publisher_claim={
                "publisher_retention_statement": "98.2% of FP16 intelligence retained",
                "publisher_metric": "14-benchmark thinking-mode average",
                "status": "publisher_claim",
            },
            notes=(
                "One publisher run, one harness (EvalScope + vLLM on NVIDIA H100, thinking mode), "
                "one benchmark identity, so base and quantized sides are comparable. The "
                "quantized side is a natively ternary-trained variant (1.72 bits/weight) rather "
                "than a post-training quantization of the FP16 checkpoint; that distinction is "
                "disclosed rather than smoothed over. Publisher evidence cannot satisfy the strict "
                "retention gate."
            ),
        )
        payload.retentions.append(retention)

    # -- external memory measurements (scoped, not fit verdicts) ------------
    payload.measurements.extend(_kv_measurements(by_model))
    payload.runtime_finding = dict(LLAMACPP_OVERHEAD_FINDING)
    payload.identity_findings = _identity_findings(by_model)
    payload.sources = source_registry_snapshot(
        sources=[
            {
                "source_id": s.source_id,
                "provider": s.provider,
                "url": s.url,
                "source_class": s.source_class,
                "independence_class": s.independence_class,
                "data_access_method": s.access_method,
                "reached": s.reached,
                "http_status": s.http_status,
                "outcome": s.outcome,
                "yields_independent_evidence": s.yields_independent_evidence,
                "terms_or_limitations": s.note,
                "credentials_stored": False,
                "observed_at": OBSERVED_AT,
            }
            for s in SOURCES_CONSULTED
        ],
        observed_at=OBSERVED_AT,
    )
    payload.sources["budget"] = dict(budget)
    payload.sources["declared_request_ceiling"] = DECLARED_REQUEST_CEILING
    payload.sources["declared_byte_ceiling"] = DECLARED_BYTE_CEILING
    payload.bonsai_discovery = {
        # Structural defaults: no caller may accidentally claim a diagnostic ran.
        "diagnostic_inference_requests": 0,
        "diagnostic_inference_required": False,
        "lifecycle_changed": False,
        **dict(bonsai_discovery),
    }
    payload.budget = dict(budget)
    return payload.to_payload()


def _kv_measurements(by_model: dict) -> list[dict]:
    """Documented KV-cache memory, stored with its exact scope attached.

    These are *not* fit verdicts. Context differs from the Atlas baseline and no
    full-device peak was published, so ``fit_support`` must refuse them.
    """
    artifact_id = by_model["core-8g-05-ternary-bonsai-tq1"]["artifact_set_id"]
    context = KV_DOCUMENTED["context_tokens_in_example"]
    common = {
        "model_id": "prism-ml-ternary-bonsai-2-27b-gguf",
        "revision": "b072e1d3b35a0a630cece372c2127528e0994386",
        "artifact_variant": artifact_id,
        "runtime": "llama.cpp",
        "runtime_version": "PrismML-Eng/llama.cpp fork, pinned binary; exact build not published",
        "backend": "CUDA",
        "gpu": "not stated for this figure",
        "gpu_vram": "not stated for this figure",
        "driver": "not stated for this figure",
        "os": "not stated for this figure",
        "system_ram": "not stated for this figure",
        "context_tokens": context,
        "batch_or_sequences": 1,
        "measurement_stage": "kv_allocated",
        "measurement_method": "documented",
        "evidence_level": "publisher_measurement",
        "source": KV_CACHE_URL,
        "observed_at": OBSERVED_AT,
    }
    fp16 = {
        **common,
        "measurement_id": "meas-v1-bonsai27b-kv-fp16-100k",
        "kv_format": "fp16",
        "offload_mode": "full",
        "reported_vram_bytes": KV_DOCUMENTED["kv_fp16_bytes_at_example_context"],
    }
    q4 = {
        **common,
        "measurement_id": "meas-v1-bonsai27b-kv-q4-100k",
        "kv_format": "q4_0",
        "offload_mode": "full",
        "reported_vram_bytes": KV_DOCUMENTED["kv_q4_0_bytes_at_example_context"],
    }
    return [fp16, q4]


def _identity_findings(by_model: dict) -> list[dict]:
    """Exact-artifact discrepancies found in the catalog by external evidence.

    These are recorded, not silently repaired: repairing them would rewrite
    artifact identity across the whole catalog, which is a wider change than
    evidence closure may make on its own.
    """
    return [
        {
            "finding_id": "identity-01-ternary-packing-label",
            "severity": "material_for_exact_artifact_matching",
            "candidate_id": "core-8g-05-ternary-bonsai-tq1",
            "catalog_artifact_variant": by_model["core-8g-05-ternary-bonsai-tq1"][
                "artifact_variant"
            ],
            "publisher_declared_labels": [p["publisher_label"] for p in PRISM_PACKINGS],
            "observed": (
                "The catalog records the artifact filename "
                f"{by_model['core-8g-05-ternary-bonsai-tq1']['artifact_filename']} (which matches "
                "the publisher's PTQ1_0 pack) but labels the variant 'TQ1_0', a label the"
                "publisher "
                "does not use. The publisher declares exactly two packings: PTQ1_0 and PQ2_0."
            ),
            "corroboration": (
                "artifact_weight_bytes 5946648928 is consistent with the publisher's stated 5.95"
                "GB "
                "PTQ1_0 packing and inconsistent with the 7.21 GB PQ2_0 packing."
            ),
            "action_taken": "recorded_only",
            "action_rationale": (
                "Renaming the variant would change artifact_set_id, which keys retention records, "
                "quality artifact matching and every closure view. That is a catalog-wide identity "
                "change requiring its own versioned decision, not an evidence-ingestion side"
                "effect."
            ),
        },
        {
            "finding_id": "identity-02-model-level-quant-label-vs-artifact",
            "severity": "material_for_exact_artifact_matching",
            "candidate_id": "core-8g-07-ternary-heretic-tq1",
            "catalog_artifact_variant": by_model["core-8g-07-ternary-heretic-tq1"][
                "artifact_variant"
            ],
            "observed": (
                "The model-level catalog record declares quant_name 'Q2' / quant_family 'q2',"
                "taken "
                "from one packing, while the Core candidate selects the other packing's artifact. "
                "Model-level quantization metadata cannot disambiguate two packings of one"
                "release, "
                "so an exact per-packing publisher result cannot be attached to this record."
            ),
            "action_taken": "rejected_attachment",
            "action_rationale": (
                "The publisher's per-packing perplexity values exist, but attaching them under a "
                "'Q2' label would assert a quantization the measurement did not use. The record is "
                "stored as evidence and the result is recorded as a rejected attachment."
            ),
        },
        {
            "finding_id": "identity-03-bonsai-quantization-scope",
            "severity": "methodological",
            "candidate_id": "core-8g-05-ternary-bonsai-tq1",
            "observed": (
                "The release is a natively ternary-trained model with Hadamard rotation folded"
                "into "
                "the stored weights, not a post-training quantization. The catalog treats any "
                "artifact_variant without a declared native quant method as post-training "
                "quantized, which routes this artifact into base-vs-quant retention logic."
            ),
            "action_taken": "recorded_only",
            "action_rationale": (
                "Native low-bit releases must use their native evaluation evidence rather than be "
                "forced through post-training retention semantics. The retention record created "
                "here discloses the distinction explicitly instead of being hidden."
            ),
        },
        {
            "finding_id": "identity-04-model-record-lacks-quantization-name",
            "severity": "material_for_exact_artifact_matching",
            "candidate_id": "core-8g-05-ternary-bonsai-tq1",
            "observed": (
                "The model-level catalog record for this release declares quant_family 'unknown'"
                "and "
                "quant_name null, because the publisher ships two packings of one release. "
                "Consequently the base-versus-quant identity guard treats the record as "
                "non-quantized, and a per-packing result can only be attached with an empty "
                "quantization field plus an artifact_id binding."
            ),
            "action_taken": "recorded_with_explicit_artifact_binding",
            "action_rationale": (
                "The publisher result was attached to the exact artifact via artifact_id, with the "
                "publisher's own packing label recorded in the retention record and in this file. "
                "The closure's own retention builder still reads only model-level quantization "
                "metadata, so its state for this artifact remains less specific than the measured "
                "comparison recorded here. That limitation is reported rather than hidden."
            ),
        },
    ]


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def write_acquisition(
    *,
    repo_root: Path,
    payload: dict,
    dry_run: bool = True,
) -> dict:
    """Persist external evidence atomically and idempotently.

    Only new files are written. No existing canonical record is rewritten, so a
    partial failure leaves the previous snapshot intact.
    """
    evidence_dir = repo_root / "catalog" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    existing = {p.stem for p in evidence_dir.glob("*.json") if p.is_file()}

    written_evidence: list[str] = []
    unchanged_evidence: list[str] = []
    for record in payload.get("evidence", []):
        evidence_id = str(record["evidence_id"])
        target = evidence_dir / f"{evidence_id}.json"
        if evidence_id in existing and target.is_file():
            unchanged_evidence.append(evidence_id)
            continue
        written_evidence.append(evidence_id)
        if not dry_run:
            atomic_write_json(target, record)

    from atlas.quality.ingest import persist_evaluations

    linkage = link_evidence_to_records(
        repo_root=repo_root, evidence=list(payload.get("evidence", [])), dry_run=dry_run
    )

    eval_written, eval_unchanged = persist_evaluations(
        repo_root, list(payload.get("evaluations", [])), dry_run=dry_run
    )

    measurements_dir = repo_root / "catalog" / "measurements"
    measurements_dir.mkdir(parents=True, exist_ok=True)
    existing_measurements = {p.stem for p in measurements_dir.glob("*.json") if p.is_file()}
    written_measurements: list[str] = []
    unchanged_measurements: list[str] = []
    for measurement in payload.get("measurements", []):
        measurement_id = str(measurement["measurement_id"])
        target = measurements_dir / f"{measurement_id}.json"
        if measurement_id in existing_measurements and target.is_file():
            unchanged_measurements.append(measurement_id)
            continue
        written_measurements.append(measurement_id)
        if not dry_run:
            atomic_write_json(target, measurement)

    closure_base = repo_root / "catalog" / "closure" / "external"
    targets = {
        "retention.json": payload.get("retentions", []),
        "measurements-index.json": {
            "schema_version": CLOSURE_SCHEMA_VERSION,
            "observed_at": OBSERVED_AT,
            "measurement_ids": sorted(m["measurement_id"] for m in payload.get("measurements", [])),
            "note": (
                "External memory facts stored with their scope. A scope that differs from the"
                "Atlas "
                "baseline context or that omits a full-device peak can never create a fit verdict."
            ),
        },
        "evidence-conditions.json": {
            "schema_version": CLOSURE_SCHEMA_VERSION,
            "observed_at": OBSERVED_AT,
            "note": (
                "Machine-readable conditions behind the evidence sidecars. evidence.schema.json is "
                "closed, so the structured detail lives here instead of inside a sidecar, and each "
                "sidecar's notes carry the same figures in prose."
            ),
            **payload.get("evidence_conditions", {}),
        },
        "runtime-overhead-finding.json": {
            "schema_version": CLOSURE_SCHEMA_VERSION,
            "observed_at": OBSERVED_AT,
            **payload.get("runtime_overhead_finding", {}),
        },
        "identity-findings.json": {
            "schema_version": CLOSURE_SCHEMA_VERSION,
            "observed_at": OBSERVED_AT,
            "findings": payload.get("identity_findings", []),
            "note": (
                "Exact-artifact discrepancies surfaced by external evidence. Recorded, not"
                "silently "
                "repaired."
            ),
        },
        "sources.json": payload.get("sources", {}),
        "bonsai-existing-server.json": {
            "schema_version": CLOSURE_SCHEMA_VERSION,
            "observed_at": OBSERVED_AT,
            **payload.get("bonsai_existing_server", {}),
        },
    }
    written_targets: list[str] = []
    for name, body in targets.items():
        target = closure_base / name
        written_targets.append(str(target))
        if not dry_run:
            atomic_write_json(target, body)

    return {
        "dry_run": dry_run,
        "evidence_written": written_evidence,
        "evidence_unchanged": unchanged_evidence,
        "record_linkage": linkage,
        "evaluations_written": eval_written,
        "evaluations_unchanged": eval_unchanged,
        "measurements_written": written_measurements,
        "measurements_unchanged": unchanged_measurements,
        "closure_files": written_targets,
        "skipped_evaluations": payload.get("skipped_evaluations", []),
    }


def journal_acquisition(*, repo_root: Path, payload: dict) -> int:
    """Append acquisition events to the existing change journal.

    No new history system is introduced: the quality event builder and
    the append-only journal file are reused, and events are deduplicated by id so
    re-running is idempotent.
    """
    from atlas.quality.changes import append_quality_events, quality_event

    events: list[dict] = []
    for record in payload.get("evidence", []):
        events.append(
            quality_event(
                event_type="quality_evidence_added",
                model_id="external-evidence",
                detected_at=OBSERVED_AT,
                subject_id=str(record["evidence_id"]),
                evidence_ids=[str(record["evidence_id"])],
                changed_fields=[str(record.get("field_path") or "evidence")],
                notes=(
                    f"External read-only acquisition from {record.get('source_id')}; "
                    f"origin={record.get('evidence_level')}"
                ),
            )
        )
    for result in payload.get("evaluations", []):
        events.append(
            quality_event(
                event_type="quality_evidence_added",
                model_id=str(result["model_id"]),
                detected_at=OBSERVED_AT,
                subject_id=str(result["evaluation_id"]),
                evidence_ids=list(result.get("evidence_ids") or []),
                changed_fields=["quality.evaluations"],
                notes=(
                    f"origin={result.get('evaluation_origin')}; "
                    f"benchmark={result.get('benchmark_id')}"
                ),
            )
        )
    for measurement in payload.get("measurements", []):
        events.append(
            quality_event(
                event_type="quality_evidence_added",
                model_id=str(measurement.get("model_id") or "external"),
                detected_at=OBSERVED_AT,
                subject_id=str(measurement["measurement_id"]),
                evidence_ids=[],
                changed_fields=["vram.external_measurements"],
                notes=(
                    "publisher measurement stored with its exact scope; a scope that differs from "
                    "the Atlas baseline cannot create a fit verdict"
                ),
            )
        )
    return append_quality_events(repo_root / "catalog" / "changes", events)


def link_evidence_to_records(
    *,
    repo_root: Path,
    evidence: list[dict],
    dry_run: bool = True,
) -> dict:
    """Reference every model-scoped evidence sidecar from its canonical record.

    Appending is additive and idempotent, so historical identifiers stay exactly
    where they were. Runtime-scoped evidence is deliberately left unreferenced:
    attaching a runtime-level claim to one release would be a false reference.
    """
    models_dir = repo_root / "catalog" / "models"
    linked: list[dict] = []
    already: list[dict] = []
    skipped: list[dict] = []
    for record in evidence:
        evidence_id = str(record["evidence_id"])
        owner = EVIDENCE_OWNER_BY_SOURCE_ID.get(str(record.get("source_id")))
        if owner is None:
            skipped.append({"evidence_id": evidence_id, "reason": "runtime_or_method_scoped"})
            continue
        path = models_dir / f"{owner}.json"
        if not path.is_file():
            skipped.append({"evidence_id": evidence_id, "reason": "owner_record_absent"})
            continue
        try:
            model_record = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            skipped.append({"evidence_id": evidence_id, "reason": "owner_record_unreadable"})
            continue
        verification = dict(model_record.get("verification") or {})
        existing = [str(e) for e in (verification.get("evidence_ids") or [])]
        if evidence_id in existing:
            already.append({"model_id": owner, "evidence_ids": [evidence_id]})
            continue
        verification["evidence_ids"] = existing + [evidence_id]
        linked.append(
            {
                "model_id": owner,
                "added_evidence_ids": [evidence_id],
                "total_references": len(verification["evidence_ids"]),
            }
        )
        if not dry_run:
            atomic_write_json(path, {**model_record, "verification": verification})
    return {
        "dry_run": dry_run,
        "records_linked": linked,
        "records_already_linked": already,
        "records_skipped": skipped,
        "historical_identifiers_preserved": True,
    }


def load_acquisition(repo_root: Path, name: str) -> dict | None:
    """Load one persisted external-evidence file, or None."""
    path = repo_root / "catalog" / "closure" / "external" / name
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None


__all__ = [
    "ACQUISITION_SCHEMA_VERSION",
    "DECLARED_BYTE_CEILING",
    "DECLARED_REQUEST_CEILING",
    "OBSERVED_AT",
    "QUALITY_SOURCE_CLASSES",
    "AcquisitionPayload",
    "SourceObservation",
    "build_payload",
    "journal_acquisition",
    "load_acquisition",
    "write_acquisition",
]

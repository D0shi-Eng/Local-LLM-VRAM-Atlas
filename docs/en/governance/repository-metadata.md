# Repository Metadata

> Arabic counterpart: [`docs/ar/governance/repository-metadata.md`](../../ar/governance/repository-metadata.md)

The intended repository metadata, recorded so it stays consistent across
changes. Every value here is written to be **calm, technical and verifiable**.
Nothing in this document may claim a capability the data does not support.

## Display title

```text
Local LLM VRAM Atlas
```

Already the repository name. No abbreviation, no emoji, no tagline appended to
the title. The title names the subject; the description carries the claim.

## Short description

GitHub renders approximately 100 characters before truncation on most surfaces,
so the description is written to survive truncation at the cost of the last
clause, not the first.

```text
Evidence-aware atlas for local LLMs across 4GB, 8GB, 12GB, and 16GB VRAM tiers, with canonical model records, quantization intelligence, architecture-aware memory analysis, quality evidence, and recommendation readiness.
```

219 characters. It survives truncation at the cost of "and recommendation
readiness", which is the least load-bearing clause because the README states it
prominently anyway.

**Shorter fallback**, if a shorter single field is preferred:

```text
Canonical, evidence-aware catalog and analysis for local LLMs across 4/8/12/16GB VRAM tiers, with memory modelling and recommendation readiness.
```

155 characters.

## Longer tagline

For use in the README, a profile, or a release header where more space exists.

```text
An evidence-aware atlas for local and open-weight LLMs: canonical records, quantization intelligence, architecture-aware memory analysis, quality evidence, and recommendation readiness across 4 / 8 / 12 / 16 GB VRAM tiers — reported honestly, including where the evidence is insufficient.
```

## Why this description and not a stronger one

Rejected alternatives, and the reason:

| Rejected | Reason |
|---|---|
| "Verified model recommendations for every VRAM tier" | False. Strict recommendations are 0 at every tier. |
| "Best local models for your GPU" | False and unmeasurable. Atlas does not rank. |
| "Complete database of local LLMs" | False. The catalog is a curated selection of 34 releases. |
| "Production-grade model compatibility" | Unearned. There is no production deployment and no certification. |
| "Benchmarked models" | Misleading. 21 evaluation results, none of them independent multi-source. |
| "100% accurate VRAM calculator" | False and precisely the opposite of the project's thesis. |

The description's strongest claim is that Atlas is **evidence-aware**. That is
true, checkable, and the project's actual contribution.

## Topics

Apply these twenty GitHub topics. Twenty is the current maximum.

```text
local-llm
llm
vram
gguf
quantization
model-catalog
memory-analysis
inference
llama-cpp
open-weight-models
benchmarking
recommendation-system
ai-infrastructure
model-intelligence
metadata
json-schema
catalog
documentation
bilingual
research
```

Coverage rationale:

| Topic | Why it earns its place |
|---|---|
| `local-llm`, `llm` | Direct subject. |
| `vram` | The organising axis of the whole project. |
| `gguf`, `quantization` | The dominant artifact format and the core analysis. |
| `model-catalog`, `catalog`, `metadata` | The deliverable is a curated dataset. |
| `memory-analysis` | Distinct from `vram`: the method is memory modelling. |
| `inference`, `llama-cpp` | The runtime context the memory model targets. |
| `open-weight-models` | The subject population. |
| `benchmarking`, `research` | Evidence discipline; accurate despite zero independent results. |
| `recommendation-system` | The declared output type. |
| `ai-infrastructure`, `model-intelligence` | Discoverability. |
| `json-schema` | 18 versioned schemas are a real contract surface. |
| `documentation`, `bilingual` | Bilingual EN/AR documentation is a genuine differentiator. |

Deliberately excluded: `cuda`, `nvidia`, `huggingface` (vendor topics imply an
endorsement the project disclaims), and `arabic` or `rtl` (narrowing the project
rather than describing it).

## Home page

Leave empty. No GitHub Pages site is published, and pointing the field at an
unpublished location is worse than leaving it unset.

## Repository visibility

```text
PRIVATE
```

Visibility is not a metadata preference; it is a release gate. See the status
note in the README.

## Social preview

The banner source is `assets/branding/banner.svg`. GitHub's social-preview
feature requires a raster image, so a 1280 × 640 PNG or JPG export is an owner
action, not a repository change. The export command is documented in
[`assets/branding/brand-guidelines.md`](../../../assets/branding/brand-guidelines.md).

## Maintaining this document

Update this file whenever the dataset scope changes materially — for example if
the model count moves substantially, or if strict recommendations become
non-zero. If the numbers here and the numbers in the README disagree, the README
is wrong and must be corrected from the catalog, not the other way round.

Verify the live figures with:

```bash
python -m atlas.cli.main catalog stats
python -m atlas.cli.main recommend tier --tier 8
python -m atlas.cli.main closure readiness
```
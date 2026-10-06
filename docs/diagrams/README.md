# Figure Index

> فهرس الأشكال — النسخة العربية في [`README_AR.md`](README_AR.md)
>
> Read in Arabic: [`README_AR.md`](README_AR.md)

Every figure in this repository is authored in English. That is a deliberate
decision: engineering diagrams carry a high density of identifiers, schema field
names and state names, and translating those inside the diagram itself degrades
readability for both audiences.

Arabic readers get a **bilingual caption and explanation for every figure** in
[`README_AR.md`](README_AR.md).

Each diagram is a native Mermaid block embedded in a Markdown document, so it
renders directly in the repository with no build step and no external tool.

---

## Engineering diagrams

| Figure | Document | What it explains |
|---|---|---|
| **Figure 1** — System architecture | [`docs/en/architecture/atlas-system-architecture.md`](../en/architecture/atlas-system-architecture.md) | The full metadata-only pipeline: external surfaces, intake, resolution, analysis, quality intelligence, evidence closure, incremental refresh, canonical catalog and generated views. |
| **Figure 2** — Canonical record derivation | [`docs/en/architecture/canonical-record-flow.md`](../en/architecture/canonical-record-flow.md) | How one published release becomes canonical model, artifact, source and evidence records, and which derived records depend on which primary records. |
| **Figure 3** — Discovery to canonical record | [`docs/en/workflows/refresh-and-evidence-ingestion.md`](../en/workflows/refresh-and-evidence-ingestion.md) | The guarded intake path: URL and weight guard, anonymous read, normalisation, identity classification, schema validation, provenance attachment and dry-run-by-default persistence. |
| **Figure 4** — From declared metadata to a memory range | [`docs/en/workflows/refresh-and-evidence-ingestion.md`](../en/workflows/refresh-and-evidence-ingestion.md) | Architecture resolution, weight and KV byte arithmetic, and why an absent runtime overhead bound keeps the upper bound absent instead of substituting a constant. |
| **Figure 5** — From a published result to a quality axis | [`docs/en/workflows/refresh-and-evidence-ingestion.md`](../en/workflows/refresh-and-evidence-ingestion.md) | Evaluation-result origin classification, exact-artifact identity matching, and how a result becomes a per-axis evidence state. |
| **Figure 6** — Two evidence paths that must not be confused | [`docs/en/workflows/refresh-and-evidence-ingestion.md`](../en/workflows/refresh-and-evidence-ingestion.md) | Quantization retention ("is it still as good?") kept separate from VRAM fit evidence ("does it run here?"), with scope limits attached to both. |
| **Figure 7** — Recommendation decision flow | [`docs/en/workflows/recommendation-readiness.md`](../en/workflows/recommendation-readiness.md) | The nine strict gates, how a failed gate lowers or blocks a state, and how states aggregate per tier without ever merging categories. |
| **Figure 8** — From canonical records to published views | [`docs/en/workflows/catalog-data-generation.md`](../en/workflows/catalog-data-generation.md) | Which artifacts are generated and which are hand-written, and the one-payload rule that makes English and Arabic views structurally incapable of diverging. |
| **Figure 9** — Repository information architecture | [`docs/en/workflows/catalog-data-generation.md`](../en/workflows/catalog-data-generation.md) | The curated published surface, and the internal engineering history deliberately excluded from it. |

## Workflow coverage

The figure set covers the six required workflow narratives:

| Workflow narrative | Figures |
|---|---|
| Source discovery and controlled intake | Figure 3 |
| Architecture, memory and quantization analysis | Figure 4 |
| Quality evidence ingestion | Figure 5 |
| Retention and VRAM evidence flow | Figure 6 |
| Recommendation decision flow | Figure 7 |
| Repository data-generation flow | Figures 8 and 9 |

## Rendering notes

Diagrams use Mermaid and render natively on the repository host. To export them
to SVG for offline use:

```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i input.md -o diagrams.svg
```

## Visual identity assets

Brand assets are documented separately and are not diagrams:

| Asset | File |
|---|---|
| Repository icon (light surface) | [`assets/branding/icon.svg`](../../assets/branding/icon.svg) |
| Repository icon (dark surface) | [`assets/branding/icon-dark.svg`](../../assets/branding/icon-dark.svg) |
| Banner / social preview source | [`assets/branding/banner.svg`](../../assets/branding/banner.svg) |
| Brand guidelines (English) | [`assets/branding/brand-guidelines.md`](../../assets/branding/brand-guidelines.md) |
| Brand guidelines (Arabic) | [`assets/branding/brand-guidelines_AR.md`](../../assets/branding/brand-guidelines_AR.md) |
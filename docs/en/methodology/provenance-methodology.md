# Provenance Methodology

> Arabic counterpart: `docs/ar/methodology/provenance-methodology.md`

## Chain of origin

Every quantized or modified variant must resolve to its full lineage:

```text
variant → quantized model → modified/fine-tuned model → base model → original model family
```

A record that cannot name its base is incomplete, not original-by-default.

## What is recorded

For each link that can be established: the variant author and publication source,
the quantizer and quantizer repository with revision, the source revision or
commit of the artifact, checksums where available, and the evidence record tying
each statement to its source. Retrieval timestamps use ISO 8601 with timezone;
a URL pointing at a moving branch is recorded as accessed content, never as an
immutable revision.

## Why it matters

Capability, license, and safety statements all depend on which base a variant came
from and what was changed. A quantized derivative can carry different license
terms, different behavior, and different hardware demands than its base model.
Provenance is what keeps those statements attached to the right artifact, and it
is why discovery-stage records wait in `pending_*` states until lineage is resolved.

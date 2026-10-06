# External VRAM Evidence Closure

> Arabic counterpart: `docs/ar/methodology/external-vram-evidence-closure-methodology.md`

## Atlas never measures

Atlas stores externally reported VRAM observations and performs none. The
measurement registry, its origins and its schema are reused unchanged. Atlas
still has no `verified_fit` state, and evidence closure did not add one.

## Evidence source classes

A VRAM source class is *derived* from the measurement origin plus configuration
completeness, so no new persisted label can disagree with the stored origin:

| Class | Meaning |
|---|---|
| `V1` | independent reproducible measurement with exact configuration |
| `V2` | official runtime/vendor benchmark with exact configuration |
| `V3` | publisher measurement with sufficiently complete conditions |
| `V4` | structured community measurement with reproducible conditions |
| `V5` | anecdotal statement; can never create strict fit |

A measurement missing any of revision, artifact variant, runtime, runtime
version, backend, GPU, GPU VRAM, context, offload mode or a reported peak
collapses to `V5` regardless of how authoritative its origin sounds. A
community claim without a reproducible method is `V5`, not `V4`.

## Conditions a measurement must preserve

For a measurement to support a *measured memory requirement* it must state: the
exact artifact identity, a peak or otherwise reported VRAM value, the context
length, the offload mode, and the runtime version. Unknowns lower strength; they
are never assumed.

## Hard distinctions

- **Context.** A 2K measurement is not 8K evidence. The Atlas baseline profile
  stays `atlas-text-8k-baseline-v1`; no hidden new default is introduced.
- **Hardware tier.** A model measured at 6.5 GiB on a 24 GB card is *measured
  memory-requirement evidence*. It is never verified fit on an 8 GB card.
- **Offload.** CPU offload, partial layer offload, shared GPU memory and system
  RAM spill are never presented as full GPU-resident fit.
- **Size.** An artifact's byte size supplies the weight component only. It can
  never create a fit verdict.

## Why strict VRAM fit is currently zero

The VRAM classifier declares `estimated_fit` only when a *reliable upper
bound* fits inside tier capacity. The upper bound requires runtime static and
dynamic overhead. No Atlas runtime memory profile carries a documented overhead
figure, and inventing one would be fabrication. Closure therefore reports
`insufficient_evidence` for candidates whose lower bound is inside the tier,
plus genuine evidence-based `estimated_not_fit` verdicts where the lower bound
already exceeds capacity.

## Refusal over approximation

Hybrid and state-space attention (for example a linear-attention layer mixed
with full-attention layers) is **refused**, because estimating from attention
layers alone would understate memory and could manufacture a false fit. An
unmodeled component is never counted as zero.

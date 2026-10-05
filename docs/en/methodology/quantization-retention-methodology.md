# Quantization Retention Methodology (Phase 6)

Quantization retention answers one question: **how much of the base release's
measured quality survives in the quantized artifact?** The answer requires
evidence on both sides from a comparable setup. Otherwise the honest answer is
`unknown`.

## Retention states

| State | Meaning |
|---|---|
| `directly_measured` | Both sides measured, comparable setup |
| `independently_measured` | Comparable setup, independent origin on at least one side |
| `publisher_measured` | Comparable setup, publisher origin only |
| `partially_comparable` | Both sides measured, settings differ materially |
| `insufficient_evidence` | Only one side measured |
| `unknown` | No evaluation evidence for either side |

A retention percentage is produced **only** in the first three states. In
`partially_comparable`, `insufficient_evidence` and `unknown`, `absolute_delta`
and `relative_delta` stay `null`. A fake percentage is never substituted for a
missing comparison.

## Comparability requirement

Retention requires identical benchmark id and version, metric, unit, reasoning
mode, tool mode, prompting mode and context configuration on both sides.
Different benchmark version, different reasoning mode or different harness
blocks the comparison.

`relative_delta` is computed only for `higher_is_better` metrics. For
lower-is-better metrics the signed absolute delta is recorded and the relative
figure is left `null`, because a "relative improvement" on a lower-is-better
metric is ambiguous.

## No quant quality inheritance

Forbidden: "Base model scored 80, therefore Q4 also scores 80." Quantization
can change accuracy, reasoning, coding, instruction following and long-context
performance, so each requires its own evidence. The base score may be shown as
`base_model_quality_context` while the quantized artifact's retention remains
`unknown`.

## Extreme compression

For IQ1, IQ2, TQ, ternary, PTQ1, native low-bit and other extreme compression,
quality retention is never assumed from storage efficiency. Exact or closely
applicable evidence is required. In the current catalog these artifacts have no
exact benchmark evidence, so their retention is `unknown` or
`insufficient_evidence` — never an inherited number.

## Native low-bit

A native low-bit model may have benchmark results published on the native
release itself. Those results represent that release when identity is clear, so
the base-versus-quant inheritance problem does not arise. However, they are
never compared against post-training quantization as though the method were
identical. Native ternary, trained ternary, post-training ternarization and TQ
artifacts stay separate, and quality evidence attaches to the exact
representation.

## Publisher retention claims

Statements such as "retains 98% of original performance" remain
`publisher_claim` unless independently reproduced. The exact methodology and
source are stored where available, and a publisher claim never upgrades a
record to `publisher_measured` with independent standing.

## Disclosure in recommendations

When a quantized artifact has unknown retention, any recommendation must state
both facts: the base model's quality is known, and the quantized variant's
retention is unknown. The confidence category reflects that limitation, and the
artifact never receives the parent's quality as its own.
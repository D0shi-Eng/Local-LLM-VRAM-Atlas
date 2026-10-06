# Layer Plan Methodology

> Arabic counterpart: `docs/ar/methodology/layer-plan.md`

## Why per-layer truth

Modern configurations vary KV heads, attention presence, MLP type, and
MoE/dense structure between layers. A global config field is safe only when
it applies to all relevant layers. The Layer Plan (`src/atlas/archinfo/
layer_plan.py`) expresses one entry per layer: index, type, attention
presence, attention type, head counts, head dimension, sliding window, MLP
type, MoE facts, and state-space components. Only evidenced fields are set.

## Override rule

When per-layer overrides exist, the per-layer value wins for that layer.
Globals are never silently multiplied across heterogeneous layers. A plan
built from per-layer structures reports whether layers are heterogeneous.

## Refusal integrity

Layers without attention contribute zero only when `attention_present` is
explicitly `False`. Layers with unknown attention presence refuse the whole
calculation instead of silently becoming zero. An empty plan refuses.

## Layered calculation

The layered KV formula (`standard-kv-layer-plan-v1`) sums each attention
layer independently with its own effective context (sliding windows apply
per layer). The estimator selects this formula only when a Layer Plan is
supplied; otherwise the global formula applies with identical refusal rules.

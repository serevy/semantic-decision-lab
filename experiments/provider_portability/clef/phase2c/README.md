# Clef-Flash Phase 2C — backbone mechanism isolation

Phase 2B v0.2 localized the reproducible packed-question order effect upstream
of the released joint head. Semantic state/question/option token identity stayed
fixed, absolute question placement changed, released-path probabilities moved,
and the fixed-backbone head-only tuple-order control produced zero delta.

Phase 2C asks a narrower mechanism question:

> Which backbone-side signal is sufficient or necessary for the observed order
> sensitivity: ordinary positional signal, causal/context order, or placement
> of the question suffix relative to the shared state?

This is a new synthetic-control experiment. It does not reinterpret Phase 2B
Evidence and does not claim that synthetic position IDs are valid provider
requests.

## Frozen intervention matrix

Phase 2C reuses exactly the 3 fixtures x 6 packed question-order conditions
from Phase 1C / Phase 2A / Phase 2B.

### A. Standard-position reference

- 18 conditions total;
- request-native token order;
- request-native attention mask;
- ordinary model-generated position behavior;
- one observation per condition.

This arm is a within-run reference for the two synthetic controls. It is not a
new repeatability study.

### B. Zero-position order control

- the same 18 encoded conditions;
- request-native token order and causal sequence remain intact;
- request-native attention mask remains intact;
- only `position_ids` are replaced with an all-zero tensor;
- canonical vs five non-canonical orders are compared by semantic question ID.

If question-order deltas remain under this control, ordinary varying position
IDs are not necessary for the observed order sensitivity under this synthetic
condition. Such a result is consistent with causal predecessor/context order
contributing, but it does not identify a specific attention edge or layer.

### C. Canonical suffix-placement control

For each of the 3 canonical requests, run two additional synthetic backbones:

- keep canonical input IDs fixed;
- keep canonical question order fixed;
- keep the canonical attention mask and causal predecessor sequence fixed;
- keep state-prefix position IDs fixed;
- add a positive offset only to positions after the exact rendered state span;
- frozen offsets: `+32` and `+128`.

A non-zero delta here would show that the positional channel alone is sufficient
to move the decision path under this synthetic control. It would not prove that
position is the sole cause of the real permutation effect.

## Execution budget

- provider-neutral canary: 1;
- standard-position backbone forwards: 18;
- zero-position backbone forwards: 18;
- canonical suffix-shift backbone forwards: 6;
- experimental backbone forwards: 42;
- one loaded model;
- no retries inside a run.

Phase 2A's 18/18 exact three-repeat local result remains the frozen reason for
one observation per condition.

## Runtime boundary

The runtime family remains fixed to Phase 2B:

- `Cloudflare/clef-flash@17f0b0ad64efb65d273590632833508766b2aae6`;
- released `joint_schema_model.py` model/head;
- CUDA + BF16;
- torch 2.11.x;
- transformers 5.10.2;
- max length 16384;
- no quantization;
- no CPU offload.

Exact GPU identity is evidence. H100/H200 is the upstream-matched class;
another BF16-capable CUDA GPU remains a distinct runtime condition.

## Evidence recorded per condition

- exact request and encoded-input identity;
- semantic state/question/option token hashes;
- position-control mode;
- position-ID hash / min / max;
- suffix boundary and offset for suffix-shift controls;
- state/question/option/global backbone trace descriptors;
- logits;
- full probability distributions;
- response-schema validation;
- trace deltas aligned by semantic question/option ID.

The full distributions remain first-class evidence; label-only agreement is
insufficient for semantic conformance.

## Frozen interpretation boundary

Phase 2C freezes no semantic, numerical-noise, sufficiency, necessity, or
causality threshold before output.

Bounded interpretations only:

- persistence under zero position IDs weakens the claim that ordinary varying
  position IDs are necessary;
- movement under a suffix-only position shift shows positional signal can be
  sufficient under that synthetic control;
- either control can be off-distribution;
- neither control alone proves the exclusive mechanism of the real order effect;
- a null result is valid Evidence;
- no provider-quality ranking follows from this experiment.

## Evidence discipline

- freeze README, manifest, runner, analyzer, and offline tests before first
  Phase 2C model output;
- preserve Phase 2B files unchanged;
- preserve every failed Phase 2C run before any retry;
- never reuse a failed run identity;
- no post-output threshold selection;
- no silent context truncation;
- dry-run schedule must report exactly 18 + 18 + 6 experimental conditions.

Refs #81, #118, #140, #141.

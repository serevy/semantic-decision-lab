# Clef-Flash Phase 2A local v0.1 — Evidence summary

## Run identity

- Experiment: `clef-flash-phase2a-local-hosted-isolation`
- Provider: local inference (`joint_schema_model.py:systemone`)
- Model: `Cloudflare/clef-flash`
- Frozen HF revision: `17f0b0ad64efb65d273590632833508766b2aae6`
- Python: `3.13.15`
- torch: `2.11.0+cu130`
- transformers: `5.10.2`
- CUDA: `13.0`
- GPU: `NVIDIA A100-SXM4-80GB`
- dtype: `bfloat16`
- loaded parameter devices: `cuda:0`
- hardware condition: `explicit-non-upstream-hardware:NVIDIA A100-SXM4-80GB`
- upstream H100/H200 hardware match: `false`
- canary stage: `validated`
- experiment calls: **54 / 54 validated**
- total model calls including canary: **55**

The source run used the Phase 2A protocol frozen by PR #132. This Evidence is from
an A100-SXM4-80GB, which is intentionally retained as a distinct non-H100/H200
runtime condition rather than pooled with the upstream-matched hardware class.

## Local repeatability

All **18 / 18** frozen fixture/order conditions were byte-identical across their
three local repeats. Each condition had exactly one local response SHA-256, and
all repeat-to-repeat semantic metric deltas were zero.

## Local question-order sensitivity

All **15 / 15** non-canonical question-order conditions showed a non-zero metric
delta versus the corresponding local canonical packed request. Owner top-choice
flips remained **0**.

Per-fixture local maxima:

| fixture | outage probability | owner per-option | severity score | severity max-bin |
| --- | ---: | ---: | ---: | ---: |
| `payments-partial` | `0.0055` | `0.0077` | `0.0069` | `0.0092` |
| `storefront-hard` | `0.0240` | `0.0034` | **`0.1244`** | **`0.0671`** |
| `support-info` | **`0.0537`** | `0.0025` | `0.0138` | `0.0249` |

For comparison, the retained hosted Phase 1C maxima were:

- `storefront-hard` severity score: `0.1212`;
- `storefront-hard` severity max-bin: `0.0652`;
- `support-info` outage probability: `0.0530`.

The local reproduction therefore materially weakens a **hosted-layer-only**
explanation for the previously observed question-order sensitivity. It does not
identify a causal mechanism inside the released local path.

## Local vs hosted Phase 1C

The analyzer compared all **54** matching local/hosted calls.

- owner top-choice mismatches: **0 / 54**;
- outage probability delta: mean `0.001072`, max `0.0048`;
- owner per-option probability delta: mean `0.000306`, max `0.0010`;
- severity reported-score delta: mean `0.001578`, max `0.0082`;
- severity per-bin delta: mean `0.001578`, max `0.0061`.

Confidence remained a separate runtime/provider-semantics observation:

- owner confidence delta: mean `0.035494`, max `0.0606`;
- severity confidence delta: mean `0.168728`, max `0.2890`.

These confidence differences are not interpreted as probability-calibration
parity or quality differences.

## Interpretation boundary

This Evidence supports the bounded statement that question-order sensitivity is
reproduced through the released local Clef-Flash joint decision path under this
A100/BF16 runtime condition. It does **not** establish whether the effect is due
to serialization, tokenization/position, model weights, the joint head, or some
interaction among those layers.

It also does not establish:

- a universal sensitivity magnitude;
- permanent parity across hosted and local runtimes;
- a semantic pass/fail threshold;
- provider quality ranking;
- H100/H200 parity from this A100 run.

## Raw Evidence archive

`clef-phase2a-local-v0.1-evidence.tgz` is the exact archive produced from the
successful Colab run before interpretation. It contains:

- `run.json` and `canary.json`;
- all 54 per-call local Evidence JSON files;
- exact local raw responses, requests, hashes, encoding preflight, and runtime
  provenance for every call.

Integrity:

- raw Evidence archive SHA-256:
  `ee61a54ac658bbc8472a2c0b5ab704ac3aa29ea0c4c83ce96927e7c0bc4107b9`
- raw Evidence archive size: `10325` bytes
- analysis JSON SHA-256:
  `91b83415e7b92ba6263c62dc9602dfdd02b18d68a993165582e8ec34ac573cf1`
- JSON Evidence files with a `stage` field: **56**
- `stage: validated`: **56 / 56**

The raw archive is retained directly rather than reconstructing it from the
human-readable summary. The analysis file is preserved separately alongside it.

## PDDR checkpoint

No new PDDR is proposed.

Phase 2A strengthens the existing PDDR-0003 boundary: provider/runtime packing,
provenance, calibration/confidence semantics, and semantic parity remain explicit
and are not assumed equivalent. The result motivates a new experiment version to
isolate the source of question-order sensitivity, but does not itself change the
durable architecture decision.

Refs #118, #81, #130, #131, #132, #133

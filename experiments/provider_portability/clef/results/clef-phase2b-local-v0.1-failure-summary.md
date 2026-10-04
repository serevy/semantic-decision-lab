# Clef-Flash Phase 2B local v0.1 — failed first trace

## Outcome

The first Phase 2B traced run did **not** complete.

- freeze commit: `08c16640320805aeaad7942079dfbe87ea8f8d7a`
- run identity: `clef-phase2b-local-v0.1`
- model revision: `17f0b0ad64efb65d273590632833508766b2aae6`
- runtime: A100-SXM4-80GB / BF16 / torch 2.11.0+cu130 / transformers 5.10.2
- canary: validated
- first actual condition: `payments-partial / packed-canonical`
- first actual typed response: preserved
- first actual logits: preserved
- failure stage: `trace-error`
- completed Phase 2B traces: 0
- head-only counterfactuals: 0

## Failure

The actual model forward and released-head output completed successfully. The
runner then attempted to apply `model.head.hidden_norm` to backbone hidden
states outside the `torch.inference_mode()` context in which those hidden
states were created.

PyTorch rejected that use with:

```text
RuntimeError: Inference tensors cannot be saved for backward.
```

This is an experiment-runner tracing bug, not evidence of a Clef model contract
failure.

## Preserved first actual output

The first actual response was preserved before the trace failed.

- response SHA-256:
  `ba2db69107ac21385caf1fc04a6057d1f0676fc13cf28689475788846006f9a5`
- owner choice: `payments`
- outage noul: `0.0241`
- severity score: `1.0074`

The response SHA matches the retained Phase 2A `payments-partial /
packed-canonical / repeat-1` response. This is descriptive only; the failed
Phase 2B v0.1 run is not promoted to a successful experiment result.

## Evidence files

Exact JSON files recovered from the Google Drive Evidence directory are retained
alongside this summary:

- `clef-phase2b-local-v0.1-failure-run.json`
- `clef-phase2b-local-v0.1-failure-canary.json`
- `clef-phase2b-local-v0.1-failure-payments-partial-packed-canonical.json`

The original Drive directory remains the primary failed-run archive source.
Do not overwrite or resume it.

## Retry boundary

The failed v0.1 identity must never be reused.

A corrected runner must be frozen under a new protocol/run identity before retry,
while keeping the same model/runtime/fixture semantics unless explicitly changed.

Refs #118, #136.

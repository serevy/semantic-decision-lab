# Clef-Flash Phase 1A — packing and order sensitivity

This phase asks whether a frozen Clef-Flash System One decision changes when only
question packing or mapping order changes.

## Pre-output freeze

Before any Phase 1A provider output is observed, v0.1 freezes 14 variants:

- 1 canonical packed request;
- 5 non-canonical permutations of the three question IDs;
- 5 non-canonical permutations of the three owner choice IDs;
- 3 single-question requests for packing/isolation comparison.

The source state, instructions, criteria text, model selector, and score criteria
order are unchanged. Score criteria are never permuted because their ordinal
position is semantic.

## Transport invariant

The hosted runner now separates two hashes:

- `request_sha256`: order-insensitive canonical-content hash retained for backward compatibility;
- `wire_request_sha256`: order-sensitive SHA-256 of the exact JSON bytes sent to Workers AI.

This separation is required because the previous hosted smoke serializer used
`sort_keys=True` for the HTTP body. That behavior would have erased the very
question/choice order differences this phase intends to test.

The historical hosted smoke is **not reused as the Phase 1A baseline**. Although
its question and owner-choice order happened to match sorted order, recursive
sorting also changed top-level and state mapping order. Phase 1A therefore
remeasures `packed-canonical` with the new order-preserving serializer and
compares only Phase 1A variants against that new baseline. Top-level and state
mapping order remain fixed across all Phase 1A variants.

## Frozen comparison sets

Packing/isolation compares each single-question response with the same answer in
`packed-canonical`.

Question-order probes compare all common answers against `packed-canonical`.
Choice-order probes keep question order canonical and compare all common answers,
not only `owner`, because the released Clef architecture may couple packed
questions.

## Frozen metrics

- `noul`: absolute probability delta.
- `choice`: maximum per-option absolute delta, base-2 Jensen-Shannon divergence,
  top-choice flip, confidence absolute delta.
- `score`: reported-score absolute delta, expected-score absolute delta, maximum
  per-bin absolute delta, base-2 Jensen-Shannon divergence, confidence absolute delta.

No pass/fail semantic threshold is frozen in Phase 1A v0.1. The first result is
descriptive Evidence about sensitivity, not a quality ranking.

## Execution boundary

`run_workers_ai.py` executes the frozen variants in manifest order with no retries.
It preserves one Evidence JSON per variant and stops early on transport/configuration
failures. A contract-validation failure is preserved and does not mutate the matrix.

Hosted model revision remains unavailable behind the Workers AI alias, so results
must be interpreted as observations of that hosted alias at execution time.

# Clef-Flash Phase 1B — replication across incident states

Phase 1A found three notable properties on one frozen incident fixture:

- all five owner choice-order permutations had zero semantic metric delta;
- question-order permutations produced small non-zero changes;
- packed-vs-single execution changed some probability distributions, especially
  the severity distribution, more than the reported scalar score suggested.

Phase 1B tests whether those observations replicate when the **state changes**
while the question contract stays fixed.

## Pre-output freeze

Before any Phase 1B provider output is observed, v0.1 freezes three fixtures:

- `payments-partial`: partial payment degradation;
- `storefront-hard`: storefront rendering outage;
- `support-info`: support/status communication issue with product paths healthy.

These fixtures intentionally cover different incident surfaces and likely owner
regions, but **no semantic gold labels are frozen**. Phase 1B remains a
sensitivity/replication experiment, not a provider-quality benchmark.

Each fixture replays the exact 14 Phase 1A variants in the same order:

- 1 packed canonical baseline;
- 5 non-canonical question orders;
- 5 non-canonical owner-choice orders;
- 3 single-question isolation probes.

Total frozen provider calls: **42**.

## Inherited methodology

Phase 1B pins the Git blob identities of the Phase 1A matrix, probe builder,
analyzer, hosted runner, and original contract fixture. CI rejects drift before
any external call.

Within each fixture:

- top-level/state mapping order is fixed;
- question definitions and criteria are identical to the contract fixture;
- score criteria order is never permuted;
- no retry occurs;
- request and exact wire hashes are recorded and checked after every call.

## Frozen descriptors

No pass/fail threshold is defined.

The analysis records:

- how many fixtures retain exact zero delta across all five choice-order probes;
- how many fixtures show any non-zero question-order delta;
- per-fixture maxima for the Phase 1A question-order metrics;
- per-fixture packed-vs-single metrics for outage, owner, and severity;
- the packed baseline answers for provenance only.

Interpretation remains descriptive. A repeated pattern can motivate a later
durable design rule, but Phase 1B itself does not promote one.

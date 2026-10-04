# Clef-Flash Phase 1C — question-order repeatability control

Phase 1A and Phase 1B repeatedly observed non-zero metric differences between
question-order variants. Before treating those differences as order sensitivity,
Phase 1C measures the hosted path's repeatability for **identical wire requests**.

## Pre-output freeze

Phase 1C keeps the three Phase 1B fixtures and only the six packed question-order
conditions:

- packed canonical;
- all five non-canonical permutations of the three question IDs.

Choice-order and single-question probes are intentionally excluded.

Each fixture/order condition is executed exactly **three times**, for:

- 3 fixtures;
- 6 order conditions;
- 3 repeats;
- **54 provider calls total**.

## Interleaved schedule

The 54 calls use three frozen rounds. Both fixture order and question-order
condition order are shifted between rounds so identical conditions are not simply
executed three times back-to-back.

This does not eliminate every hosted-time confound because the Workers AI alias
does not expose an immutable model revision. It does make simple sequential drift
less able to masquerade as a stable condition difference.

## Frozen descriptors

No causality or semantic pass/fail threshold is defined before output.

For each fixture/order condition, Phase 1C records:

- number of unique raw response SHA-256 values across the three repeats;
- repeat-1 versus repeat-2/3 metric deltas using the Phase 1A metric definitions;
- observed owner labels.

For each non-canonical order, it also records all **nine** pairwise comparisons
between the three canonical repeats and the three variant repeats.

The key interpretation question is descriptive:

> Are between-order differences visibly larger and more stable than the
> within-identical-request repeat variation?

If identical conditions are byte-identical while different orders remain
different, that materially strengthens an order-sensitivity interpretation for
the observed hosted alias/window. If identical conditions vary, Phase 1A/1B
differences must be interpreted against that noise floor.

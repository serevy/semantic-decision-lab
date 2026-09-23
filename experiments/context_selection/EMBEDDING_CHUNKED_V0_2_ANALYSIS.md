# Embedding chunked v0.2 analysis

## Result

The frozen complete-record chunked condition did **not** improve required-context
retrieval at Top-2.

| condition | required hits | mean required recall | mean useful recall | precision | irrelevant rate | reduction |
|---|---:|---:|---:|---:|---:|---:|
| first-512-token embedding | 10/12 | 0.8333 | 0.2778 | 0.7083 | 0.2917 | 0.6667 |
| complete-record chunks + max aggregation | 9/12 | 0.7500 | 0.3611 | 0.7083 | 0.2917 | 0.6667 |

The chunked arm rescued **ctx-002**, where required PDDR-0006 moved from rank 3
to rank 2. **ctx-003** remained rank 3. Two previously correct cases became new
misses: **ctx-006** and **ctx-007**.

This means that exposing the complete record is not, by itself, a monotonic
improvement under the frozen max-chunk scoring rule.

## Rank changes around required records

- ctx-002 / required PDDR-0006: rank **3 -> 2**, score
  **0.841031 -> 0.869666**, winning chunk 1.
- ctx-003 / required PDDR-0007: rank **3 -> 3**, score
  **0.867942 -> 0.864234**, winning chunk 2.
- ctx-006 / required PDDR-0004: rank **1 -> 3**, score
  **0.848380 -> 0.855227**, winning chunk 0.
- ctx-007 / required PDDR-0005: rank **1 -> 4**, score
  **0.853153 -> 0.853343**, winning chunk 0.

For ctx-006, PDDR-0006 chunk 4 and PDDR-0003 chunk 4 outranked the required
PDDR-0004. For ctx-007, PDDR-0006 chunk 4, PDDR-0004 chunk 3, and PDDR-0003
chunk 4 outranked required PDDR-0005.

Inspection of the frozen corpus shows that the winning tail chunks of
PDDR-0003 and PDDR-0006 are largely delivery/evidence/related-record material.
That is consistent with a local-match / max-aggregation failure hypothesis, but
the 12-case dataset is too small to establish it as a general cause.

## What this changes

PR #69/#71 showed that the original embedding arm was an invalid proxy for
full-record retrieval because every PDDR passage was truncated. PR #72 fixed
that representation gap, but the complete-record result is **worse on the
primary required-recall metric**.

Therefore:

1. Do not replace the frozen first-512 baseline with the chunked arm.
2. Do not infer that "more document coverage" automatically improves PDDR
   retrieval.
3. Keep the max-chunk arm as evidence of a simple complete-record baseline,
   including its possible document-length / multiple-opportunity bias.
4. Avoid tuning chunk size, overlap, or aggregation against these 12 labels in
   place. Any alternate representation must be a new versioned condition.

## Next experiment boundary

The original protocol also requires **downstream task success**. The retrieval
arms now disagree in informative ways: keyword Top-2 has the strongest required
recall among reduced-context Top-2 arms, the first-512 embedding arm has known
input invalidity as a full-record proxy, and the chunked arm trades one rescued
required case for two new misses while increasing useful recall.

The next high-value slice should therefore evaluate whether those retrieval
differences actually change downstream task success under a frozen task/evaluator
contract, rather than continuing to tune retrieval on the same 12 gold labels.

A structural/section-aware retrieval condition remains a possible later
diagnostic if downstream failures show that retrieval representation is the
bottleneck.

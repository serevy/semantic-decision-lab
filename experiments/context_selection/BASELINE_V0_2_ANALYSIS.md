# Dataset v0.2 baseline failure analysis

This note freezes the first failure analysis for Experiment #2 after the
12-case / 2-corpus dataset v0.2 baseline replay.

The dataset and gold were frozen in PR #64. Baseline runners were introduced in
PR #65 and executed in workflow run
[`35728375871`](https://github.com/serevy/semantic-decision-lab/actions/runs/35728375871).
No task, gold label, model, prompt, ranking rule, or Top-k value is changed by
this analysis.

Machine-readable aggregate evidence, artifact digests, exact result-file hashes,
per-case selections, and the score ranks used below are stored in
[`results/baseline-v0.2-evidence.json`](results/baseline-v0.2-evidence.json).

## Aggregate snapshot

| Arm | Required hit | Useful recall | Selection precision | Irrelevant rate | Mean reduction |
|---|---:|---:|---:|---:|---:|
| Full context | 12/12 | 1.000 | 0.479 | 0.521 | 0.000 |
| Keyword Top-2 | 11/12 | 0.528 | 0.917 | 0.083 | 0.667 |
| multilingual-e5-small Top-2 | 10/12 | 0.278 | 0.708 | 0.292 | 0.667 |

The full-context control preserves every required and useful record, but does not
reduce context. Both Top-2 arms materially reduce the bounded corpora. The
keyword arm misses one required record; the embedding arm misses two.

These values describe this frozen diagnostic set only. They do **not** establish
that keyword retrieval is generally better than semantic retrieval. The tasks
were authored from known decisions, so lexical overlap is itself a possible
dataset advantage that should be tested later.

## Failure A — ctx-003 is shared by keyword and embedding

`ctx-003` asks for the safe upgrade mechanism for an already adopted PDDR Kit.
The required record is **PDDR-0007**, which defines manifest/hash-based upgrades,
dry-run behavior, conflict stopping, and the project-owned exclusions.

Both Top-2 arms instead return:

- PDDR-0001 — broad project rationale; gold marks it irrelevant here
- PDDR-0003 — external-adoption findings; useful, but not the required upgrade mechanism

For the embedding arm, PDDR-0007 is **rank 3**, immediately outside the frozen
Top-2:

1. PDDR-0001 — 0.8698444
2. PDDR-0003 — 0.8693416
3. **PDDR-0007 — 0.8679416**

This is a concrete example of a broad/general decision and an adjacent useful
decision outranking the mechanism-specific required record.

## Failure B — ctx-002 is embedding-only

`ctx-002` asks for the Consumption Contract: historical PDDR is not executable
policy, current instructions/policy take precedence, and only the minimum
relevant records should be selected.

The required record is **PDDR-0006**. Keyword Top-2 includes it, while the
embedding arm selects PDDR-0001 and PDDR-0003, both gold-irrelevant for this
case.

Again the required record is **rank 3**:

1. PDDR-0001 — 0.8487826
2. PDDR-0003 — 0.8444420
3. **PDDR-0006 — 0.8410314**

The miss is therefore sensitive to the frozen Top-2 cutoff, not a case where the
required record is far down the ranking.

## Cutoff sensitivity is now a first-class question

Both embedding required misses are at rank 3. A Top-3 replay would recover those
two required records on this frozen score set, but it would also reduce context
less:

- 7-record corpus: reduction falls from 71.4% at Top-2 to 57.1% at Top-3
- 5-record corpus: reduction falls from 60% at Top-2 to 40% at Top-3

This should be tested as a **new frozen reduction-frontier condition**, not by
retroactively changing v0.2 Top-2 results.

## Broad-record attractor observation

The embedding arm selects **PDDR-0001 in 10/12 cases**. In five of those
(`ctx-002`, `ctx-003`, `ctx-009`, `ctx-010`, `ctx-011`) the gold labels
mark PDDR-0001 irrelevant.

This is consistent with a possible broad-document / semantic-attractor effect,
but the present evidence does not establish its cause. In particular, we should
not label it model "hubness" as a proven mechanism without a targeted diagnostic.

## Long-context instrumentation is incomplete

The current embedding replay fixes the model revision and prefixes, but the
Evidence does not record effective tokenizer input lengths or whether any
passage was truncated by the embedding stack.

Therefore this run supports **no truncation claim either way**. Before making
long-context conclusions, a separate diagnostic should record token counts,
effective limits, and truncation status without changing the frozen gold.

## Next experiment slice

The baseline failures suggest three concrete additions before tuning providers:

1. **Top-k reduction frontier** — replay the frozen v0.2 rankings over multiple
   Top-k values and report required recall versus reduction.
2. **Input-length diagnostics** — record tokenizer lengths / truncation state for
   the embedding arm as a separate diagnostic condition.
3. **Downstream task success** — test whether a selected context set actually
   preserves task behavior, not only gold record IDs.

Semantic backend families remain frozen under PDDR-0002. Existing semantic arms
can later be replayed on dataset v0.2 under the provider-neutral contract without
adding new backend families.

## PDDR checkpoint

This work adds experiment Evidence and failure categories. It does not introduce
a new durable Project / Product / Process decision beyond PDDR-0002 through
PDDR-0004, so this checkpoint intentionally creates **no new PDDR**.

# Dataset v0.2 Top-k frontier analysis

This note records the observed required-recall / context-reduction frontier for
Experiment #2 without changing dataset v0.2, gold labels, provider/model,
ranking semantics, or the already frozen Top-2 evidence.

Source workflow:
[`35743653448`](https://github.com/serevy/semantic-decision-lab/actions/runs/35743653448)

The uploaded artifact digest is
`sha256:3fc82bb3a373adc978f05a134cd83965c947d96175018ff75b4f0c5f65290a35`.
A compact machine-readable Evidence summary is preserved in
[`results/topk-frontier-v0.2-evidence.json`](results/topk-frontier-v0.2-evidence.json).

## Observed frontier

| Top-k | Keyword required hit | Embedding required hit | Mean context reduction |
|---:|---:|---:|---:|
| 1 | 10/12 | 9/12 | 83.3% |
| 2 | 11/12 | 10/12 | 66.7% |
| 3 | 12/12 | 12/12 | 50.0% |
| 4 | 12/12 | 12/12 | 33.3% |
| 5 | 12/12 | 12/12 | 16.7% |
| Full context | 12/12 | 12/12 | 0% |

Within the tested range, **Top-3 is the first point where both frozen ranking
arms recover all required records while still removing 50% of context on
average**.

This is an observation, not a production recommendation.

## Where the frontier changes

At Top-1:

- keyword misses `ctx-002` and `ctx-003`
- embedding misses `ctx-002`, `ctx-003`, and `ctx-005`

At Top-2:

- keyword recovers `ctx-002` and still misses only `ctx-003`
- embedding recovers `ctx-005` and still misses `ctx-002` / `ctx-003`

At Top-3:

- both arms recover all required records

So the required-recall gap between the two arms is concentrated near the
cutoff. It is not evidence that their full rankings are equivalent, nor does it
say anything yet about useful-context recall or downstream task quality.

## Why Top-3 is not a policy decision yet

The experiment's highest-priority guardrail is required-context recall, but
selection quality has other dimensions:

- useful-context recall
- irrelevant-context rate / precision
- downstream task success
- latency and cost
- model/input-length validity

This frontier slice deliberately measures only required recall versus reduction.
A Top-3 operating point is therefore a **follow-up candidate**, not an accepted
default.

## Remaining confound: embedding input length

The current multilingual-e5-small Evidence still does not record effective
tokenizer input lengths or truncation state. The frontier replay reuses the
frozen score ordering and cannot resolve that missing instrumentation.

Before attributing embedding behavior to model semantics, the next low-cost
diagnostic should record:

- tokenizer-declared effective limit
- per-PDDR passage token count
- whether truncation occurs
- the exact text span retained if truncation occurs

without changing dataset or gold.

## PDDR checkpoint

The frontier is new experiment Evidence, but it does not establish a durable
Project / Product / Process rule. In particular, this note does **not** adopt
Top-3 as a permanent selection policy.

No new PDDR is created at this checkpoint.

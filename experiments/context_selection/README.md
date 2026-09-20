# PDDR context-selection pilot

This directory contains the frozen three-case pilot for Experiment #2.

The gold labels were defined before provider runs. Do not silently edit them after observing keyword, embedding, Jev, or other provider outputs. Corrections require a versioned dataset change with rationale.

## Smoke test

```bash
python experiments/context_selection/evaluate_context_selection.py \
  experiments/context_selection/cases.v0.1.json \
  experiments/context_selection/selections.gold-only.json
```

The gold-only smoke selection should produce required recall 1.0, irrelevant rate 0.0, and a positive reduction ratio for every case. It is only a metric-semantics check, not an experimental result.

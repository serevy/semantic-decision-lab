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


## Baselines

The first baselines are intentionally simple and deterministic.

```bash
# Full-context control
python experiments/context_selection/run_baseline.py \
  experiments/context_selection/cases.v0.1.json \
  experiments/context_selection/corpus/pddr-kit-v0.1 full 7

# Keyword baseline (top 2)
python experiments/context_selection/run_baseline.py \
  experiments/context_selection/cases.v0.1.json \
  experiments/context_selection/corpus/pddr-kit-v0.1 keyword 2
```

Pipe either output to a selections JSON file and pass it to `evaluate_context_selection.py`.

The keyword baseline uses normalized token overlap only. It is deliberately not tuned per case and must remain frozen once provider comparisons begin.


## Embedding baseline v0.1

The first semantic-retrieval baseline is frozen before observing its output:

- model: `intfloat/multilingual-e5-small`
- model revision: `fd1525a9fd15316a2d503bf26ab031a61d056e98`
- sentence-transformers: `6.1.0`
- retrieval: normalized embedding cosine similarity
- query prefix: `query: `
- document prefix: `passage: `
- top-k: **2**, matching the keyword baseline

The corpus is Japanese while the task text is English, so a multilingual retrieval model is used deliberately. This is still a retrieval baseline, not a semantic-decision provider.

Run:

```bash
pip install -r experiments/context_selection/requirements-embedding.txt
python experiments/context_selection/run_embedding_experiment.py
```

Do not change the model, revision, prefixes, or top-k after seeing results without creating a new experiment version.

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


## SemanticDecisionProvider contract v0.1

Semantic backends are kept behind a provider-neutral typed contract. For every
candidate PDDR, an adapter returns a probability distribution over:

- `required`
- `useful`
- `irrelevant`

The experiment applies one shared selection policy after the provider returns:

1. higher `required_probability` first
2. then higher `useful_probability`
3. then PDDR ID for deterministic ties
4. take top-k = **2**
5. an explicit provider abstention selects nothing

This keeps the evaluator independent from Jev-specific or open-backend response
shapes and prevents each backend from choosing its own threshold/cutoff after
seeing results. Provider adapters may batch questions, make multiple calls, or
run locally; those details belong in adapter/run provenance, not evaluator code.

Contract tests:

```bash
cd experiments/context_selection
python -m unittest -v test_semantic_provider.py
```


## Open Jev HTTP adapter

The first concrete open backend adapter targets
`intikhab49/open-jev-typed-decision-engine` running its local
`python 05_serve.py --serve` endpoint.

The adapter sends the frozen task and all candidate PDDR records as state, then
asks one dynamic `choice` question per record with the same three labels used by
the provider-neutral contract: `required`, `useful`, and `irrelevant`.

The backend's probabilities are normalized into `CandidateDecision`; the shared
contract still owns ranking and the fixed **Top-2** cutoff.

Example after starting the external backend:

```bash
python experiments/context_selection/run_open_jev_experiment.py \
  experiments/context_selection/cases.v0.1.json \
  experiments/context_selection/corpus/pddr-kit-v0.1 \
  --endpoint http://127.0.0.1:8000/decide \
  --top-k 2 \
  --output-dir experiments/context_selection/results/open-jev-v0.1
```

CI tests only the adapter mapping with a fake transport; it does not download,
train, or load the external model.


### Open Jev v0.1 frozen run

Before the first real provider output is observed, the exact upstream revision,
training/calibration configuration, and dynamic-schema model choice are frozen in
`providers/open-jev-v0.1.json`.

Use `OPEN_JEV_RUNBOOK.md` for the GPU/Colab run. The experiment runner records
provider revision and checkpoint SHA-256 in `provenance.json`.


### One-shot Colab execution

For the first real Open Jev v0.1 measurement, use a **fresh Colab T4 runtime**
and run `open_jev_v0_1_colab.ipynb`. The notebook delegates to
`run_open_jev_colab.py`, which performs the pinned clone, smoke test, training,
calibration, local serving, experiment run, provenance capture, and shutdown.

The runner refuses to overwrite an existing `results/open-jev-v0.1` directory,
so the first observed provider output cannot be silently replaced.

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


## Open Jev v0.2 independent record packing

v0.1 is preserved as raw evidence but classified as an adapter/context-packing
failure: all three tasks were truncated away and reached the model as identical
1,024-token inputs.

v0.2 changes only the adapter packing:

- one PDDR record per backend request
- the frozen task text lives in the question instructions
- one `required/useful/irrelevant` Choice per request
- seven distributions are combined into the same provider-neutral result
- the shared Top-2 ranking policy is unchanged

The frozen configuration is in `providers/open-jev-v0.2.json`.

The 1,024-token preflight showed that independent packing fixed task loss but
still truncated every long PDDR record. Before any v0.2 provider output was
observed, the v0.2 inference context was therefore frozen at **4,096 tokens**.
The exact-token preflight now fails if even one frozen PDDR record is truncated.

The upstream checkpoint is still trained with max_len=1,024; v0.2 changes only
the inference context exposed to the same ModernBERT-base encoder (8,192-token
capacity) and records that condition in provenance.

If the original Colab runtime still contains the v0.1 checkpoint, reuse it when
possible so the next run isolates packing/context changes. Otherwise the one-shot
runner retrains with the frozen v0.1 training configuration and records the new
checkpoint SHA-256.

Run the rematch in a Colab T4 with `open_jev_v0_2_colab.ipynb`.


## Laya multilingual v0.1

The next semantic-provider arm uses the multilingual Laya checkpoint so the
English task / Japanese PDDR setting can be tested explicitly rather than
treating all typed-decision backends as equivalent.

Frozen before provider output:

- source: `NandhaKishorM/laya@42626c348753fbb17572a813127df2278a1ec527`
- model: `convaiinnovations/laya-multilingual@4bb4d65403a3a7b8abd9e6876ccb5e75cf923b5c`
- model SHA-256: `9d628fd971b700382ac6f65920a86f149777b2e748e0c955fb3b19695aa8f204`
- checkpoint default max_len: 1024
- inference max_len: **4096**
- head_max_len: **256**
- one complete PDDR record per classification
- shared `required/useful/irrelevant` labels and shared **Top-2**
- checkpoint temperatures are used as shipped; no calibration is fitted on the
  frozen three PDDR cases

The exact pinned `build_sequence` implementation is exercised before inference.
The run aborts unless all 21 inputs preserve the complete task/question, all
three criteria, and the complete PDDR state, and unless each PDDR's final input
hash differs across the three tasks.

Use `LAYA_MULTILINGUAL_V01_RUNBOOK.md` or
`laya_multilingual_v0_1_colab.ipynb` for the first T4 run.


## Zefan Open-Jev 2B v0.1

After the Laya multilingual arm, the next open backend uses the released
Qwen-based 2B Open-Jev checkpoint from `Zefan-Cai/Open-Jev`.

Frozen before provider output:

- source: `Zefan-Cai/Open-Jev@ed45657bf726c3b77408942830e5578f99df904e`
- model: `ZefanCai/Open-Jev-2B@0c7aa498b1627be8da4acf34c863ff0ee0a92785`
- base: `Qwen/Qwen3.5-2B@15852e8c16360a2fea060d615a32b45270f8a8fc`
- packaged checkpoint SHA-256:
  `3076462e6356412082e79af909227b39b2863b90def79155ca0821aa506b7ded`
- saved temperature: `1.518796342858676`
- max_length: **4096**
- batch_size: **1**
- prefix cache: **off**
- one complete PDDR per relevance Choice
- shared `required/useful/irrelevant` labels and **Top-2**

The upstream loader uses BF16 for the Qwen backbone. The frozen first run keeps
that behavior and requires a BF16-capable CUDA GPU; it refuses T4 rather than
silently switching dtype.

Before inference, pinned upstream request compilation and candidate rendering are
combined with the pinned Qwen tokenizer/chat template. All 63 candidate
sequences must preserve task, complete PDDR text and candidate text, remain
within 4096 tokens, and differ across tasks for the same PDDR.

The real HTTP responses must also prove the frozen checkpoint digest, base
revision, source revision, max length, LoRA decision-head method and disabled
prefix cache.

Use `ZEFAN_OPENJEV_2B_V01_RUNBOOK.md` or
`zefan_openjev_2b_v0_1_colab.ipynb` for the first run.


## typed-decision-bert v0.1

The final methodologically distinct backend arm in the current Experiment #2
comparison uses the JevBERT P0.5 PoC from
`hawkymisc/typed-decision-bert`.

Frozen before provider output:

- source revision:
  `f0994cd4c91e7516f0e2a8d9e04b71107c309642`
- bundle: `jevbert-poc-nli-ja-en-0.2.0`
- bundle digest:
  `sha256:61dbb2190c473fa8925a523e28f32a1ec83df1dcbb2f52f832fdbdea0cb1d494`
- backend: `a0-nli-zeroshot-v2`
- serializer: `serializer-nli-v1+nli-template-v1`
- source model:
  `MoritzLaurer/bge-m3-zeroshot-v2.0@9abf1c8aaeb82a2447809c20753ed0b106b76652`
- FP32
- uncalibrated T=1.0
- server sequence limit: 2048
- one complete PDDR per relevance Choice
- shared labels / Top-2 / frozen dataset / gold unchanged

This arm fills the comparison gap between embedding retrieval and
typed-decision-specific training by testing a multilingual **zero-shot NLI
cross-encoder**.

Before inference, all 63 candidate sequences are reconstructed with the pinned
upstream compiler/template, BGE-M3 tokenizer, and JevBERT A0 escape/assembly
rules. No truncation is allowed. The preflight also records how many sequences
exceed the tokenizer-declared 512-token limit, because the PoC allows up to
2048 but upstream quality above 512 is not established.

Use `TYPED_DECISION_BERT_V01_RUNBOOK.md` or
`typed_decision_bert_v0_1_colab.ipynb` for the first run.

After this arm is frozen, backend expansion pauses for the planned issue audit.


## Dataset v0.2 — 12-case balanced expansion

v0.2 expands the frozen three-case pilot to **12 cases across two real PDDR
corpus snapshots** without changing any v0.1 pilot task or gold label.

Corpora:

- `pddr-kit-v0.1`: the existing seven-record pilot snapshot
- `readme-i18n-kit-v0.1`: five records pinned from
  `serevy/readme-i18n-kit@a4eba358cf3174532c7e07c54ad1d1a13dc240fc`

Design invariants frozen before any v0.2 baseline/provider run:

- ctx-001 through ctx-003 are byte-for-byte unchanged for
  `difficulty`, `task`, `corpus`, and `gold` relative to
  `cases.v0.1.json`
- ctx-004 through ctx-007 add the four pddr-kit records that were not the
  required record in the pilot
- ctx-008 through ctx-012 add one case for each readme-i18n-kit PDDR
- each case has exactly one required record
- **every record in each corpus snapshot is the required record exactly once**
  across that snapshot's cases, avoiding a required-label frequency prior
- required/useful/irrelevant partitions cover the full bounded corpus
- new labels are derived from the frozen PDDR text and written before any v0.2
  provider output is observed
- later label corrections require a new dataset version and rationale

Validate the freeze:

```bash
python experiments/context_selection/validate_dataset_v0_2.py
python experiments/context_selection/evaluate_context_selection.py \
  experiments/context_selection/cases.v0.2.json \
  experiments/context_selection/selections.gold-only.v0.2.json
```

The gold-only smoke is a metric-semantics check only. Do **not** run v0.2
keyword, embedding, or semantic-provider arms until the dataset-freeze change
has been reviewed and merged.


## Dataset v0.2 baseline replay

After the v0.2 dataset freeze is merged, replay the provider-neutral baselines
before any semantic backend optimization.

Frozen baseline conditions:

- full-context control: all records in the case's frozen corpus snapshot
- keyword baseline: existing normalized token-overlap implementation, Top-2
- embedding baseline:
  - `intfloat/multilingual-e5-small`
  - revision `fd1525a9fd15316a2d503bf26ab031a61d056e98`
  - normalized cosine similarity
  - `query: ` / `passage: ` prefixes
  - Top-2
- evaluator semantics unchanged from v0.1

The v0.2 runners resolve each case's `corpus_snapshot` through
`corpus-registry.v0.2.json`; no cross-corpus retrieval is performed in this
phase.

Results are written to new `baseline-v0.2` and `embedding-v0.2` directories.
v0.1 evidence is immutable.

## Dataset v0.2 baseline Evidence freeze

The first v0.2 baseline workflow completed successfully in PR #65. The
repository now preserves a compact machine-readable Evidence summary with
artifact digests, result-file SHA-256 hashes, aggregate metrics, selections, and
failure-rank evidence:

- [`results/baseline-v0.2-evidence.json`](results/baseline-v0.2-evidence.json)
- [`BASELINE_V0_2_ANALYSIS.md`](BASELINE_V0_2_ANALYSIS.md)

The failure analysis does not change the frozen Top-2 condition. Top-k frontier,
input-length diagnostics, and downstream task success are follow-up experiment
conditions rather than edits to the observed v0.2 results.

## Dataset v0.2 Top-k reduction frontier

The first baseline failure analysis showed that both multilingual-e5-small
required misses at frozen Top-2 were ranked **third**. The next slice therefore
replays the selection budget without changing dataset, gold, model, or score
ordering.

Frozen frontier condition:

- dataset: v0.2, unchanged
- tested Top-k: **1 through 5**
- keyword: the existing deterministic normalized token-overlap selector
- embedding: required-record ranks derived from the exact frozen PR #65 score
  artifact, whose result-file SHA-256 is already preserved in
  `results/baseline-v0.2-evidence.json`
- primary comparison: required-context recall versus context reduction
- Top-2 must reproduce the already frozen v0.2 evidence before the frontier is
  accepted

Run:

```bash
python experiments/context_selection/run_topk_frontier_v0_2.py
```

Results are written to `results/topk-frontier-v0.2/frontier.json`. This is a
budget replay, not provider tuning. Secondary precision/useful-recall analysis
and downstream task success remain separate follow-up slices.

## Dataset v0.2 embedding input-length diagnostics

The Top-k frontier still leaves one model-validity question unresolved: the
frozen multilingual-e5-small runner did not record effective tokenizer input
lengths or truncation state.

This diagnostic uses the **same pinned SentenceTransformer model revision and
the same `query: ` / `passage: ` strings** as the baseline. It records:

- `SentenceTransformer.max_seq_length`
- tokenizer class / fast-tokenizer capability / declared model max length
- raw token count before truncation
- actual token count produced by `SentenceTransformer.tokenize`
- whether tokens are truncated
- truncated-token count
- when offset mappings are available, the exact retained character boundary and
  SHA-256 hashes of retained/dropped text

It does **not** rerun similarity scoring, change Top-k, or alter gold labels.
Observed truncation is evidence that text is omitted from model input; it is not
by itself proof that truncation caused a retrieval miss.

## Dataset v0.2 embedding diagnostic result

The exact input-length diagnostic completed successfully. With the frozen
`multilingual-e5-small` stack, **all 12 PDDR passages were truncated to 512
tokens**, while all 12 task queries fit without truncation.

Preserved Evidence and interpretation:

- [`results/embedding-input-diagnostics-v0.2-evidence.json`](results/embedding-input-diagnostics-v0.2-evidence.json)
- [`EMBEDDING_INPUT_DIAGNOSTIC_V0_2_ANALYSIS.md`](EMBEDDING_INPUT_DIAGNOSTIC_V0_2_ANALYSIS.md)

The original v0.2 embedding result remains immutable evidence for the
first-512-token condition. A complete-record / chunked embedding experiment must
use a new versioned result path.

## Dataset v0.2 complete-record chunked embedding condition

PR #69 / #71 established that every frozen PDDR passage exceeded the embedding
model's 512-token input limit. The next condition isolates the representation
change while keeping dataset, gold, model revision, query text, Top-k, and
evaluator semantics fixed.

Frozen before observing output:

- model: same `intfloat/multilingual-e5-small` revision as the v0.2 baseline
- dataset / gold: v0.2 unchanged
- Top-k: **2**
- chunk content budget: **448 tokenizer tokens**
- chunk overlap: **64 tokens**
- chunk step: **384 tokens**
- chunks are cut from original text using fast-tokenizer offset mappings
- every prefixed chunk must fit the model's effective max sequence length
- document score: **maximum cosine similarity across its chunks**
- tie break: PDDR ID ascending
- no cross-corpus retrieval

The exact condition is versioned in
[`embedding-chunked-condition.v0.2.json`](embedding-chunked-condition.v0.2.json).

Run:

```bash
python experiments/context_selection/run_embedding_chunked_experiment_v0_2.py
```

Results are written to `results/embedding-chunked-v0.2/`.

This condition intentionally uses max-chunk aggregation as a simple first
complete-record representation. Because documents with more chunks receive more
opportunities to produce a high score, any observed gain/loss belongs to the
**chunking + max-aggregation condition as a whole**. Do not silently tune chunk
size, overlap, or aggregation after seeing the first output; changes require a
new versioned condition.

## Dataset v0.2 complete-record chunked embedding result

The frozen complete-record chunked Top-2 run completed successfully. Required
hits were **9/12**, compared with **10/12** for the original first-512-token
embedding arm. It rescued ctx-002, left ctx-003 missed, and introduced new
required misses in ctx-006 and ctx-007. Mean useful recall increased from
0.2778 to 0.3611 while selection precision and irrelevant rate were unchanged.

Evidence and interpretation:

- [`results/embedding-chunked-v0.2-evidence.json`](results/embedding-chunked-v0.2-evidence.json)
- [`EMBEDDING_CHUNKED_V0_2_ANALYSIS.md`](EMBEDDING_CHUNKED_V0_2_ANALYSIS.md)

The chunked arm remains a frozen complete-record baseline; it does not replace
the original embedding evidence and is not evidence that complete-record
visibility improves retrieval. The next priority is downstream task success,
not in-place chunk/aggregation tuning on the same 12 labels.

## Downstream task-success v0.1 freeze

Retrieval-ID metrics are now separated from a first bounded downstream behavior
slice. The 12 downstream cases map 1:1 to ctx-001..012 but ask for a
project-specific action rather than a PDDR ID.

Frozen before any downstream-model output:

- four plausible actions (A-D) per case plus `ABSTAIN`
- balanced gold labels: A/B/C/D each appear exactly three times
- gold source record and rationale are never included in the model prompt
- six context arms:
  - no-context negative control
  - required-only oracle/minimal-context control
  - full-context control
  - frozen keyword Top-2
  - frozen first-512 embedding Top-2
  - frozen complete-record chunked Top-2
- retrieval selections are replayed from existing Evidence; no selector is
  rerun or tuned for this slice
- one downstream run must use the same model and sampling configuration across
  all arms

Files:

- [`downstream-cases.v0.1.json`](downstream-cases.v0.1.json)
- [`downstream-arms.v0.1.json`](downstream-arms.v0.1.json)
- [`downstream-evaluation-contract.v0.1.json`](downstream-evaluation-contract.v0.1.json)

Validate the pre-output freeze and evaluator semantics:

```bash
python experiments/context_selection/validate_downstream_v0_1.py
python experiments/context_selection/evaluate_downstream_v0_1.py \
  experiments/context_selection/selections.downstream-gold-smoke.v0.1.json
```

Primary metrics are gold action accuracy and wrong-action rate. Abstention,
behavior preservation versus full context, and no-context correctness are
diagnostics. A high no-context score weakens the case as evidence that selected
PDDR context preserved the behavior.

PDDR-0004's explicit downstream-evaluation revisit condition is triggered here.
PDDR-0005 is included as **proposed** and must not be treated as accepted until
maintainer approval.


# typed-decision-bert v0.1 runbook

This runbook freezes the final methodologically distinct backend arm in the
current Experiment #2 PDDR Context Selection comparison before observing any
provider output.

## Frozen identity

- source: `hawkymisc/typed-decision-bert`
- source revision: `f0994cd4c91e7516f0e2a8d9e04b71107c309642`
- bundle: `jevbert-poc-nli-ja-en-0.2.0`
- bundle digest:
  `sha256:61dbb2190c473fa8925a523e28f32a1ec83df1dcbb2f52f832fdbdea0cb1d494`
- backend: `a0-nli-zeroshot-v2`
- serializer: `serializer-nli-v1+nli-template-v1`
- source model: `MoritzLaurer/bge-m3-zeroshot-v2.0`
- source model revision:
  `9abf1c8aaeb82a2447809c20753ed0b106b76652`
- dtype: **float32**
- calibration: **uncalibrated**, T=1.0
- max sequence tokens: **2048**
- max request tokens: **131072**
- shared Top-2 unchanged

No training, calibration fitting, prompt tuning, truncation, or gold-label
change is part of this arm.

## Why this arm exists

The currently tested backends cover lexical retrieval, embedding retrieval,
small typed-decision models, multilingual typed-decision models and a 2B
Qwen-based trained decision head.

typed-decision-bert adds a different point in the design space: a
**multilingual zero-shot NLI cross-encoder** that converts each proposed answer
into an entailment problem without task-specific typed-decision training.

## Preflight

Before provider output, the pinned upstream validator/compiler/template and the
pinned BGE-M3 tokenizer are used with the published JevBERT A0 escaping and
sequence assembly.

All 21 case/PDDR requests and 63 candidate sequences must preserve:

- the exact task
- the complete PDDR state
- the exact candidate label and description
- final encoded length <= 2048
- no truncation
- distinct final hashes for the same PDDR under different tasks

The tokenizer declares a 512-token model limit even though the PoC server
allows 2048. The preflight therefore records the number of sequences above 512
instead of hiding that quality caveat.

## Runtime identity

Before the first provider prediction, the authenticated
`/jevbert/v1/capabilities` response must match the frozen bundle digest,
backend, serializer, source model revision, FP32 dtype, uncalibrated
temperatures and token limits.

## Colab

Use `typed_decision_bert_v0_1_colab.ipynb` on an NVIDIA GPU.

A successful run produces:

`/content/typed-decision-bert-v0.1-results.zip`

Only after ZIP creation does the runner remove its temporary backend checkout,
model files and dedicated Hugging Face cache.

Do not overwrite first valid evidence. Any condition change requires a new
experiment version.

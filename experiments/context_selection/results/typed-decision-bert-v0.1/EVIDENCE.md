# typed-decision-bert v0.1 evidence

This directory freezes the first valid typed-decision-bert / JevBERT P0.5
provider run for Experiment #2.

## Run identity

- source repository: `hawkymisc/typed-decision-bert`
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
- GPU: NVIDIA L4
- max sequence tokens: **2048**
- max request tokens: **131072**
- top-k: **2**
- observed_at_utc: `2026-09-22T09:07:05.129455+00:00`

No training, calibration fitting, prompt tuning, truncation, or selection-policy
change was performed after observing provider output.

## Input validity

The pinned upstream request validator/compiler/template plus pinned BGE-M3
tokenizer and the published JevBERT A0 escape/assembly path checked all 21
case/PDDR classifications and all 63 candidate sequences before inference:

- complete task preserved
- complete PDDR state preserved
- candidate label/description preserved
- all 63 candidate sequences <= the frozen 2048-token server limit
- no truncation
- same PDDR under the three tasks produced distinct combined final-input hashes:
  **all 7 records**
- fallback escaping was not required on the observed inputs
- maximum observed candidate length: **1912 tokens**

Runtime capabilities matched the frozen bundle digest, backend, serializer,
source-model revision, FP32 dtype, uncalibrated T=1.0 temperatures, and token
limits before the first provider prediction.

This is therefore a valid execution/packing/runtime-identity run.

## Critical quality caveat: 63/63 sequences exceed tokenizer-declared 512

The underlying pinned tokenizer reports `model_max_length = 512`.

**Every one of the 63 final candidate sequences exceeded 512 tokens**, while
remaining within the JevBERT PoC server's explicitly configured 2048-token
limit.

Therefore this evidence must not be read as an evaluation of established
BGE-M3 zero-shot NLI quality inside its tokenizer-declared length range.
It records the behavior of the frozen JevBERT PoC configuration on this PDDR
workload. The source project itself had not established quality above the
tokenizer-declared 512-token range.

Do not silently remove, truncate, summarize, or chunk the PDDRs to "fix" this
run; any such change is a new experiment version.

## Result

| case | required PDDR | selected Top-2 | required rank | required recall |
| --- | --- | --- | ---: | ---: |
| ctx-001 | PDDR-0002 | PDDR-0002, PDDR-0006 | 1 | 1.0 |
| ctx-002 | PDDR-0006 | PDDR-0004, PDDR-0002 | 3 | 0.0 |
| ctx-003 | PDDR-0007 | PDDR-0002, PDDR-0006 | 7 | 0.0 |

Required hit rate: **1/3**.

All cases use the shared Top-2 cutoff, so the context reduction ratio is
**71.4%** for every case.

The three tasks changed final encoded inputs and provider probabilities. The
Top-2 set for ctx-001 and ctx-003 was the same, while ctx-002 differed. This
small sample supports only task sensitivity of the frozen inputs/outputs; it
does not establish context-selection quality.

Recorded provider HTTP time across the 21 classifications was
**8.827378368 seconds**. This excludes environment setup/model download time.

Total JevBERT expanded-input token count reported by the server was **89,091**.
This is JevBERT's own `expanded-input-a0-v1` accounting and is not a Jev
billing-token metric.

## Artifact integrity

The uploaded first-valid-run ZIP is committed as `raw-results.zip`.

ZIP SHA-256:

`abbaa8a380dabc5efd59fa511668a160eb4ce0e04d0e09f7267517148b8a8cb5`

Contained file SHA-256 values:

- `provenance.json`: `151a54590235c76d173a7a604b637bc4852b4cb5356bc26222cd6dc298d0bd2a`
- `provider-results.json`: `8683c9fae9dfd436287b64ab615696bec13bfb8fa3f3467ff6bd229bed700286`
- `input-preflight.json`: `3367b008fbedea8885ec00fedee174e6ebf0bca7d7811a9486412199ad0cc4d7`
- `selections.json`: `552ec659dacfefc3a2cd5d96b30144af6ab4adecd6e66f0912d03b51c12aecbe`
- `metrics.json`: `b73aac751548636f4fd97fd2823d7f954f4ef81e42a619f593a6ea8261d6fd33`

The ZIP is the byte-preserving source artifact containing all five raw files.
The small summary JSON files are also committed directly for quick inspection.

Do not overwrite this evidence. Any change to input length handling, PDDR
packing, prompt/template, model/bundle, dtype, calibration, or selection policy
requires a new experiment version.

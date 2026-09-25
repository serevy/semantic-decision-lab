# Downstream task-success v0.2 — first-run Evidence

## Status

Frozen first-run Evidence for Experiment #2 / Issue #97.

v0.2 was harder than v0.1, but the pre-output context-dependence gate did not pass. The run therefore remains benchmark-design Evidence and must not be used to claim that retrieval misses preserve project decision behavior.

## Run provenance

- Workflow run: https://github.com/serevy/semantic-decision-lab/actions/runs/36035143735
- Repository head: `4ebbc459951370c27f7b5ceede89a460bd805a66`
- Provider: OpenAI
- Model: `gpt-5.6-luna`
- Reasoning effort: `none`
- Temperature: `0`
- Max completion tokens: `8`
- Requests: **72**
- Valid responses: **72**
- API / transport errors: **0**
- Exact-choice parse errors: **0**
- Returned model: `gpt-5.6-luna` for **72/72**

Frozen request pack SHA-256:

`bb7eb5109f46c93dd2e4a8ca0ceb9a99b36c6f2bc4eecdf044ede6e40b84b325`

Execution-order SHA-256:

`d8fea40bd7118fcf420a23a700022c28bb504421d1f29d7f502139bda2765c33`

## Artifact provenance

- artifact id: `10825221547`
- artifact digest: `sha256:b1e25f081d691b88af3930de255433b062a7c203476b3cf8867fc052691c035c`
- expires: `2026-12-23T17:33:33Z`

Hashes inside the downloaded artifact:

- `raw-results.json`: `2333162a11934cd5187b0e89d95f1e3a425c60531a148769b383ef404f6cf983`
- `evaluator-input.json`: `613f1ef27017346e395b7d91f8e07762b3381fffdd4735ee43de31a725197a21`
- `evaluation.json`: `bae7533c465d0fa2311448d1c074808273be52d7c1ead71489d2a88cda5d8b2c`

## Results

| arm | correct | abstain | gold accuracy | required record present |
| --- | ---: | ---: | ---: | ---: |
| no-context | 10/12 | 2/12 | 0.8333 | 0/12 |
| required-only | 12/12 | 0/12 | 1.0000 | 12/12 |
| full-context | 12/12 | 0/12 | 1.0000 | 12/12 |
| keyword Top-2 | 12/12 | 0/12 | 1.0000 | 11/12 |
| first-512 embedding Top-2 | 12/12 | 0/12 | 1.0000 | 10/12 |
| complete-record chunked Top-2 | 12/12 | 0/12 | 1.0000 | 9/12 |

Additional answerability diagnostics:

- no-context expected behavior: `ABSTAIN`
- no-context abstention rate: **2/12 = 0.1667**
- no-context unsupported commitment rate: **10/12 = 0.8333**

## Frozen diagnostic gate

| check | result |
| --- | --- |
| no-context correct <= 8/12 | **FAIL** |
| required-only correct >= 10/12 | pass |
| full-context correct >= 10/12 | pass |
| required-only - no-context >= 2 | pass |
| full-context - no-context >= 2 | pass |

Overall gate: **FAIL**.

## Interpretation

v0.2 improved the negative control from v0.1's 12/12 no-context score to 10/12, so the benchmark became more context-sensitive.

However, the model still committed to an A-D action in 10/12 no-context cases, and every one of those commitments happened to match the hidden gold action. The benchmark therefore still allowed generic engineering priors and option wording to mask whether the required PDDR was actually present.

The replayed retrieval arms make the masking visible:

- keyword Top-2 missed one required PDDR but still scored 12/12;
- first-512 embedding Top-2 missed two required PDDRs but still scored 12/12;
- complete-record chunked Top-2 missed three required PDDRs but still scored 12/12.

The v0.2 result must therefore **not** be interpreted as evidence that those retrieval misses were behaviorally harmless.

## Follow-up

Issue #102 moves the diagnostic to matched counterfactual pairs. Within each pair, prompt-visible scenario/options are identical while the supplied decision context selects opposite plausible actions.

# Downstream context-fidelity v0.3 — first-run Evidence

## Status

Frozen first-run Evidence for Experiment #2 / Issue #102.

v0.3 passed the full pre-output context-fidelity gate.

## Run provenance

- Workflow run: https://github.com/serevy/semantic-decision-lab/actions/runs/36099039635
- Repository head: `05170ffccafecf7e894c695a7dd8ea997a166c97`
- Provider: OpenAI
- Model: `gpt-5.6-luna`
- Reasoning effort: `none`
- Temperature: `0`
- Max completion tokens: `8`
- Requests: **48**
- Valid responses: **48**
- API / transport errors: **0**
- Exact-choice parse errors: **0**

Frozen request pack SHA-256:

`9d4a78f8a39bc7ecdf2d209780f48d5b7a9dd2c5dae345bd0454c0eb97ae92ef`

Execution-order SHA-256:

`16539e09e0ac0df5e5846fdea209aab3d5ebd162b7364fd30678eb307283a00f`

Config SHA-256:

`fcd542edeb4275a00db101e1a69314b4cd0671a50e2d97fc131ee1ba807da141`

## Artifact provenance

- artifact id: `10848421945`
- artifact digest: `sha256:932f135bb9ec3a0e6e916267e7dc6a8c942bd7de4bc9523d11e624e99bfab845`
- expires: `2026-12-24T05:33:09Z`

Hashes inside the downloaded artifact:

- `raw-results.json`: `3cfde78ac7faaea625ef797d7f6340269b80a657daaa72ff94f1c3331746ffb3`
- `evaluator-input.json`: `e0cfe042ae0fbf37cb4e2d2401fa670f58d8f5577c3d235e31e8c93f7d3c1051`
- `evaluation.json`: `b0c9a8a0c673eb262d199a8a966b6d4c1a9bac83c84e6f08f5d3afe22a394649`
- `downstream-requests.v0.3.jsonl`: `9d4a78f8a39bc7ecdf2d209780f48d5b7a9dd2c5dae345bd0454c0eb97ae92ef`

## Results

| arm | gold correct | abstain | wrong action |
| --- | ---: | ---: | ---: |
| no-context | 0/12 | **12/12** | 0/12 |
| correct-context | **12/12** | 0/12 | 0/12 |
| wrong-context | 0/12 | 0/12 | **12/12** |
| both-contexts | 0/12 | **12/12** | 0/12 |

Matched-pair behavior:

- correct-context pair flips: **6/6**
- wrong-context supplied-context follow: **12/12 = 1.0**

## Frozen diagnostic gate

| check | result |
| --- | --- |
| correct-context correct >= 10/12 | pass |
| no-context ABSTAIN >= 10/12 | pass |
| matched-pair correct flips >= 5/6 | pass |
| both-contexts ABSTAIN >= 8/12 | pass |

Overall gate: **PASS**.

## Interpretation

v0.3 removes the major v0.1/v0.2 confound.

With no Decision Context, the model abstained on all 12 cases. With the matching
Decision Context, it selected all 12 project-specific gold actions and flipped
correctly across all six otherwise-identical matched pairs. With both conflicting
accepted cards, it abstained on all 12 cases.

This establishes that the downstream model is behaviorally sensitive to the
supplied decision context under the bounded v0.3 contract rather than merely
reconstructing the hidden gold from generic engineering priors.

The wrong-context arm is equally important: when the sibling counterfactual
decision was supplied, the model followed it on all 12 cases. Decision Context
is therefore not just informative; it is behaviorally causal enough that an
incorrectly retrieved accepted decision can deterministically redirect the
downstream action in this slice.

That makes retrieval correctness a meaningful next variable.

## Follow-up

Issue #106 recouples retrieval to the matched-snapshot design.

The v0.4 protocol scopes ranking to one active project snapshot, freezes
keyword/embedding selections before any downstream output, and then measures
whether required-card hit/miss states predict downstream correctness,
abstention, or wrong action.

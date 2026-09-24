# Downstream task-success v0.1 — first-run Evidence

## Status

Frozen first-run Evidence for Experiment #2 / Issue #74.

The run completed mechanically successfully, but the downstream slice did **not**
establish that retrieval preserved project decision behavior. The no-context
negative control also achieved 12/12, so the task wording/options were sufficient
for the downstream model to recover every gold action without PDDR context.

Do not rewrite this result after hardening the benchmark. Follow-up work belongs
to a new version; see Issue #97.

## Run provenance

- Workflow run: https://github.com/serevy/semantic-decision-lab/actions/runs/35940937705
- Repository head: `5a58e466ad721a320f28f91731660931940f491c`
- Provider: OpenAI
- Model: `gpt-5.6-luna`
- Reasoning effort: `none`
- Temperature: `0`
- Max completion tokens: `8`
- Requests: **72**
- Valid responses: **72**
- API / transport errors: **0**
- Exact-choice parse errors: **0**

Frozen request pack SHA-256:

`67977e204aea5618e2683b0be42d33696e0d83885e64a79612186588e6c89ca7`

Execution-order SHA-256:

`26658b10589611a0d4a2f8271d63084d1d41301148b6b0d32713a5fcf1d13a49`

## Artifact provenance

GitHub Actions artifact:

- id: `10785662652`
- digest: `sha256:719d7164090c6e8c12d54dd2bce71d2bb736b2087b3603107abe81fce5bd0ada`
- expires: `2026-12-23T00:59:50Z`

Hashes inside the downloaded first-run artifact:

- `raw-results.json`: `8e57ffca476f44b1d52c0ad010b864a2a5c6fec377d780b411403c08d59bced1`
- `evaluator-input.json`: `76786042a11bd0d5582b05ef29f4fbb3d090793e738f1b94d9505e59d391f85e`
- `evaluation.json`: `18a4819beea2bd94865366da6a41f146f939bee0fa50b6fd9ba9e5942b58f77f`

The full ~0.9 MB request JSONL is not duplicated here because the repository's
frozen deterministic builder reproduces it and the SHA-256 above identifies the
exact request pack.

## Results

| arm | correct | accuracy | wrong-action rate | abstention rate |
| --- | ---: | ---: | ---: | ---: |
| no-context | 12/12 | 1.00 | 0.00 | 0.00 |
| required-only | 12/12 | 1.00 | 0.00 | 0.00 |
| full-context | 12/12 | 1.00 | 0.00 | 0.00 |
| keyword Top-2 | 12/12 | 1.00 | 0.00 | 0.00 |
| first-512 embedding Top-2 | 12/12 | 1.00 | 0.00 | 0.00 |
| complete-record chunked Top-2 | 12/12 | 1.00 | 0.00 | 0.00 |

`no_context_correct_rate_as_prompt_leakage_signal = 1.0`.

## Interpretation

Earlier frozen retrieval Evidence contains real required-record misses:

- keyword Top-2: 11/12 required hit
- first-512 embedding Top-2: 10/12
- complete-record chunked Top-2: 9/12

Those misses produced no downstream difference in v0.1 because the no-context
arm already solved every bounded-choice task.

Therefore:

1. **Do not** interpret 12/12 on the reduced-context arms as proof that their
   retrieval misses were harmless.
2. **Do** treat the negative control as a successful diagnostic: it exposed that
   the benchmark was not sufficiently context-dependent.
3. Preserve v0.1 unchanged and harden the downstream benchmark through a new
   version rather than tuning the frozen retrieval arms against these labels.

## Follow-up

Issue #97 defines downstream v0.2 benchmark hardening. Its key requirement is
that project-specific PDDR context must be necessary to resolve the action, with
plausible distractors and a pre-output context-dependence audit.

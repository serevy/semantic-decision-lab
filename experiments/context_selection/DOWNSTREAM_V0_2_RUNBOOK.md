# Downstream task-success v0.2 execution runbook

This runbook executes the already-frozen context-dependent downstream v0.2
evaluation from Issue #97. It reuses GPT-5.6 Luna from v0.1 so the first v0.2
comparison changes the benchmark design rather than the downstream model family.

## Frozen request pack

The deterministic builder must reproduce:

- requests: **72**
- bytes: **914,765**
- SHA-256: `bb7eb5109f46c93dd2e4a8ca0ceb9a99b36c6f2bc4eecdf044ede6e40b84b325`

The first pre-output preview was produced by workflow run
`35967410372`.

## Live condition

- provider: OpenAI Chat Completions
- model: `gpt-5.6-luna`
- reasoning effort: `none`
- temperature: `0`
- max completion tokens: `8`
- concurrency: 1
- minimum request-start interval: 8.1 seconds
- transport retries: 0
- exact output parser: A/B/C/D/ABSTAIN

The live workflow reuses the existing repository `OPENAI_API_KEY` and shares
the README-i18n concurrency lock only for the paid API job.

## Interpretation boundary

A mechanically successful run may still fail the frozen benchmark diagnostic
gate. That is valid Evidence, not an infrastructure failure.

The v0.2 evaluator separately reports:

- gold-action accuracy
- wrong-action rate
- abstention
- no-context unsupported commitment
- no-context answerability success
- accuracy when the required PDDR is present vs absent
- frozen context-dependence gate pass/fail

Do not edit the v0.2 cases, options, gold, prompt, or diagnostic thresholds after
observing the first live output.

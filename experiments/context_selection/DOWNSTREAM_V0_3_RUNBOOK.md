# Downstream context-fidelity v0.3 execution runbook

This runbook executes the frozen matched-counterfactual evaluation from Issue #102.

## Frozen request pack

The deterministic builder must reproduce:

- requests: **48**
- bytes: **90,188**
- SHA-256: `9d4a78f8a39bc7ecdf2d209780f48d5b7a9dd2c5dae345bd0454c0eb97ae92ef`

The first pre-output preview was produced by workflow run `36098682182`.

## Live condition

- provider: OpenAI Chat Completions
- model: `gpt-5.6-luna`
- reasoning effort: `none`
- temperature: `0`
- max completion tokens: `8`
- concurrency: 1
- minimum request-start interval: 8.1 seconds
- transport retries: 0
- exact parser: A/B/C/D/ABSTAIN

The live workflow reuses repository secret `OPENAI_API_KEY`.

## Four context arms

- no-context: expect ABSTAIN
- correct-context: expect project gold
- wrong-context: diagnostic follow rate
- both-contexts: expect ABSTAIN because accepted cards conflict

## Interpretation boundary

A mechanically successful run may fail the frozen diagnostic gate. That is valid research Evidence.

v0.3 isolates downstream context fidelity and does not claim retrieval quality.
Do not alter cards, matched tasks, gold, prompt contract, or gate after observing
the first live output.

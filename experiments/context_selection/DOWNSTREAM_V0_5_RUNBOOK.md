# Downstream historical-miss coupling v0.5 execution runbook

This runbook executes the frozen v0.5 coupling experiment from Issue #109.

## Frozen request pack

- requests: **54**
- bytes: **509,138**
- SHA-256: `67f7a0b2f282246b62fb8fd8358517eb50ca03ce429487532d5a7e6114e35d1a`

Pre-output preview:
https://github.com/serevy/semantic-decision-lab/actions/runs/36332932773

## Historical retrieval miss distribution

The retrieval selections are exact replays from pre-existing frozen v0.2 evidence:

- keyword Top-2: 5/6 required hits
- first-512 embedding Top-2: 4/6
- complete-record chunked Top-2: 3/6

They are not rerun or tuned in v0.5.

## Live condition

- OpenAI Chat Completions
- model: `gpt-5.6-luna`
- reasoning effort: `none`
- temperature: `0`
- max completion tokens: `8`
- concurrency: 1
- minimum request-start interval: 8.1 seconds
- retries: 0
- exact parser: A/B/C/D/ABSTAIN

## Interpretation

The control gate must pass before interpreting retrieval coupling.

The core output is whether historical required-record misses now map to:
- ABSTAIN,
- wrong action,
- or accidental gold action,

after the matched-counterfactual controls established that no-context generic-prior rescue is suppressed.

Do not alter the v0.5 cases, historical selections, prompt contract, or evaluator after observing the first live output.

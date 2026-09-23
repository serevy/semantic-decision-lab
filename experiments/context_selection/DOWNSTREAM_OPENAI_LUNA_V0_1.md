# OpenAI Luna downstream run v0.1

This file freezes the first downstream-model execution condition for Experiment
#2. It is reviewed before any model output is observed.

## Why Luna for the first run

The downstream task is a bounded A-D/ABSTAIN decision task over already-frozen
project context. The first run uses `gpt-6-luna` as a cost-sensitive
high-volume model rather than making the first evidence run also a test of a
more expensive reasoning configuration. OpenAI's 2026-09-22 release lists
GPT-6 Luna at $0.10 / 1M input tokens and $0.50 / 1M output tokens for Standard
short-context processing, 50% below GPT-5.6 Luna's promotional input price and
more than 50% below its promotional output price.

This is **not** a claim that Luna is the best downstream model. OpenAI reports
broad capability improvements for GPT-6 Luna over its predecessor, but this
experiment will measure the exact `reasoning_effort=none` bounded-choice
condition rather than importing benchmark conclusions. A later Sol or
other-model replication is a separate versioned run if the experiment needs it.

## Frozen condition

See `downstream-run.openai-luna-v0.1.json`.

- OpenAI Chat Completions
- model: `gpt-6-luna`
- reasoning effort: `none`
- temperature: 0
- max completion tokens: 8
- one request at a time
- at least 8.1 seconds between request starts
- no transport retries in the first evidence run
- deterministic SHA-256-ranked execution order
- strict exact-choice parsing: A/B/C/D/ABSTAIN only

The request-pack SHA-256 must match the frozen v0.1 manifest before the runner
can call the API.

## Execution boundary

PR validation performs only `--dry-run`; it cannot call OpenAI.

After this condition is merged, a maintainer may manually dispatch
`Context selection downstream OpenAI Luna v0.1` and must type
`RUN_LUNA_V0_1`. The live job uses the existing repository
`OPENAI_API_KEY` secret and uploads raw/evaluated evidence as an Actions
artifact.

A transport/API failure stops the run and preserves the partial result artifact.
The first evidence run does not silently retry individual requests. Invalid
model formatting is preserved as a parse error rather than coerced into
`ABSTAIN`.

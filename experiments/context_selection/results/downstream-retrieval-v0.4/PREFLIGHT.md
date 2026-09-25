# Downstream v0.4 retrieval preflight Evidence

## Status

Pre-output retrieval-only Evidence for Issue #106.

No downstream model was called.

## Provenance

- Workflow run: https://github.com/serevy/semantic-decision-lab/actions/runs/36158498159
- PR head: `8856d23c27c577f26b765c282e30dcdca7a54eeb`
- retrieval result SHA-256: `70f36d4602732e047986906fe541dc0fc812bde59c7ccfef3ccbbf0d34656efb`
- artifact id: `10874457247`
- artifact digest: `sha256:2664810f0d4c4fcba4bc115603a3bf9c53e6df014c0132026130ddb2f85927ad`
- artifact expires: `2026-10-09T16:07:22Z`

Embedding condition:

- model: `intfloat/multilingual-e5-small`
- revision: `fd1525a9fd15316a2d503bf26ab031a61d056e98`
- sentence-transformers: `6.1.0`
- normalized cosine
- `query: ` / `passage: ` prefixes

## Required-card hit results

| selector | required hit |
| --- | ---: |
| keyword Top-1 | **12/12** |
| keyword Top-2 | **12/12** |
| embedding Top-1 | **12/12** |
| embedding Top-2 | **12/12** |

## Interpretation

The matched two-snapshot corpus is too separable for the intended retrieval-coupling question.

Every frozen selector retrieves the required card for every case even at Top-1. If this slice were sent to the paid downstream model, the retrieval arms would contain no hit/miss variation, so the run could not test whether a retrieval miss becomes downstream ABSTAIN or wrong action.

This is a successful **pre-output stop** rather than a failed downstream experiment.

No selector, query, Top-k, or downstream prompt is tuned against model output because no downstream output exists.

## Disposition

Do not create a paid v0.4 downstream run for this corpus.

The next slice should reuse pre-existing frozen retrieval evidence that already contains misses, rather than manufacturing misses by tuning this new corpus after observing its retrieval results.

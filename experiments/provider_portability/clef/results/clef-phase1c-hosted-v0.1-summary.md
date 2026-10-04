# Clef-Flash Phase 1C hosted v0.1 — Evidence summary

## Run identity

- Workflow run: `37206425338`
- Workflow head: `22eee3e0b531f89303ce78b6f54d41eea0516271`
- Artifact ID: `11305000613`
- Artifact digest: `sha256:06ea548d2aedd9a4bf305a2ae9c21220b0530cfc6c2fe894118e122beeb62c1f`
- Frozen manifest SHA-256: `931786cbb8a53d8883e51ebdbe36f27cf3c9c49a4fb3b05684fd26997694b00d`
- Provider: `cloudflare-workers-ai`
- Model alias: `@cf/cloudflare/clef-flash`
- Hosted immutable model revision: unavailable
- Provider calls: **54 / 54**
- Failures: **0**

Phase 1C measured repeatability for the same six packed question-order conditions
across the three Phase 1B fixtures. Each fixture/order condition was executed
three times using a frozen interleaved schedule.

## Repeatability result

There were **18 conditions** total.

- byte-identical across all three repeats: **18 / 18**
- unique raw-response SHA-256 values per condition: **1**
- within-identical-request semantic metric delta: **0**
- owner choice remained stable across every repeat

A cross-workflow comparison also matched each Phase 1C repeat-1 response against
the same fixture/order condition from the earlier Phase 1B workflow:

- raw-response SHA-256 matches: **18 / 18**

The two workflows were separated by roughly thirteen minutes.

## Between-order result

While identical wire requests were byte-identical, changing only the question
mapping order continued to produce the same non-zero differences observed in
Phase 1B.

### payments-partial maxima

- outage probability delta: `0.0051`
- owner max per-option delta: `0.0085`
- owner confidence delta: `0.0245`
- severity reported-score delta: `0.0058`
- severity max-bin delta: `0.0088`
- severity confidence delta: `0.0217`
- owner top-choice flip: false

### storefront-hard maxima

- outage probability delta: `0.0296`
- owner max per-option delta: `0.0033`
- owner confidence delta: `0.0098`
- severity reported-score delta: **`0.1212`**
- severity max-bin delta: **`0.0652`**
- severity confidence delta: `0.0470`
- owner top-choice flip: false

### support-info maxima

- outage probability delta: **`0.0530`**
- owner max per-option delta: `0.0025`
- owner confidence delta: `0.0072`
- severity reported-score delta: `0.0139`
- severity max-bin delta: `0.0252`
- severity confidence delta: `0.0548`
- owner top-choice flip: false

## Interpretation

Phase 1C materially weakens the hypothesis that the Phase 1A/1B question-order
differences are ordinary run-to-run stochastic noise.

For the observed Workers AI alias and observation window:

> identical wire requests produced identical response bytes, while different
> question mapping orders produced reproducibly different fixed responses.

The strongest supported statement is therefore about the **hosted pipeline**,
not necessarily the Clef model weights alone. The current evidence does not
isolate whether the sensitivity originates in the released joint decision head,
serialization/tokenization, or another hosted processing layer.

It also does not establish:

- permanent determinism of the moving Workers AI alias;
- behavior under a future hidden hosted revision;
- hosted/local Clef parity;
- a provider-quality ranking;
- a universal semantic threshold for acceptable order sensitivity.

No new PDDR is required yet: this strengthens the existing PDDR-0003 rule that
packing, transport/runtime provenance, calibration, and semantic parity must be
kept distinct.

## Raw Evidence bundle

The complete compact bundle is stored as four ordered Base64 text parts:

- `clef-phase1c-hosted-v0.1.bundle.json.gz.b64.part-00`
- `clef-phase1c-hosted-v0.1.bundle.json.gz.b64.part-01`
- `clef-phase1c-hosted-v0.1.bundle.json.gz.b64.part-02`
- `clef-phase1c-hosted-v0.1.bundle.json.gz.b64.part-03`

Concatenating them reproduces the original Base64 file containing all 54 exact
provider response bodies, request/wire hashes, run identity, and analysis.

Integrity of the concatenated bundle:

- uncompressed compact JSON SHA-256:
  `b8565405e5611035fae32ae7fd8c4839392e4d4a4ed95bae30053081d7de0120`
- decoded gzip SHA-256:
  `0eba089ef62afd6396be66f9d1396a6a48d16823c98d6df38a399533ac833cdb`
- concatenated Base64 text SHA-256:
  `616f895c4bef1d2e93a31daecbf15ad4a4977d76d3f3f8b4febdfe5e5fc4820c`

Example reconstruction:

```bash
cat clef-phase1c-hosted-v0.1.bundle.json.gz.b64.part-* |
  base64 -d |
  gzip -d > clef-phase1c-hosted-v0.1.bundle.json
```

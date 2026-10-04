# Clef-Flash Phase 1A hosted v0.1 — Evidence summary

## Run identity

- Workflow run: `37203075106`
- Workflow head: `45039ddf3e416f17b34aa229240bc6b56ed07769`
- Artifact ID: `11303433490`
- Artifact digest: `sha256:bf7ed7d898908ae537bab2a589171ee154fb15cc933a28498db396c5ba0dbf2b`
- Frozen matrix SHA-256: `a7272d7c12c570ccef70d8d49f3412269c12ba1324d6750b6406cf2642500a76`
- Provider: `cloudflare-workers-ai`
- Model alias: `@cf/cloudflare/clef-flash`
- Hosted immutable model revision: unavailable
- Variants executed: **14 / 14**
- HTTP failures: **0**
- Contract failures: **0**

The historical hosted smoke is not used as the Phase 1A baseline. Phase 1A
remeasured `packed-canonical` after switching the wire serializer from recursive
sorted-key JSON to mapping-order-preserving JSON.

## Frozen baseline

`packed-canonical` returned:

- outage / noul: `0.9403`
- owner: `payments`
  - payments: `0.9738`
  - storefront: `0.0132`
  - support: `0.0130`
  - confidence: `0.9231`
- severity score: `2.6487`
  - 0: `0.0097`
  - 1: `0.0087`
  - 2: `0.3048`
  - 3: `0.6768`
  - confidence: `0.4015`

Its raw response SHA-256 was
`c8564d76753a7206ee8856737da5d45eca1ba10d3a43550aadf200e65bce94cb`,
the same response-body digest observed in the earlier hosted smoke. This is an
observation only; the hosted alias does not expose an immutable model revision.

## Choice-order probes

All five non-canonical owner-choice permutations produced **zero semantic metric
delta** against the packed baseline:

- no top-choice flips;
- per-option maximum absolute delta: `0`;
- Jensen-Shannon divergence: `0`;
- confidence delta: `0`;
- outage and severity metrics also remained `0`.

The raw response bytes differ because the response probability mapping follows
the supplied choice-key order, but values attached to each option key are
identical in this fixture.

Interpretation: choice mapping order showed no observed semantic/calibration
effect for this single frozen fixture. This does **not** establish universal
choice-order invariance or reveal whether normalization occurs in the hosted
service or the model path.

## Question-order probes

All five non-canonical question permutations kept `owner.choice=payments`, but
produced small non-zero probability / score / confidence changes.

Observed maxima versus `packed-canonical`:

- outage absolute probability delta: **0.0104**
- owner max per-option absolute delta: **0.0084**
- owner JSD (base 2): **0.0004402163**
- owner confidence delta: **0.0241**
- severity reported score delta: **0.0364**
- severity expected-score delta: **0.0365**
- severity max per-bin delta: **0.0333**
- severity JSD (base 2): **0.0009390752**
- severity confidence delta: **0.0318**
- top-choice flips: **0**

Interpretation: question mapping order is an observed experimental variable for
this packed request. These data are consistent with the prior concern that
packed questions should not be assumed independent or permutation invariant.

## Packed vs single-question probes

Compared with the same answer in `packed-canonical`:

- `single-outage`
  - noul: `0.9612` vs `0.9403`
  - absolute delta: **0.0209**
- `single-owner`
  - owner remained `payments`
  - max per-option delta: **0.0013**
  - JSD: **0.00001955**
  - confidence delta: **0.0040**
- `single-severity`
  - score: `2.6630` vs `2.6487`
  - reported-score delta: **0.0143**
  - expected-score delta: **0.0142**
  - max per-bin probability delta: **0.0692**
  - JSD: **0.0068248272**
  - confidence delta: **0.0392**

For severity, the scalar score moved only modestly while the underlying
distribution moved much more. Treating only the reported scalar as the decision
signal would therefore hide a material packing-sensitive calibration shift in
this fixture.

## Interpretation boundary

This is one incident fixture under one hosted alias at one observation window.

It supports:
- keeping question packing/order in experiment provenance;
- preserving raw probability distributions rather than only chosen labels or
  scalar scores;
- treating packed-vs-single parity as an empirical property, not an API-contract
  guarantee.

It does not establish:
- permanent determinism of Workers AI;
- universal choice-order invariance;
- a quality ranking against Jev or another provider;
- hosted/local Clef parity;
- a semantic pass/fail threshold for acceptable sensitivity.

## Raw Evidence bundle

`clef-phase1a-hosted-v0.1.bundle.json.gz.b64` is a gzip-compressed,
Base64-encoded compact Evidence bundle containing all 14 exact provider response
bodies as `raw_response_base64`, frozen request/wire hashes, run metadata, and
the analysis object.

Integrity:

- decoded gzip SHA-256:
  `eeb859a44b0514b022e160132a9d6c973a15a47bae27447635006aaa4028d18c`
- Base64 text SHA-256:
  `b2078081cde2d3e7f352c06ee96856561056707bb4d1115849c0277c16bcf75c`
- uncompressed compact JSON SHA-256:
  `181385f4588b08aa53fc600962e6bd996b864d899ed4d291fd881e1e54006164`

Example reconstruction:

```bash
base64 -d clef-phase1a-hosted-v0.1.bundle.json.gz.b64 |
  gzip -d > clef-phase1a-hosted-v0.1.bundle.json
```

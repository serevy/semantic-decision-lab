# Clef-Flash Phase 1B hosted v0.1 — Evidence summary

## Run identity

- Workflow run: `37205657656`
- Workflow head: `2c98622338a19f09a7926e6dcf05533a59d48a80`
- Artifact ID: `11304537926`
- Artifact digest: `sha256:3cef7569014381bd33574657e892b5f1034f29281fd6c917fe0ce6b2f9752629`
- Frozen manifest SHA-256: `b4868b760af95b080d8848db7cfe5e610eb1bf6cca110b805c89b14105a9c23a`
- Provider: `cloudflare-workers-ai`
- Model alias: `@cf/cloudflare/clef-flash`
- Hosted immutable model revision: unavailable
- Provider calls: **42 / 42**
- HTTP / transport failures: **0**
- Contract failures: **0**
- Request / wire hash drift: **0**

Phase 1B replayed the exact 14 Phase 1A variants across three new incident-state
fixtures while keeping the typed question contract unchanged.

## Replication summary

All three new fixtures reproduced the two main Phase 1A order observations:

- choice-order exact-zero semantic metric delta: **3 / 3 fixtures**;
- question-order non-zero metric delta: **3 / 3 fixtures**;
- question-order owner top-choice flips: **0**.

Combined with the original Phase 1A fixture, the current hosted observation set is:

- choice-order exact-zero semantic metrics: **4 / 4 frozen fixtures**;
- question-order non-zero metrics: **4 / 4 frozen fixtures**;
- question-order owner top-choice flips: **0** across these fixtures.

The three Phase 1B packed baselines also selected all three owner regions:
`payments`, `storefront`, and `support`.

## Fixture observations

### payments-partial

Packed baseline:

- outage / noul: `0.0242`
- owner: `payments` with probability `0.9775`
- severity score: `1.0065`

Question-order maxima:

- outage probability delta: `0.0051`
- owner max per-option delta: `0.0085`
- owner confidence delta: `0.0245`
- severity score delta: `0.0058`
- severity max-bin delta: `0.0088`
- severity confidence delta: `0.0217`

Packed vs single:

- outage probability delta: `0.0072`
- owner max per-option delta: `0.0032`
- severity score delta: `0.0411`
- severity max-bin delta: `0.0362`
- severity confidence delta: `0.0865`

### storefront-hard

Packed baseline:

- outage / noul: `0.8265`
- owner: `storefront` with probability `0.9892`
- severity score: `2.2716`

Question-order maxima:

- outage probability delta: `0.0296`
- owner max per-option delta: `0.0033`
- owner confidence delta: `0.0098`
- severity score delta: **`0.1212`**
- severity max-bin delta: `0.0652`
- severity confidence delta: `0.0470`

Packed vs single:

- outage probability delta: **`0.0833`**
- owner max per-option delta: `0.0037`
- severity score delta: **`0.1165`**
- severity max-bin delta: **`0.0959`**
- severity confidence delta: `0.0046`

### support-info

Packed baseline:

- outage / noul: `0.0653`
- owner: `support` with probability `0.9835`
- severity score: `0.9616`

Question-order maxima:

- outage probability delta: **`0.0530`**
- owner max per-option delta: `0.0025`
- owner confidence delta: `0.0072`
- severity score delta: `0.0139`
- severity max-bin delta: `0.0252`
- severity confidence delta: `0.0548`

Packed vs single:

- outage probability delta: `0.0376`
- owner max per-option delta: `0.0053`
- severity score delta: `0.0404`
- severity max-bin delta: `0.0259`
- severity confidence delta: `0.0340`

## Interpretation

The replication strengthens two working conclusions for this hosted alias and
typed-decision shape:

1. question packing/order must remain explicit experiment provenance and must not
   be assumed permutation-invariant;
2. preserving full probability distributions matters, because packing-sensitive
   movement can be larger in the distribution than the final label or scalar
   alone suggests.

Choice-key order remained exactly invariant at the frozen metric level across all
four fixtures observed so far, including baselines that selected payments,
storefront, and support. This is useful evidence but is **not promoted to a
universal contract guarantee**.

The evidence does not establish:

- permanent determinism of the moving Workers AI alias;
- universal choice-order invariance;
- hosted/local Clef parity;
- a provider-quality ranking;
- a semantic pass/fail threshold for acceptable sensitivity.

These results reinforce the existing PDDR-0003 boundary rather than requiring a
new durable decision.

## Raw Evidence bundle

`clef-phase1b-hosted-v0.1.bundle.json.gz.b64` is a gzip-compressed,
Base64-encoded compact Evidence bundle containing:

- all 42 exact provider response bodies as `raw_response_base64`;
- request and wire hashes;
- run identity and artifact identity;
- all 42 exact provider response bodies and their request/wire hashes.

The full analysis summary remains separately preserved in `clef-phase1b-hosted-v0.1-analysis-summary.json`.

Integrity after repair:

- decoded gzip SHA-256:
  `c306d9c804ec22541b96ca601da1bc7dfee00297b343fcbe7c74ec91674911ea`
- Base64 text SHA-256:
  `af1a25d3ffe16132c6f6a2b2585fe165a2c11e82c065a1b6d207ae05854ccfe1`
- uncompressed compact JSON SHA-256:
  `5329baffb357cca3caf4a4df540dce023c7c2fe89462b0e8ddc7d76a55225edb`

Repair provenance:

- the previously retained bundle was found during PR #131 review to fail gzip CRC validation;
- this replacement was reconstructed from GitHub Actions Artifact `11304537926`;
- the downloaded artifact SHA-256 was rechecked against the frozen digest
  `3cef7569014381bd33574657e892b5f1034f29281fd6c917fe0ce6b2f9752629`;
- all **42 / 42** decoded raw response bodies matched their recorded
  `raw_response_sha256` before this replacement was written;
- the repaired repository Evidence independently reproduces the Phase 1B -> Phase 1C
  raw-response SHA-256 comparison at **18 / 18**.

Example reconstruction:

```bash
base64 -d clef-phase1b-hosted-v0.1.bundle.json.gz.b64 |
  gzip -d > clef-phase1b-hosted-v0.1.bundle.json
```

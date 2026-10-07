# Clef-Flash Phase 2B local v0.2 — source localization

## Outcome

The corrected Phase 2B v0.2 local run completed successfully and preserved the
frozen source-localization experiment.

- freeze commit: `c837061ca02508d0dd1272f9be4e367cacbabf77`
- run identity: `clef-phase2b-local-v0.2`
- model revision: `17f0b0ad64efb65d273590632833508766b2aae6`
- runtime: A100-SXM4-80GB / BF16 / torch 2.11.0+cu130 / transformers 5.10.2 / CUDA 13.0
- provider: local inference via `joint_schema_model.py:systemone`
- actual traced conditions: **18 / 18**
- fixed-backbone head-only counterfactuals: **15 / 15**
- Evidence JSON files: **35**
- stage validated: **35 / 35**

The A100 runtime remains an explicit non-H100/H200 hardware condition.

## Cross-phase reproduction

All 18 Phase 2B actual responses matched the retained Phase 2A repeat-1
response hashes:

- Phase 2A repeat-1 response-hash matches: **18 / 18**

This comparison is descriptive and is not an execution gate.

## Encoding invariants

Semantic token identity was preserved while question placement moved:

- state token hash mismatches: **0**
- state span mismatches: **0**
- question instruction token hash mismatches: **0**
- option semantic token hash mismatches: **0**
- question absolute span changes: **39**
- option absolute span changes: **117**

## Released-path probability deltas

Across the 15 non-canonical actual request variants, the maximum per-condition
probability delta versus the canonical request was:

- min: `0.006627202033996582`
- mean: `0.033776309713721274`
- max: `0.0670178234577179`

## Fixed-backbone head-only control

With the canonical backbone hidden states held fixed and only the
`EncodedRecord.questions` tuple order changed, all 15 counterfactuals produced
zero probability delta:

- min: `0.0`
- mean: `0.0`
- max: `0.0`

This weakens tuple-order-alone explanations in the released head. It does not
prove a specific backbone attention or positional mechanism.

## Backbone localization

The frozen trace shows:

- state backbone raw max delta: `0.0`
- state backbone normalized max delta: `0.0`
- lexical option max delta: `0.0`
- global backbone raw max delta: `4.0`
- global backbone normalized max delta: `4.375`
- question backbone raw max delta: `4.91015625`
- question backbone normalized max delta: `3.69921875`
- option-context raw max delta: `20.453125`
- option-context normalized max delta: `11.658203125`

The observations are consistent with question placement changing contextual
backbone representations before the released head produces the final
probabilities. Phase 2B does not assign causality to a specific attention,
position, serialization, or other backbone mechanism.

## Interpretation boundary

- No semantic, numerical-noise, or causality threshold was frozen before output.
- The fixed-backbone head-only control is synthetic and is not a provider request.
- Zero head-only delta weakens tuple-order-alone explanations but does not prove a
  specific backbone mechanism.
- Phase 2A response-hash comparison is descriptive.
- Non-H100/H200 hardware remains a distinct runtime condition.

## Preserved files

- `clef-phase2b-local-v0.2-summary.md`
- `clef-phase2b-local-v0.2-analysis.json`
- `clef-phase2b-local-v0.2-evidence.tgz`

The raw archive is the exact successful Google Drive Evidence archive containing
`run.json`, `canary.json`, 18 actual trace JSON files, and 15 head-only
counterfactual JSON files.

Integrity:

- raw archive SHA-256:
  `683abcbc77c32f689c812b2eb763101002962bc0ef8fd99f18ce57de927e54e7`
- analysis SHA-256:
  `2e54ec9635cd4ddaab54be861b6ebe289096549869d10d5c5751d6bdc5431ad8`

## PDDR checkpoint

No new PDDR is proposed by this evidence preservation change.

The result strengthens the provider/runtime assurance research direction and
motivates a separately frozen follow-up if deeper backbone mechanism isolation is
pursued.

Refs #118, #135, #136, #138.

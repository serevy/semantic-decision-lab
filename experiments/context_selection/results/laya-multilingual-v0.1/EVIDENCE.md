# Laya multilingual v0.1 evidence

This directory freezes the first valid Laya multilingual provider run for Experiment #2.

## Run identity

- source repository: `NandhaKishorM/laya`
- source revision: `42626c348753fbb17572a813127df2278a1ec527`
- model repository: `convaiinnovations/laya-multilingual`
- model revision: `4bb4d65403a3a7b8abd9e6876ccb5e75cf923b5c`
- model.safetensors SHA-256: `9d628fd971b700382ac6f65920a86f149777b2e748e0c955fb3b19695aa8f204`
- device: `cuda`
- dtype: `torch.float16`
- inference max_len: **4096**
- head_max_len: **256**
- top-k: **2**
- observed_at_utc: `2026-09-21T16:27:15.893978+00:00`

The checkpoint temperatures were used as shipped. No calibration was fitted on
the three frozen PDDR cases.

## Input validity

The exact pinned Laya token-packing preflight checked all 21 case/record inputs:

- complete task/question preserved: **21/21**
- all three criteria preserved: **21/21**
- complete PDDR state preserved: **21/21**
- state truncation: **0**
- option truncation: **0**
- marker count: **3** for every request
- same PDDR under different tasks produced distinct final input hashes: **all 7 records**

This run is therefore treated as a valid provider run, not an adapter or
context-packing failure.

## Result

| case | required PDDR | selected Top-2 | required rank | required recall |
| --- | --- | --- | ---: | ---: |
| ctx-001 | PDDR-0002 | PDDR-0005, PDDR-0006 | 7 | 0.0 |
| ctx-002 | PDDR-0006 | PDDR-0005, PDDR-0006 | 2 | 1.0 |
| ctx-003 | PDDR-0007 | PDDR-0005, PDDR-0006 | 6 | 0.0 |

Required hit rate: **1/3**.

All three cases selected the same Top-2 pair, `PDDR-0005` and `PDDR-0006`.
The required-probability ordering was also identical across the three tasks:
`0005 > 0006 > 0004 > 0001 > 0003 > 0007 > 0002`.

All cases use the shared Top-2 cutoff, so the context reduction ratio is
**71.4%** for every case.

These observations describe this frozen three-case run only. They are not a
general ranking of Laya against other providers.

## Artifact integrity

The uploaded first-run ZIP is committed as `raw-results.zip`.

ZIP SHA-256:

`32408681c2557276e229f0bd3d04273add97741663d3a3fadf991ae06a0e27de`

Contained file SHA-256 values:

- `provider-results.json`: `c2ba5149323ef608894a73ccaedbdfd678035843384aa731143cfe1ef73df508`
- `provenance.json`: `861c83f294efbd6b4feb4872b632e32179f24aa851e72b71804ccca6df0f589f`
- `metrics.json`: `e9b4ff935679663dbbe86b506259e2d4e29b40f5c1b29d3071782fc323e9b608`
- `input-preflight.json`: `78cd211862fd98eaff1d2dd29c71f99dac6126e0028e71aa7540079aa50b827e`
- `selections.json`: `c7f764695b285916cd281b4f20453eb75413912755eee988a524c17581123c4d`

The small summary JSON files are also committed directly for quick inspection.
The ZIP is the byte-preserving source artifact containing all five raw files.

No end-to-end latency metric is claimed here; the runner did not write a timing
measurement into the result artifact.

Do not overwrite this evidence. Any prompt, checkpoint, packing, context,
calibration, or selection-policy change requires a new experiment version.

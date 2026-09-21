# Zefan Open-Jev 2B v0.1 evidence

This directory freezes the first valid Zefan Open-Jev 2B provider run for
Experiment #2.

## Run identity

- source repository: `Zefan-Cai/Open-Jev`
- source revision: `ed45657bf726c3b77408942830e5578f99df904e`
- model repository: `ZefanCai/Open-Jev-2B`
- model revision: `0c7aa498b1627be8da4acf34c863ff0ee0a92785`
- base model: `Qwen/Qwen3.5-2B`
- base revision: `15852e8c16360a2fea060d615a32b45270f8a8fc`
- packaged checkpoint SHA-256:
  `3076462e6356412082e79af909227b39b2863b90def79155ca0821aa506b7ded`
- saved temperature: `1.518796342858676`
- device: NVIDIA L4 / CUDA
- upstream BF16 loader preserved
- inference max_length: **4096**
- batch_size: **1**
- prefix cache: **off**
- top-k: **2**
- observed_at_utc: `2026-09-21T19:24:17.228971+00:00`

No training, calibration fitting, prompt tuning, or selection-policy change was
performed after observing provider output.

## Input validity

The exact pinned upstream request compiler / candidate renderer plus pinned Qwen
tokenizer/chat template checked all 21 case/record classifications and all 63
candidate sequences before inference:

- complete task preserved: **63/63**
- complete PDDR state preserved: **63/63**
- candidate text preserved: **63/63**
- every candidate <= 4096 encoded tokens
- same PDDR under the three tasks produced distinct combined input hashes:
  **all 7 records**

The server then reported the frozen checkpoint digest, base revision, source
commit, max length, LoRA decision-head method and disabled prefix cache.

This run is therefore treated as a valid provider run, not an adapter,
context-packing, or runtime-identity failure.

## Result

| case | required PDDR | selected Top-2 | required rank | required recall |
| --- | --- | --- | ---: | ---: |
| ctx-001 | PDDR-0002 | PDDR-0007, PDDR-0001 | 3 | 0.0 |
| ctx-002 | PDDR-0006 | PDDR-0003, PDDR-0007 | 4 | 0.0 |
| ctx-003 | PDDR-0007 | PDDR-0001, PDDR-0003 | 3 | 0.0 |

Required hit rate: **0/3**.

Unlike the Laya multilingual v0.1 run, the three tasks produced different Top-2
sets and different required-probability orderings. That observation only shows
task sensitivity in this small frozen sample; it does not establish better
context-selection quality.

All cases use the shared Top-2 cutoff, so the context reduction ratio is
**71.4%** for every case.

Recorded provider inference time across the 21 classifications was
**19.315545415 seconds**. This excludes setup/model-download time.

These observations describe this frozen three-case run only. They are not a
general conclusion about Open-Jev 2B or Qwen3.5-2B.

## Artifact integrity

The uploaded first valid-run ZIP is committed as `raw-results.zip`.

ZIP SHA-256:

`251163e3d9a82d00252af315415c49c119bef728ffb35efb3f76d3c1e95fa690`

Contained file SHA-256 values:

- `provenance.json`: `0ab3c43aa6dab96ab5aab934f94196c7ea5ae3095ff75fefd216d203cbbaa500`
- `provider-results.json`: `3dc66503e3630c3ac31278ed49945aedbe8279acc155673ad897e5071c24a101`
- `input-preflight.json`: `737594b64a08ff14fb27ea384704b5a505cfdb21e73eaf7d627a353fddf37d02`
- `selections.json`: `ec69a388d103274470c288e96837011aab8f4c9f8ef7b35553dcf2ac9b9c84d9`
- `metrics.json`: `225bba3c6fa0cc355ae684ce3cfdb0f8397014f4c132414165eeb1c58b5d93f5`

The small summary JSON files are also committed directly for quick inspection.
The ZIP is the byte-preserving source artifact containing all five raw files.

Do not overwrite this evidence. Any prompt, checkpoint, dtype, packing, caching,
calibration, context, or selection-policy change requires a new experiment
version.

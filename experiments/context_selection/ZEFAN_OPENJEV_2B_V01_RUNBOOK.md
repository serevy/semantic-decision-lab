# Zefan Open-Jev 2B v0.1 runbook

This runbook freezes the first `Zefan-Cai/Open-Jev` 2B provider run for
Experiment #2 before observing any provider output.

## Frozen identity

- source: `Zefan-Cai/Open-Jev`
- source revision: `ed45657bf726c3b77408942830e5578f99df904e`
- model: `ZefanCai/Open-Jev-2B`
- model revision: `0c7aa498b1627be8da4acf34c863ff0ee0a92785`
- base model: `Qwen/Qwen3.5-2B`
- base revision: `15852e8c16360a2fea060d615a32b45270f8a8fc`
- packaged checkpoint SHA-256:
  `3076462e6356412082e79af909227b39b2863b90def79155ca0821aa506b7ded`
- saved temperature: `1.518796342858676`
- inference max_length: **4096**
- batch_size: **1**
- prefix cache: **off**
- shared selection cutoff: **Top-2**

No training or calibration fitting is performed.

## Hardware

The pinned upstream implementation loads the Qwen backbone as BF16. The first
run therefore requires a CUDA device for which
`torch.cuda.is_bf16_supported()` is true.

The runner refuses a T4 rather than modifying upstream dtype behavior. In Colab,
select an L4, A100, or another BF16-capable runtime.

## Packing preflight

Each PDDR is evaluated independently. The upstream `compile_request` and
`candidate_prompts` code produces three candidate sequences for the relevance
Choice.

The exact pinned Qwen tokenizer and chat template are then used before model
inference. All 63 candidate sequences must:

- contain the exact frozen task
- contain the complete PDDR state
- contain the expected candidate text
- remain at or below 4096 encoded tokens

The combined final-input hash for the same PDDR must differ across the three
tasks.

## Runtime identity

Every real provider response must report the frozen checkpoint digest, base
revision, max_length, source code commit, LoRA decision-head method, and disabled
prefix cache. Any mismatch aborts the run.

## Colab

Open `zefan_openjev_2b_v0_1_colab.ipynb` on a BF16-capable GPU and run the
single code cell.

A successful run produces:

`/content/zefan-open-jev-2b-v0.1-results.zip`

Only after the ZIP is created, the runner uninstalls Open-Jev and deletes its
temporary source checkout, adapter package and dedicated Hugging Face cache.
The evidence ZIP and Semantic Decision Lab checkout remain.

Do not tune prompt, checkpoint, dtype, max length, batching, caching,
calibration, or Top-2 after observing results without a new experiment version.

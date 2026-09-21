# Laya multilingual v0.1 runbook

This runbook freezes the first Laya multilingual provider run for Experiment #2
before observing any provider output.

## Frozen identity

- source: `NandhaKishorM/laya`
- source revision: `42626c348753fbb17572a813127df2278a1ec527`
- model: `convaiinnovations/laya-multilingual`
- model revision: `4bb4d65403a3a7b8abd9e6876ccb5e75cf923b5c`
- model.safetensors SHA-256:
  `9d628fd971b700382ac6f65920a86f149777b2e748e0c955fb3b19695aa8f204`
- checkpoint default max_len: 1024
- inference max_len: **4096**
- head_max_len: **256**
- shared selection cutoff: **Top-2**

The checkpoint ships with temperature 1.0 and no option-count temperatures.
This experiment uses that state as-is. It does not fit calibration on the
three frozen PDDR cases.

## Packing

Each PDDR is evaluated independently:

- state: the complete PDDR markdown record
- question: current task + PDDR ID + relevance instruction
- Choice labels: required / useful / irrelevant

Before model inference, the exact pinned Laya `build_sequence` implementation
must verify all 21 case/record inputs preserve the complete question, all three
criteria, and the complete PDDR state with three marker positions.

## Colab

Open `laya_multilingual_v0_1_colab.ipynb` in a T4 runtime and run the single
code cell. The one-shot runner clones the pinned Laya source, downloads the
pinned published checkpoint, verifies its SHA-256, runs the preflight, runs the
experiment, and packages the first result evidence as:

`/content/laya-multilingual-v0.1-results.zip`

Do not tune the prompt, checkpoint, max length, calibration, or Top-2 after
observing results without creating a new experiment version.

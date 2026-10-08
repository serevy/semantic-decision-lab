# Clef-Flash Phase 2C — Colab execution handoff

This document is an **execution helper only**. It does not change the frozen
Phase 2C protocol, runner, manifest, intervention matrix, or interpretation
boundary.

The first Phase 2C model output must be produced from the exact merged freeze:

```text
semantic-decision-lab
commit 7ef54c5e6cec348abb0007cd066741283a382f29
Cloudflare/clef-flash
revision 17f0b0ad64efb65d273590632833508766b2aae6
```

Do **not** execute the first Phase 2C run from a later moving `main` revision.

## Frozen execution envelope

Phase 2C contains:

- one provider-neutral canary;
- 18 standard-position conditions;
- 18 zero-position conditions;
- 6 canonical suffix-position-shift conditions;
- 42 experimental backbone forwards total;
- suffix offsets `+32` and `+128`;
- one loaded model;
- no in-run retries.

The run identity is frozen as:

```text
clef-phase2c-local-v0.1
```

No semantic, numerical-noise, sufficiency, necessity, or causality threshold
was selected before output.

## GPU target

Prefer:

- H100 / H200 — upstream-matched hardware class;
- A100 80 GB — preferred fallback and matches the successful Phase 2B local
  hardware class;
- A100 40 GB or another BF16-capable CUDA GPU may be attempted only as an
  explicit different hardware condition.

If the assigned GPU cannot run the frozen protocol, **stop and preserve the
failure**. Do not add quantization, CPU offload, a different dtype, or another
model path to make it fit.

## 1. Confirm the accelerator before installing anything

```bash
!nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
!df -h /content
```

If the GPU is unsuitable, stop before producing model output.

## 2. Clone the exact merged freeze

```bash
!rm -rf /content/semantic-decision-lab
!git clone https://github.com/serevy/semantic-decision-lab.git /content/semantic-decision-lab
%cd /content/semantic-decision-lab
!git checkout --detach 7ef54c5e6cec348abb0007cd066741283a382f29
!git rev-parse HEAD
!git status --short
```

Expected:

- HEAD is exactly
  `7ef54c5e6cec348abb0007cd066741283a382f29`;
- worktree is clean.

## 3. Install the frozen runtime family

Phase 2C keeps the Phase 2A/2B runtime family:

- torch 2.11.x;
- transformers exactly 5.10.2;
- CUDA;
- BF16;
- no quantization;
- no CPU offload.

```python
%pip install --upgrade "torch>=2.11,<2.12" "transformers==5.10.2" huggingface_hub safetensors accelerate pillow
```

Verify before the run:

```python
import torch
import transformers

print("torch:", torch.__version__)
print("transformers:", transformers.__version__)
print("cuda:", torch.version.cuda)
print("gpu:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
print("bf16:", torch.cuda.is_bf16_supported() if torch.cuda.is_available() else False)

assert str(torch.__version__).startswith("2.11")
assert transformers.__version__ == "5.10.2"
assert torch.cuda.is_available()
assert torch.cuda.is_bf16_supported()
```

The Phase 2C runner independently repeats the relevant runtime gates.

## 4. Run the frozen credential-free dry-run first

This produces **no model decision output** and downloads no model weights.

```python
!python experiments/provider_portability/clef/phase2c/run_local.py \
  --dry-run > /content/clef-phase2c-dry-run.json

!python -m json.tool /content/clef-phase2c-dry-run.json > /dev/null

import json

with open("/content/clef-phase2c-dry-run.json", encoding="utf-8") as handle:
    p = json.load(handle)

print("run identity:", p["run_identity"])
print("standard:", p["standard_conditions"])
print("zero-position:", p["zero_position_conditions"])
print("suffix-shift:", p["suffix_shift_conditions"])
print("experimental forwards:", p["experimental_backbone_forwards"])
```

Expected frozen envelope:

```text
run identity: clef-phase2c-local-v0.1
standard: 18
zero-position: 18
suffix-shift: 6
experimental forwards: 42
```

Also confirm the pinned model revision directly from the manifest:

```python
import json

with open(
    "experiments/provider_portability/clef/phase2c/mechanism-isolation-manifest.v0.1.json",
    encoding="utf-8",
) as handle:
    m = json.load(handle)

print(m["model"]["hf_revision"])
assert m["model"]["hf_revision"] == "17f0b0ad64efb65d273590632833508766b2aae6"
assert m["phase2c_model_outputs_observed_before_freeze"] == 0
```

If any value differs, stop.

## 5. Execute the first Phase 2C local run

Use the exact frozen run identity as the fresh output directory name:

```python
!python experiments/provider_portability/clef/phase2c/run_local.py \
  --output-dir /content/clef-phase2c-local-v0.1
```

The runner will:

1. resolve the exact Hugging Face revision;
2. download that exact snapshot;
3. record released code/head hashes and runtime identity;
4. load one BF16 CUDA model instance;
5. preflight and reserve the canary Evidence;
6. preserve `canary-error` before propagation for inference, validation, or
   truncation failure;
7. only after a validated canary, execute the frozen 18 standard conditions;
8. execute the frozen 18 zero-position controls;
9. execute the frozen 6 canonical suffix-shift controls;
10. preserve per-condition Evidence before validation;
11. stop on failure without an in-run retry.

A failed run is still Evidence.

## 6. Inspect terminal run state before interpretation

Do not inspect selective probabilities first. Check the run envelope first.

```python
import json
from pathlib import Path

root = Path("/content/clef-phase2c-local-v0.1")

with open(root / "run.json", encoding="utf-8") as handle:
    run = json.load(handle)

print("stage:", run["stage"])
print("observed counts:", run.get("observed_counts"))
print("runtime:", run.get("runtime"))
```

A fully completed run should reach:

```text
stage: validated
observed_counts:
  standard: 18
  zero_position: 18
  suffix_shift: 6
  experimental_backbone_forwards: 42
```

If the run failed, do not modify code/packages and rerun into the same
directory.

## 7. Preserve Evidence before analysis, interpretation, or retry

Archive the complete first-run directory immediately:

```bash
!tar -C /content -czf /content/clef-phase2c-local-v0.1-evidence.tgz clef-phase2c-local-v0.1
!sha256sum /content/clef-phase2c-local-v0.1-evidence.tgz
```

The archive **must be copied outside the Colab VM before analysis,
interpretation, retry, or ending the session**. A copy that exists only under
`/content` is not considered preserved Evidence.

Google Drive is the default off-VM destination:

```python
from google.colab import drive
drive.mount("/content/drive")
```

```bash
!mkdir -p /content/drive/MyDrive/semantic-decision-lab-evidence
!cp /content/clef-phase2c-local-v0.1-evidence.tgz \
  /content/drive/MyDrive/semantic-decision-lab-evidence/
!sha256sum /content/drive/MyDrive/semantic-decision-lab-evidence/clef-phase2c-local-v0.1-evidence.tgz
```

The copied archive SHA-256 **must exactly match** the original archive SHA-256.

If Google Drive is unavailable, use another durable destination outside the
Colab VM (for example, download the archive to the operator machine) and verify
the same SHA-256 there. Record which external destination was used.

**STOP gate:** do not begin analysis, inspect selective model results, change
code/packages, retry, or intentionally terminate the Colab session until at
least one off-VM copy exists and its SHA-256 has been verified.

## 8. Analysis boundary

The analysis axes were frozen before output in
`phase2c/analysis_plan.py`:

- max probability delta;
- state-backbone raw max absolute delta;
- global-backbone raw max absolute delta;
- question-backbone raw max absolute delta;
- option-context raw max absolute delta.

All semantic, numerical-noise, sufficiency, necessity, and causality thresholds
remain `None`.

The repository's current `phase2c/analyze.py` freezes the analysis contract; it
does not silently add a post-output decision threshold.

**Preserve the raw Evidence archive first.** Any later analysis implementation
must use the already-frozen axes and must not rewrite the first-run Evidence.

## Interpretation boundary

Bounded interpretations only:

- persistence of question-order deltas under zero position IDs weakens the
  hypothesis that ordinary varying position IDs are necessary;
- movement under canonical suffix-only position shifts shows only that the
  positional channel can be sufficient under that synthetic control;
- either control may be off-distribution;
- neither result alone proves one exclusive mechanism behind the real
  question-order effect;
- a null result is valid Evidence.

Refs #81, #118, #140, #141, #142.

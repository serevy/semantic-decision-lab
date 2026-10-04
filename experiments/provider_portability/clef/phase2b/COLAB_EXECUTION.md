# Clef-Flash Phase 2B — Colab execution handoff

This document is an **execution helper only**. It does not change the frozen
Phase 2B protocol.

The first Phase 2B internal trace must be produced from the exact freeze:

```text
semantic-decision-lab
commit 08c16640320805aeaad7942079dfbe87ea8f8d7a
Cloudflare/clef-flash
revision 17f0b0ad64efb65d273590632833508766b2aae6
```

Do not execute the first Phase 2B trace from a later moving `main`.

## 1. Confirm or restore the frozen runtime family

Phase 2B keeps the Phase 2A runtime family:

- CUDA;
- BF16;
- torch 2.11.x;
- transformers 5.10.2;
- no quantization;
- no CPU offload;
- max length 16384.

Check the assigned GPU first:

```bash
!nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
```

Then verify Python packages:

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

If the runtime was reset, reinstall the same frozen family before continuing:

```python
%pip install --upgrade "torch>=2.11,<2.12" "transformers==5.10.2" huggingface_hub safetensors accelerate pillow
```

Restart the runtime only if Colab requests it, then re-run the verification.

## 2. Check out the exact Phase 2B freeze

Reuse the existing clone if it is still present:

```bash
!test -d /content/semantic-decision-lab/.git || git clone https://github.com/serevy/semantic-decision-lab.git /content/semantic-decision-lab
%cd /content/semantic-decision-lab
!git fetch origin
!git checkout --detach 08c16640320805aeaad7942079dfbe87ea8f8d7a
!git rev-parse HEAD
!git status --short
```

Expected HEAD:

```text
08c16640320805aeaad7942079dfbe87ea8f8d7a
```

The worktree must be clean.

## 3. Keep Evidence on Google Drive

Mount Drive if needed:

```python
from google.colab import drive
drive.mount("/content/drive")
```

Prepare the parent directory:

```bash
!mkdir -p /content/drive/MyDrive/clef-research
```

The first run identity is:

```text
/content/drive/MyDrive/clef-research/clef-phase2b-local-v0.1
```

Do not reuse that directory after any failure.

## 4. Run the credential-free dry-run

```python
!python experiments/provider_portability/clef/phase2b/run_local.py \
  --dry-run > /content/clef-phase2b-dry-run.json

!python -m json.tool /content/clef-phase2b-dry-run.json > /dev/null

import json
with open("/content/clef-phase2b-dry-run.json", encoding="utf-8") as handle:
    p = json.load(handle)

print("revision:", p["hf_revision"])
print("fixtures:", p["fixture_count"])
print("orders:", p["question_order_count"])
print("conditions:", p["condition_count"])
print("actual backbone forwards:", p["actual_backbone_forwards"])
print("total backbone forwards including canary:", p["total_backbone_forwards_including_canary"])
print("head-only counterfactuals:", p["head_only_counterfactuals"])
```

Expected frozen envelope:

```text
revision: 17f0b0ad64efb65d273590632833508766b2aae6
fixtures: 3
orders: 6
conditions: 18
actual backbone forwards: 18
total backbone forwards including canary: 19
head-only counterfactuals: 15
```

Stop if any value differs.

## 5. Execute the first Phase 2B traced run

Confirm the Evidence directory does not already exist:

```bash
!test ! -e /content/drive/MyDrive/clef-research/clef-phase2b-local-v0.1
```

Then run:

```python
!python experiments/provider_portability/clef/phase2b/run_local.py \
  --output-dir /content/drive/MyDrive/clef-research/clef-phase2b-local-v0.1
```

The runner records:

- one provider-neutral canary;
- 18 actual traced question-order conditions;
- encoded semantic spans;
- state / global / question / option backbone descriptors;
- lexical option-vector descriptors;
- released-head logits and probabilities;
- 15 fixed-backbone head-only counterfactuals;
- source Git blob SHAs and model/head/runtime provenance.

Intermediate and failure Evidence is written before validation where relevant.
There are no in-run retries.

## 6. Analyze only after `run.json` reaches `stage: validated`

```python
from pathlib import Path
import json

run_path = Path(
    "/content/drive/MyDrive/clef-research/"
    "clef-phase2b-local-v0.1/run.json"
)
run = json.loads(run_path.read_text(encoding="utf-8"))

print("stage:", run["stage"])
print("actual:", run.get("completed_actual_conditions"))
print("head-only:", run.get("completed_head_only_counterfactuals"))
print("gpu:", run["runtime"]["gpu"])
print("revision:", run["hf_revision"])
```

Expected completion counts are 18 actual and 15 head-only.

Then analyze:

```python
!python experiments/provider_portability/clef/phase2b/analyze.py \
  --results-dir /content/drive/MyDrive/clef-research/clef-phase2b-local-v0.1 \
  --output /content/drive/MyDrive/clef-research/clef-phase2b-local-v0.1-analysis.json

!python -m json.tool \
  /content/drive/MyDrive/clef-research/clef-phase2b-local-v0.1-analysis.json \
  > /dev/null
```

The analyzer refuses to overwrite an existing report.

## 7. Archive before interpretation or retry

Whether the traced run succeeds or fails, preserve it before changing code,
packages, GPU, or retrying.

```bash
!tar -C /content/drive/MyDrive/clef-research \
  -czf /content/drive/MyDrive/clef-research/clef-phase2b-local-v0.1-evidence.tgz \
  clef-phase2b-local-v0.1

!sha256sum /content/drive/MyDrive/clef-research/clef-phase2b-local-v0.1-evidence.tgz
```

If analysis exists:

```bash
!sha256sum /content/drive/MyDrive/clef-research/clef-phase2b-local-v0.1-analysis.json
```

A failed run is still Evidence. Any retry must use a new output identity, for
example `clef-phase2b-local-v0.2`.

## Interpretation boundary

Do not infer a mechanism from one number.

The frozen analyzer distinguishes:

- semantic token identity vs absolute placement;
- state/global/question/option backbone representation deltas;
- lexical option-vector deltas;
- released-path probability deltas;
- fixed-backbone head-only tuple-order deltas.

The head-only condition is synthetic and is not a provider request. No semantic,
numerical-noise, or causality threshold was frozen before output.

# Clef-Flash Phase 2A — Colab execution handoff

This document is an **execution helper only**. It does not change the frozen
Phase 2A protocol.

The first local decision output must be produced from the exact protocol freeze:

```text
semantic-decision-lab
commit 6001ca2763b4c39b18c74ff22bd1326de358ac48
Cloudflare/clef-flash
revision 17f0b0ad64efb65d273590632833508766b2aae6
```

Do not execute from a later moving `main` revision for the first Phase 2A run.

## GPU target

For the first exact run, prefer:

- H100 / H200 — upstream-matched hardware class;
- A100 40 GB or larger — acceptable, but preserved as a different hardware
  condition.

Do not weaken the frozen protocol to make a smaller GPU fit. In particular, do
not add quantization, CPU offload, a different dtype, or a different decision
path.

The model repository is about 19.1 GB before runtime memory, and the released
local path is documented by Cloudflare as tested on one H200.

## 1. Confirm the Colab accelerator before installing anything

```bash
!nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
!df -h /content
```

If the assigned GPU is not suitable, stop before creating provider output.

## 2. Clone the exact frozen experiment revision

```bash
!rm -rf /content/semantic-decision-lab
!git clone https://github.com/serevy/semantic-decision-lab.git /content/semantic-decision-lab
%cd /content/semantic-decision-lab
!git checkout --detach 6001ca2763b4c39b18c74ff22bd1326de358ac48
!git rev-parse HEAD
!git status --short
```

The final two commands should show the frozen commit and a clean worktree.

## 3. Install the frozen runtime family

The protocol requires `torch` 2.11.x and exactly
`transformers==5.10.2`.

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

The Phase 2A runner independently repeats these gates.

## 4. Run the credential-free frozen dry-run first

This produces **no model decision output** and downloads no model weights.

```python
!python experiments/provider_portability/clef/phase2a/run_local.py --dry-run > /content/clef-phase2a-dry-run.json
!python -m json.tool /content/clef-phase2a-dry-run.json > /dev/null

import json
with open("/content/clef-phase2a-dry-run.json", encoding="utf-8") as handle:
    p = json.load(handle)

print("revision:", p["hf_revision"])
print("conditions:", p["condition_count"])
print("scheduled calls:", p["scheduled_calls"])
print("total calls including canary:", p["total_model_calls_if_executed"])
```

Expected frozen envelope:

- revision:
  `17f0b0ad64efb65d273590632833508766b2aae6`;
- 18 conditions;
- 54 scheduled experiment calls;
- 55 total calls including the canary.

If any of those values differ, stop.

## 5. Execute the first Phase 2A local run

Use a fresh output directory. Never overwrite or resume a failed Evidence
directory.

```python
!python experiments/provider_portability/clef/phase2a/run_local.py --output-dir /content/clef-phase2a-local-v0.1
```

The runner will:

1. resolve the exact Hugging Face revision again;
2. download that exact snapshot;
3. record joint-schema code and joint-head hashes;
4. validate CUDA / BF16 / library versions;
5. load one model instance;
6. preflight the canary plus all 18 unique conditions for truncation;
7. execute one contract canary;
8. only after the canary validates, execute the frozen 54-call Phase 1C schedule;
9. preserve per-call Evidence before validation.

There are no in-run retries.

## 6. Analyze against the frozen hosted Phase 1C Evidence

Only after the run reaches `stage: validated`:

```python
!python experiments/provider_portability/clef/phase2a/analyze.py --results-dir /content/clef-phase2a-local-v0.1 --output /content/clef-phase2a-local-v0.1-analysis.json
!python -m json.tool /content/clef-phase2a-local-v0.1-analysis.json > /dev/null
```

The analyzer does not query Workers AI. It reads the repository-pinned Phase 1C
hosted bundle frozen by PR #131.

## 7. Preserve Evidence before interpretation or rerun

Whether the model run succeeds or fails, archive the directory **before**
changing code, packages, GPU, or retrying.

```python
!tar -C /content -czf /content/clef-phase2a-local-v0.1-evidence.tgz clef-phase2a-local-v0.1
!sha256sum /content/clef-phase2a-local-v0.1-evidence.tgz
```

If analysis was produced, preserve it alongside the archive:

```bash
!sha256sum /content/clef-phase2a-local-v0.1-analysis.json
```

A failed run is still Evidence. Use a new output directory for any subsequent
attempt.

## Interpretation boundary

Do not infer a causal mechanism directly from one outcome.

- local question-order sensitivity weakens a hosted-layer-only explanation;
- local invariance while the frozen hosted result remains sensitive increases
  interest in hosted request lowering/runtime differences;
- different local/hosted magnitudes leave multiple model/runtime explanations
  open.

No semantic parity threshold or acceptable delta was frozen before output.

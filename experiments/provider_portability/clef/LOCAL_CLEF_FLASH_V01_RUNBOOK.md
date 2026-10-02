# Clef-Flash local System One smoke v0.1

This runbook is for the **released Clef decision-head path**, not generic chat
generation.

Do not use a `vllm serve ... /v1/chat/completions` result as a substitute for
this first smoke. The released typed-decision implementation is
`joint_schema_model.py` + `joint_head.safetensors`.

## Pre-output freeze gate

Before the first model output:

1. Resolve the current full immutable revision:

   ```python
   from huggingface_hub import model_info
   print(model_info("Cloudflare/clef-flash").sha)
   ```

2. Confirm it starts with the discovery-time prefix `17f0b0a`.
3. Record the full SHA in the Issue / follow-up manifest **before inference**.
4. If the prefix changed, stop and review the upstream diff rather than silently
   running the newer model.

The current repository only stores the discovery-time short revision because
the public model page exposed that prefix during the first anatomy pass.

## Hardware boundary

The model card reports Clef-Flash as a 9B BF16 release and says Cloudflare
tested the local path with torch 2.11 / transformers 5.10.2 on a single H200.

For the first exact run:

- prefer an H100/H200-class environment matching or exceeding the upstream
  memory envelope;
- do not silently quantize, CPU-offload, or change dtype;
- if another GPU is used, record it as a different runtime condition;
- a quantized GGUF/Ollama/LM Studio run belongs in a later runtime-lowering arm.

## Download pinned snapshot

```python
from huggingface_hub import snapshot_download

FULL_SHA = "<recorded-full-sha>"
path = snapshot_download(
    "Cloudflare/clef-flash",
    revision=FULL_SHA,
)
print(path)
```

## Execute the frozen contract fixture

From the repository root:

```bash
python experiments/provider_portability/clef/run_local_clef_flash_smoke.py \
  --snapshot "<snapshot-path>" \
  --output "/tmp/clef-flash-local-v0.1.json"
```

The runner:

- requires the released joint-head artifacts;
- calls `load_release_model(..., device="cuda")`;
- calls the released `systemone(...)` helper;
- keeps the local helper default `max_length=16384`;
- validates the System One response shape;
- records runtime versions, GPU, and hashes of the decision-head code/weights;
- refuses to overwrite an existing evidence file.

The first smoke checks **contract execution**, not semantic quality.

## After the run

Attach/preserve the raw evidence before interpreting it. Then decide separately
whether to add:

- local vs Workers AI probability-delta checks;
- context-length buckets;
- question packing/isolation;
- option-order sensitivity;
- multimodal fixtures;
- Clef 27B.

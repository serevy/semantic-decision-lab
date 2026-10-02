# Clef-Flash local System One smoke v0.1

This runbook is for the **released Clef decision-head path**, not generic chat
generation.

Do not use a `vllm serve ... /v1/chat/completions` result as a substitute for
this first smoke. The released typed-decision implementation is
`joint_schema_model.py` + `joint_head.safetensors`.

## Pre-output freeze gate

Before the first model output, resolve the current full immutable revision:

```python
from huggingface_hub import model_info

full_sha = model_info("Cloudflare/clef-flash").sha
print(full_sha)
```

The full SHA must begin with the discovery-time prefix `17f0b0a`.

1. Record that full SHA in Issue #118 before inference.
2. If the prefix changed, stop and review the upstream diff.
3. Pass the exact 40-character SHA to the runner.

The runner independently enforces the same gate: it rejects short/floating
revisions, rejects a revision outside the approved prefix, resolves the
requested Hugging Face revision again, requires an exact SHA match, and
downloads that exact snapshot before inference.

Changing the approved prefix requires a reviewed repository change rather than
a command-line override.

The first exact smoke also freezes `max_length` at **16,384** in the runner.
There is no command-line override for this value. Any later context-length arm
must use a separately versioned experiment instead of changing this condition.

## Hardware boundary

The model card reports Clef-Flash as a 9B BF16 release and says Cloudflare
tested the local path with torch 2.11 / transformers 5.10.2 on a single H200.

For the first exact run:

- prefer an H100/H200-class environment matching or exceeding the upstream
  memory envelope;
- do not silently quantize, CPU-offload, or change dtype;
- if another GPU is used, record it as a different runtime condition;
- a quantized GGUF/Ollama/LM Studio run belongs in a later runtime-lowering arm.

## Execute the frozen contract fixture

From the repository root:

```bash
python experiments/provider_portability/clef/run_local_clef_flash_smoke.py \
  --hf-revision "<recorded-full-sha>" \
  --output "/tmp/clef-flash-local-v0.1.json"
```

Before loading the 9B model, the runner:

- reserves the evidence destination exclusively;
- validates the frozen System One request;
- verifies and records the immutable Hugging Face revision;
- downloads the exact approved snapshot;
- loads only the processor plus released `joint_schema_model.py` for an
  encoding preflight;
- records original/retained state token counts and the encoded-input hash;
- **rejects the first exact smoke if upstream `encode_record` would truncate
  any state tokens**;
- records Python / torch / transformers / CUDA / GPU before model inference.

Only after those gates pass does it load the released model and call
`systemone(..., max_length=16384)`. It preserves raw/failure evidence before
contract validation and records the loaded model dtype before inference.

The first smoke checks **contract execution**, not semantic quality. A later
long-context/truncation experiment must use a separately versioned condition
instead of weakening this gate.

## After the run

Attach/preserve the evidence regardless of success or failure before
interpreting it. Then decide separately whether to add:

- local vs Workers AI probability-delta checks;
- context-length buckets;
- question packing/isolation;
- option-order sensitivity;
- multimodal fixtures;
- Clef 27B.

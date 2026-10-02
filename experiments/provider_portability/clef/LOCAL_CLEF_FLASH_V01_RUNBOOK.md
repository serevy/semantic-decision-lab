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

The runner:

- reserves the evidence destination before network/model work and refuses a
  concurrent or overwrite attempt;
- verifies and records the full immutable Hugging Face revision before inference;
- downloads the exact approved snapshot itself;
- requires the released joint-head artifacts;
- calls `load_release_model(..., device="cuda")`;
- calls the released `systemone(...)` helper;
- keeps the local helper default `max_length=16384`;
- preserves raw/failure evidence before contract validation;
- records runtime versions, GPU, and hashes of the decision-head code/weights.

The first smoke checks **contract execution**, not semantic quality.

## After the run

Attach/preserve the evidence regardless of success or failure before
interpreting it. Then decide separately whether to add:

- local vs Workers AI probability-delta checks;
- context-length buckets;
- question packing/isolation;
- option-order sensitivity;
- multimodal fixtures;
- Clef 27B.

# Clef-Flash Phase 2A — local / hosted isolation

Phase 2A asks whether the reproducible question-order sensitivity observed in the
Workers AI hosted path also appears in Cloudflare's **released local joint
decision-head path**.

This is an isolation experiment, not a provider-quality benchmark.

## Why this phase exists

Phase 1C established, for the frozen hosted observation window, that identical
wire requests repeated three times produced byte-identical responses while
different question mapping orders produced reproducibly different fixed
responses.

That weakens ordinary hosted call-to-call noise as an explanation, but it does
not isolate the source of the sensitivity to:

- Clef-Flash weights / joint decision head;
- record encoding or tokenization;
- Workers AI request lowering;
- another hosted runtime layer.

Phase 2A moves the same frozen request family to the released local
`joint_schema_model.py:systemone` path.

## Pre-output freeze

No Phase 2A local model output has been observed before this protocol freeze.

The model revision is frozen to:

`Cloudflare/clef-flash@17f0b0ad64efb65d273590632833508766b2aae6`

The phase also pins the Phase 1C manifest, probes, hosted Evidence bundle, hosted
analysis summary, provider-neutral contract, reference canary fixture, and the
existing local smoke runner by Git blob SHA.

## Execution shape

The run loads one model snapshot once.

1. Validate revision, runtime, snapshot files, and all request encodings.
2. Reject any canary or scheduled request that would truncate state.
3. Execute one provider-neutral contract canary.
4. Continue only if the canary passes structural/runtime gates.
5. Replay the **exact Phase 1C 54-call schedule**:
   - 3 fixtures;
   - 6 packed question-order conditions;
   - 3 repeats per condition;
   - the same interleaving order.

The canary has **no semantic quality threshold** and cannot be used to tune the
54-call protocol.

## Frozen runtime boundary

- CUDA execution;
- requested dtype: BF16;
- `torch` 2.11.x;
- `transformers` 5.10.2;
- `max_length = 16384`;
- no quantization;
- no CPU offload.

The upstream-matched hardware condition is H100/H200. Another BF16-capable CUDA
GPU is not silently rejected, but it is recorded as a distinct runtime condition
and must not be pooled with the upstream-matched condition.

## Analysis

The analyzer records three different questions separately:

1. **Local repeatability** — does an identical local request repeat identically?
2. **Local question-order sensitivity** — does reordering only the question
   mapping move the typed probabilities?
3. **Local vs hosted parity** — how far is each local typed answer from the
   matching frozen hosted answer?

The phase deliberately freezes **no acceptable-delta or causality threshold**.

Examples of later interpretations may be suggested by the data, but none are
pre-declared as proof:

- local sensitivity would weaken a hosted-layer-only explanation;
- local invariance with hosted sensitivity would increase interest in hosted
  lowering/runtime differences;
- different magnitudes would leave multiple model/runtime explanations open.

## Execution

Offline validation only:

```bash
python experiments/provider_portability/clef/phase2a/run_local.py --dry-run
```

GPU execution:

```bash
python experiments/provider_portability/clef/phase2a/run_local.py \
  --output-dir /tmp/clef-phase2a-local-v0.1
```

Analyze after preserving the run Evidence:

```bash
python experiments/provider_portability/clef/phase2a/analyze.py \
  --results-dir /tmp/clef-phase2a-local-v0.1 \
  --output /tmp/clef-phase2a-local-v0.1-analysis.json
```

Do not rerun into the same output directory after a failure. Preserve the failed
run first and use a new run identity.

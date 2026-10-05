# Clef-Flash Phase 2B — question-order source localization

Phase 2B asks a narrower question than Phase 2A:

> When question order changes, at which boundary does the measurable difference
> first enter the released local Clef-Flash decision path?

Phase 2A already established two facts under the frozen A100/BF16 run:

- all 18 local fixture/order conditions were byte-identical across three repeats;
- the same 15 non-canonical question-order conditions still moved typed
  probabilities.

Phase 2B therefore does **not** spend another 54 calls re-proving repeatability.
It traces one observation for each of the same 18 conditions and adds a
fixed-backbone head-order counterfactual.

## v0.2 retry freeze

The first frozen v0.1 execution reached a validated canary and preserved the
first actual typed response/logits, then failed before the first internal trace.
The failure was a runner context bug: backbone hidden states created under
`torch.inference_mode()` were later passed to trace-only `hidden_norm` while
ordinary autograd tracking was enabled.

The v0.1 failed Evidence is preserved and its run identity is never reused.

v0.2 keeps the released inference path unchanged. After the actual model/head
output is produced under `torch.inference_mode()`, the backbone hidden states
are cloned under `torch.no_grad()` into a normal graph-free tensor used only by
the trace path. Trace-only LayerNorm/mean operations also run under
`torch.no_grad()`.

No successful Phase 2B internal trace had been observed before the v0.2 retry
freeze.

## Upstream path under test

The released local path is:

```text
encode_record
  -> Qwen backbone last_hidden_state
  -> JointSchemaHead
  -> per-question logits / softmax probabilities
  -> SystemOne response
```

The joint head consumes context-dependent question and option span vectors,
a final-token global vector, lexical option vectors from the output embedding,
and joint routing layers.

## Frozen questions

Phase 2B records these boundaries separately.

1. **Encoding / placement**
   - exact encoded-input hash and length;
   - question instruction span token hash and absolute span;
   - option semantic span token hash and absolute span.
2. **Backbone representation**
   - state-span hidden representation;
   - final-token/global hidden vector;
   - aligned question mean-span vectors;
   - aligned option context mean-span vectors.
3. **Lexical option channel**
   - aligned option vectors derived from output embedding weights.
4. **Released final path**
   - logits, probabilities, and SystemOne answer.
5. **Fixed-backbone head-order counterfactual**
   - use the canonical encoded sequence and canonical backbone hidden states;
   - retain every semantic question's original canonical spans;
   - reorder only the `EncodedRecord.questions` tuple to the non-canonical
     question order;
   - execute the unchanged released `JointSchemaHead`;
   - align the resulting logits back by question ID.

The counterfactual is intentionally synthetic. It does **not** claim to be a
valid provider request. Its only purpose is to test whether head tuple ordering
alone is sufficient to reproduce the observed order effect when the backbone
representation is held fixed.

## Execution shape

The same Phase 1C / Phase 2A fixture family is inherited:

- 3 fixtures;
- 6 packed question-order conditions per fixture;
- 18 actual traced conditions total;
- one observation per condition;
- 5 fixed-backbone head-only counterfactuals per fixture = 15 controls.

One provider-neutral canary is executed first.

Phase 2A's 18/18 byte-identical three-repeat result is pinned as the reason that
Phase 2B v0.2 uses one observation per condition. Phase 2B does not redefine
repeatability.

## Runtime boundary

The runtime boundary remains unchanged from Phase 2A:

- exact `Cloudflare/clef-flash` revision
  `17f0b0ad64efb65d273590632833508766b2aae6`;
- local provider path `joint_schema_model.py:systemone`;
- CUDA + BF16;
- torch 2.11.x;
- transformers 5.10.2;
- max length 16384;
- no quantization;
- no CPU offload.

H100/H200 remains the upstream-matched hardware class. Other BF16-capable CUDA
GPUs remain explicit distinct runtime conditions.

## Interpretation boundary

Phase 2B freezes no semantic-delta or causality threshold.

Examples of bounded interpretations:

- invariant semantic span token hashes with changed absolute spans confirm that
  the same semantic question/option text is being placed in a different schema
  position;
- invariant state hidden representation with changed question/global
  representations localizes the effect after the shared state prefix without
  identifying a particular attention layer or positional mechanism;
- zero (or only numerical-noise-scale) fixed-backbone head-order delta while
  actual permutations differ would weaken "head tuple order alone" as an
  explanation;
- non-zero fixed-backbone head-order delta would show that joint-head field
  ordering contributes independently even with the backbone held fixed.

None of those outcomes alone prove a specific causal mechanism.

## Evidence discipline

- Preserve the v0.1 failed run before the v0.2 retry.
- Freeze v0.2 protocol and code before the first successful Phase 2B internal trace.
- Preserve every failed run before any retry.
- Never overwrite an Evidence directory.
- Record exact model/code/head hashes and runtime.
- Keep Phase 2A raw Evidence immutable.
- No post-output threshold selection.

Refs #118, #131, #132, #135, #136.

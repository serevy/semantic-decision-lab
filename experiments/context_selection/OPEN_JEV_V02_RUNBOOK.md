# Open Jev v0.2 runbook

v0.2 corrects the v0.1 adapter/context-packing failure without changing the
frozen dataset, gold labels, provider revision, or shared Top-2 evaluator.

## Preferred path: reuse the exact v0.1 checkpoint

If the original Colab runtime still exists, keep it alive. v0.2 expects the
pinned upstream checkout at:

`/content/open-jev-typed-decision-engine`

and reuses `jevlite.pt` only if its SHA-256 is exactly:

`90f6e2766b6b1e9210d701340325b6379530046804ab53b88239fced40908115`

This isolates the experiment change to packing only.

## Fresh runtime fallback

If the upstream checkout is absent, the v0.2 runner clones the same pinned
revision and trains/calibrates with the frozen v0.1 model configuration. The
new checkpoint SHA-256 is recorded in provenance. This is still a valid v0.2
run, but it is not a pure same-checkpoint A/B against v0.1.

## One-shot Colab

Run `open_jev_v0_2_colab.ipynb` on a T4 runtime.

The runner:

1. verifies/reuses the exact v0.1 checkpoint when present, otherwise trains it;
2. re-runs the exact 21-request v0.2 token-packing preflight;
3. starts the pinned Open Jev server;
4. runs the independent-record v0.2 provider adapter;
5. preserves selections, provider probabilities, metrics, provenance, and the
   preflight diagnostic;
6. creates `/content/open-jev-v0.2-results.zip`.

Do not overwrite an existing v0.2 results directory.

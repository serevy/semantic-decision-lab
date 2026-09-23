# Downstream task-success v0.1 execution runbook

This runbook executes the already-frozen downstream evaluation from Issue #74
and PDDR-0005. It does **not** choose or tune a downstream model.

## 1. Reproduce the frozen request pack

The exact 72-request pack is frozen by a deterministic builder plus the SHA-256
stored in `downstream-request-pack.v0.1.json`.

```bash
python experiments/context_selection/build_downstream_requests_v0_1.py --check
python experiments/context_selection/build_downstream_requests_v0_1.py \
  --output /tmp/downstream-requests.v0.1.jsonl
```

The generated JSONL contains 72 requests: 12 cases × 6 frozen context arms.
Every row includes the exact system/user prompt, selected PDDR IDs, and a
`prompt_sha256`. Gold choice, gold source-record mapping, rationale, and
`source_case_id` are intentionally absent.

The first CI generation is also preserved as a workflow artifact, but the
artifact is not the long-term source of truth: the versioned builder inputs and
frozen file SHA-256 are.

The context-selection arm determines **which records are supplied**. Once a
record is selected, the downstream model receives that record's complete frozen
Markdown text. The historical "first-512" name describes the retrieval
representation that produced the selected IDs; it does not truncate the
downstream context again.

## 2. Freeze one downstream run configuration before execution

Record at minimum:

- provider / runtime
- exact model identity and revision when available
- execution date
- sampling configuration
- any seed or determinism setting
- endpoint / adapter version when relevant

One run must use the same model and sampling configuration for all 72 requests.

Do not expose `downstream-cases.v0.1.json` to the model runner; it contains the
gold metadata. The model runner needs only `downstream-requests.v0.1.jsonl`.

## 3. Execute each frozen request exactly once for the first evidence run

Store a JSON envelope like:

```json
{
  "run": {
    "provider": "example-provider",
    "model": "exact-model-id",
    "executed_at": "2026-09-23T00:00:00Z",
    "sampling": {
      "temperature": 0
    }
  },
  "responses": [
    {
      "request_id": "keyword_top2/ds-001",
      "prompt_sha256": "...",
      "choice": "B",
      "raw_response": "B"
    }
  ]
}
```

`choice` must be exactly `A`, `B`, `C`, `D`, or `ABSTAIN`.
Preserve the raw response even when it is identical to the parsed choice.

For the first evidence run, do not selectively retry semantically undesirable
answers. Transport failures should be recorded separately and resolved under a
documented rerun policy before treating a run as complete.

## 4. Validate provenance and convert to evaluator input

```bash
python experiments/context_selection/validate_downstream_results_v0_1.py \
  /path/to/raw-results.json \
  --requests /tmp/downstream-requests.v0.1.jsonl

python experiments/context_selection/prepare_downstream_evaluator_input_v0_1.py \
  /path/to/raw-results.json \
  --requests /tmp/downstream-requests.v0.1.jsonl \
  --output /tmp/downstream-evaluator-input.json
```

The validator checks request coverage, prompt hashes, exact-choice parsing, and
run provenance without reading downstream gold.

## 5. Evaluate

```bash
python experiments/context_selection/evaluate_downstream_v0_1.py \
  /tmp/downstream-evaluator-input.json
```

Interpret the no-context arm first. If it scores highly, the scenario/options
may reveal the expected action without PDDR context, weakening claims that
retrieval preserved behavior.

Then compare full-context, required-only, and the three reduced-context arms.
Do not alter v0.1 prompts, options, gold, or retrieval selections in response to
the observed model outputs.

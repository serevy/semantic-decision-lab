from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CLEF_ROOT = ROOT.parent
if str(CLEF_ROOT) not in sys.path:
    sys.path.insert(0, str(CLEF_ROOT))

from contract import load_fixture, validate_response
from evidence_io import reserve_evidence, update_evidence
from phase2a.run_local import REQUIRED_SNAPSHOT_FILES, _runtime_condition
from phase2b.probes import (
    DEFAULT_MANIFEST,
    load_manifest,
    materialize_case,
    resolve_pinned_path,
    validate_manifest,
)
from run_local_clef_flash_smoke import (
    inspect_state_encoding,
    load_joint_schema_module,
    sha256_file,
)


def _json_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _response_sha256(response: dict[str, Any]) -> str:
    return _json_sha256(response)


def _token_sha256(token_ids: list[int] | tuple[int, ...]) -> str:
    raw = json.dumps(list(token_ids), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _tensor_descriptor(tensor: Any) -> dict[str, Any]:
    import torch

    value = tensor.detach().float().cpu().contiguous()
    raw = value.numpy().astype("<f4", copy=False).tobytes()
    return {
        "shape": list(value.shape),
        "float32_sha256": hashlib.sha256(raw).hexdigest(),
        "l2_norm": float(torch.linalg.vector_norm(value).item()),
    }


def _tensor_delta(first: Any, second: Any) -> dict[str, float]:
    import torch

    a = first.detach().float().reshape(-1)
    b = second.detach().float().reshape(-1)
    if a.shape != b.shape:
        raise ValueError(f"tensor shape mismatch: {tuple(a.shape)} != {tuple(b.shape)}")
    diff = a - b
    a_norm = torch.linalg.vector_norm(a)
    b_norm = torch.linalg.vector_norm(b)
    denominator = a_norm * b_norm
    cosine = (
        float(torch.dot(a, b).div(denominator).item())
        if float(denominator.item()) != 0.0
        else 1.0
    )
    return {
        "mean_absolute_delta": float(diff.abs().mean().item()),
        "max_absolute_delta": float(diff.abs().max().item()),
        "l2_delta": float(torch.linalg.vector_norm(diff).item()),
        "cosine_similarity": cosine,
    }


def _run_backbone(model: Any, batch: dict[str, Any]) -> tuple[Any, Any]:
    base_model = (
        model.language_model.get_base_model()
        if hasattr(model.language_model, "get_base_model")
        else model.language_model
    )
    media = batch.get("media") or {}
    text_model = base_model.model
    if not media and hasattr(text_model, "language_model"):
        text_model = text_model.language_model
    outputs = text_model(
        input_ids=batch["input_ids"],
        attention_mask=batch["attention_mask"],
        use_cache=False,
        return_dict=True,
        **media,
    )
    return outputs.last_hidden_state, base_model.get_output_embeddings().weight


def _response_from_logits(
    module: Any,
    request: dict[str, Any],
    encoded: Any,
    logits: list[Any],
) -> dict[str, Any]:
    questions = request["questions"]
    answers = {}
    for question, question_logits in zip(encoded.questions, logits):
        probabilities = dict(
            zip(
                question.option_ids,
                question_logits.float().softmax(-1).tolist(),
            )
        )
        answers[question.question_id] = module.systemone_answer(
            questions[question.question_id],
            probabilities,
        )
    return {
        "model": request["model"],
        "answers": answers,
        "usage": {"input_tokens": len(encoded.input_ids), "output_tokens": 0},
    }


def _logit_record(encoded: Any, logits: list[Any]) -> dict[str, Any]:
    result = {}
    for question, question_logits in zip(encoded.questions, logits):
        values = question_logits.detach().float().cpu().tolist()
        probabilities = question_logits.detach().float().softmax(-1).cpu().tolist()
        result[question.question_id] = {
            "option_ids": list(question.option_ids),
            "logits": values,
            "probabilities": dict(zip(question.option_ids, probabilities)),
        }
    return result


def _trace_components(
    module: Any,
    model: Any,
    processor: Any,
    request: dict[str, Any],
    encoded: Any,
    hidden_states: Any,
    input_ids: Any,
    output_embedding_weight: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if encoded.media:
        raise RuntimeError("Phase 2B v0.1 inherits text-only Phase 1C fixtures")

    sequence_length = len(encoded.input_ids)
    raw_hidden = hidden_states[0, :sequence_length]
    normalized_hidden = model.head.hidden_norm(raw_hidden)

    prefix_ids = module._tokens(
        processor.tokenizer,
        f"<|im_start|>system\n{module.SYSTEM_PROMPT}<|im_end|>\n"
        "<|im_start|>user\nSTATE:\n",
    )
    state_ids = module._tokens(processor.tokenizer, module.render(request["state"]))
    state_span = (len(prefix_ids), len(prefix_ids) + len(state_ids))
    if tuple(encoded.input_ids[state_span[0] : state_span[1]]) != tuple(state_ids):
        raise RuntimeError("Phase 2B could not recover the exact state span")

    tensor_values: dict[str, Any] = {
        "state_raw": raw_hidden[state_span[0] : state_span[1]],
        "state_normalized": normalized_hidden[state_span[0] : state_span[1]],
        "global_raw": raw_hidden[-1],
        "global_normalized": normalized_hidden[-1],
        "questions": {},
    }

    questions_json: dict[str, Any] = {}
    for question in encoded.questions:
        q_start, q_end = question.question_span
        question_tokens = input_ids[0, q_start:q_end].detach().cpu().tolist()
        q_raw = raw_hidden[q_start:q_end].mean(dim=0)
        q_norm = normalized_hidden[q_start:q_end].mean(dim=0)

        option_json: dict[str, Any] = {}
        option_tensors: dict[str, Any] = {}
        for option_id, (start, end) in zip(question.option_ids, question.option_spans):
            token_ids = input_ids[0, start:end]
            token_list = token_ids.detach().cpu().tolist()
            context_raw = raw_hidden[start:end].mean(dim=0)
            context_norm = normalized_hidden[start:end].mean(dim=0)
            lexical = output_embedding_weight[token_ids].mean(dim=0)
            option_json[option_id] = {
                "span": [start, end],
                "token_count": end - start,
                "semantic_token_sha256": _token_sha256(token_list),
                "backbone_context_raw": _tensor_descriptor(context_raw),
                "backbone_context_normalized": _tensor_descriptor(context_norm),
                "lexical_output_embedding": _tensor_descriptor(lexical),
            }
            option_tensors[option_id] = {
                "context_raw": context_raw,
                "context_normalized": context_norm,
                "lexical": lexical,
            }

        questions_json[question.question_id] = {
            "question_type": question.question_type,
            "span": [q_start, q_end],
            "token_count": q_end - q_start,
            "instruction_token_sha256": _token_sha256(question_tokens),
            "backbone_question_raw": _tensor_descriptor(q_raw),
            "backbone_question_normalized": _tensor_descriptor(q_norm),
            "options": option_json,
        }
        tensor_values["questions"][question.question_id] = {
            "question_raw": q_raw,
            "question_normalized": q_norm,
            "options": option_tensors,
        }

    trace = {
        "encoded_input_tokens": sequence_length,
        "encoded_input_ids_sha256": _token_sha256(encoded.input_ids),
        "question_order": [question.question_id for question in encoded.questions],
        "state_span": list(state_span),
        "state_token_count": len(state_ids),
        "state_token_sha256": _token_sha256(state_ids),
        "state_backbone_raw": _tensor_descriptor(tensor_values["state_raw"]),
        "state_backbone_normalized": _tensor_descriptor(
            tensor_values["state_normalized"]
        ),
        "global_backbone_raw": _tensor_descriptor(tensor_values["global_raw"]),
        "global_backbone_normalized": _tensor_descriptor(
            tensor_values["global_normalized"]
        ),
        "questions": questions_json,
    }
    return trace, tensor_values


def _trace_delta(
    current_trace: dict[str, Any],
    current_tensors: dict[str, Any],
    canonical_trace: dict[str, Any],
    canonical_tensors: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "encoded_input_ids_sha256_match": (
            current_trace["encoded_input_ids_sha256"]
            == canonical_trace["encoded_input_ids_sha256"]
        ),
        "state_token_sha256_match": (
            current_trace["state_token_sha256"] == canonical_trace["state_token_sha256"]
        ),
        "state_span_match": current_trace["state_span"] == canonical_trace["state_span"],
        "state_backbone_raw": _tensor_delta(
            current_tensors["state_raw"], canonical_tensors["state_raw"]
        ),
        "state_backbone_normalized": _tensor_delta(
            current_tensors["state_normalized"],
            canonical_tensors["state_normalized"],
        ),
        "global_backbone_raw": _tensor_delta(
            current_tensors["global_raw"], canonical_tensors["global_raw"]
        ),
        "global_backbone_normalized": _tensor_delta(
            current_tensors["global_normalized"],
            canonical_tensors["global_normalized"],
        ),
        "questions": {},
    }

    for question_id, current_question in current_tensors["questions"].items():
        canonical_question = canonical_tensors["questions"][question_id]
        current_meta = current_trace["questions"][question_id]
        canonical_meta = canonical_trace["questions"][question_id]
        question_result = {
            "instruction_token_sha256_match": (
                current_meta["instruction_token_sha256"]
                == canonical_meta["instruction_token_sha256"]
            ),
            "absolute_span_match": current_meta["span"] == canonical_meta["span"],
            "backbone_question_raw": _tensor_delta(
                current_question["question_raw"],
                canonical_question["question_raw"],
            ),
            "backbone_question_normalized": _tensor_delta(
                current_question["question_normalized"],
                canonical_question["question_normalized"],
            ),
            "options": {},
        }
        for option_id, current_option in current_question["options"].items():
            canonical_option = canonical_question["options"][option_id]
            current_option_meta = current_meta["options"][option_id]
            canonical_option_meta = canonical_meta["options"][option_id]
            question_result["options"][option_id] = {
                "semantic_token_sha256_match": (
                    current_option_meta["semantic_token_sha256"]
                    == canonical_option_meta["semantic_token_sha256"]
                ),
                "absolute_span_match": (
                    current_option_meta["span"] == canonical_option_meta["span"]
                ),
                "backbone_context_raw": _tensor_delta(
                    current_option["context_raw"],
                    canonical_option["context_raw"],
                ),
                "backbone_context_normalized": _tensor_delta(
                    current_option["context_normalized"],
                    canonical_option["context_normalized"],
                ),
                "lexical_output_embedding": _tensor_delta(
                    current_option["lexical"],
                    canonical_option["lexical"],
                ),
            }
        result["questions"][question_id] = question_result
    return result


def _build_head_only_record(module: Any, canonical_encoded: Any, target_order: list[str]) -> Any:
    by_id = {
        question.question_id: question
        for question in canonical_encoded.questions
    }
    if set(by_id) != set(target_order):
        raise ValueError("head-only target order does not match canonical question IDs")
    return module.EncodedRecord(
        input_ids=canonical_encoded.input_ids,
        questions=tuple(by_id[question_id] for question_id in target_order),
        record_id=canonical_encoded.record_id,
        media=canonical_encoded.media,
    )


def dry_run(manifest: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "experiment": manifest["experiment"],
        "mode": "dry-run-no-model-output",
        "hf_repo": manifest["model"]["hf_repo"],
        "hf_revision": manifest["model"]["hf_revision"],
        "condition_count": len(plan["conditions"]),
        "fixture_count": len(plan["fixtures"]),
        "question_order_count": len(plan["variants"]),
        "actual_backbone_forwards": manifest["execution"]["actual_backbone_forwards"],
        "total_backbone_forwards_including_canary": manifest["execution"][
            "total_backbone_forwards_including_canary"
        ],
        "head_only_counterfactuals": manifest["execution"][
            "head_only_counterfactuals"
        ],
        "schedule": [
            {
                "fixture_id": case["fixture_id"],
                "variant_id": case["variant"]["id"],
                "source_repeat_index": int(case["repeat_index"]),
            }
            for case in plan["conditions"]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output-dir")
    parser.add_argument("--cache-dir")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)
    plan = validate_manifest(manifest, manifest_path)

    if args.dry_run:
        print(json.dumps(dry_run(manifest, plan), ensure_ascii=False, indent=2))
        return 0

    if not args.output_dir:
        parser.error("--output-dir is required unless --dry-run is used")

    output_dir = Path(args.output_dir)
    run_path = output_dir / "run.json"
    run_evidence: dict[str, Any] = {
        "schema_version": "0.1",
        "experiment": manifest["experiment"],
        "stage": "reserved-before-model-preparation",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": manifest["provider"],
        "hf_repo": manifest["model"]["hf_repo"],
        "hf_revision_requested": manifest["model"]["hf_revision"],
        "traced_actual_conditions": len(plan["conditions"]),
        "head_only_counterfactuals": manifest["execution"][
            "head_only_counterfactuals"
        ],
    }
    try:
        reserve_evidence(run_path, run_evidence)
    except FileExistsError as exc:
        raise SystemExit(
            f"refusing to overwrite existing Phase 2B run evidence: {run_path}"
        ) from exc

    try:
        from huggingface_hub import model_info, snapshot_download
        import torch
        import transformers

        revision = manifest["model"]["hf_revision"]
        info = model_info(manifest["model"]["hf_repo"], revision=revision)
        if info.sha != revision:
            raise RuntimeError(
                f"HF revision mismatch: requested={revision} resolved={info.sha}"
            )

        snapshot = Path(
            snapshot_download(
                manifest["model"]["hf_repo"],
                revision=revision,
                cache_dir=args.cache_dir,
            )
        ).resolve()
        missing = [
            name for name in REQUIRED_SNAPSHOT_FILES
            if not (snapshot / name).is_file()
        ]
        if missing:
            raise RuntimeError(f"snapshot is incomplete: missing={missing}")

        module = load_joint_schema_module(snapshot)
        runtime = _runtime_condition(torch, transformers, manifest)
        run_evidence.update(
            {
                "stage": "snapshot-and-runtime-validated",
                "hf_revision": info.sha,
                "snapshot_path": str(snapshot),
                "joint_schema_model_sha256": sha256_file(
                    snapshot / "joint_schema_model.py"
                ),
                "joint_head_sha256": sha256_file(
                    snapshot / "joint_head.safetensors"
                ),
                "runtime": runtime,
            }
        )
        update_evidence(run_path, run_evidence)

        model, processor = module.load_release_model(
            str(snapshot),
            device=manifest["runtime_contract"]["device"],
            dtype=torch.bfloat16,
        )
        parameter_devices = sorted(
            {str(parameter.device) for parameter in model.parameters()}
        )
        if not parameter_devices or any(
            not device.startswith("cuda") for device in parameter_devices
        ):
            raise RuntimeError(
                "Phase 2B forbids CPU/offloaded model parameters: "
                f"devices={parameter_devices}"
            )
        first_dtype = str(next(model.parameters()).dtype)
        if first_dtype != "torch.bfloat16":
            raise RuntimeError(
                f"loaded model dtype drift: expected=torch.bfloat16 actual={first_dtype}"
            )
        runtime["loaded_parameter_devices"] = parameter_devices
        runtime["loaded_model_first_parameter_dtype"] = first_dtype
        update_evidence(run_path, run_evidence)

        canary_request = plan["canary_request"]
        canary_encoding = inspect_state_encoding(
            module,
            processor,
            canary_request,
            max_length=manifest["model"]["max_length"],
        )
        if canary_encoding["state_truncated"]:
            raise RuntimeError("Phase 2B canary state truncation is forbidden")

        canary_fixture = load_fixture(
            resolve_pinned_path(
                manifest_path,
                manifest["frozen_pins"]["canary_fixture_path"],
            )
        )
        probability_tolerance = float(
            canary_fixture["contract_expectations"][
                "probability_tolerance_after_rounding"
            ]
        )

        canary_path = output_dir / "canary.json"
        canary_evidence = {
            "schema_version": "0.1",
            "experiment": manifest["experiment"],
            "stage": "reserved-before-canary-inference",
            "request": canary_request,
            "encoding_preflight": canary_encoding,
            "hf_revision": revision,
            "runtime": runtime,
        }
        reserve_evidence(canary_path, canary_evidence)
        try:
            canary_response = module.systemone(
                model,
                processor,
                canary_request,
                max_length=manifest["model"]["max_length"],
            )
            canary_evidence.update(
                {
                    "stage": "canary-response-received",
                    "raw_response": canary_response,
                    "response_sha256": _response_sha256(canary_response),
                }
            )
            update_evidence(canary_path, canary_evidence)
            validate_response(
                canary_response,
                canary_request,
                probability_tolerance=probability_tolerance,
            )
            canary_evidence.update(
                {
                    "stage": "validated",
                    "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                }
            )
            update_evidence(canary_path, canary_evidence)
        except Exception as exc:
            canary_evidence.update(
                {
                    "stage": "canary-error",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            update_evidence(canary_path, canary_evidence)
            raise

        run_evidence["stage"] = "canary-validated-before-traces"
        update_evidence(run_path, run_evidence)

        canonical_cache: dict[str, dict[str, Any]] = {}
        completed_actual = 0
        completed_head_only = 0

        for case in plan["conditions"]:
            fixture_id = case["fixture_id"]
            variant_id = case["variant"]["id"]
            request = materialize_case(case)
            preflight = inspect_state_encoding(
                module,
                processor,
                request,
                max_length=manifest["model"]["max_length"],
            )
            if preflight["state_truncated"]:
                raise RuntimeError(
                    f"{fixture_id}/{variant_id}: state truncation is forbidden"
                )

            path = output_dir / fixture_id / "actual" / f"{variant_id}.json"
            evidence = {
                "schema_version": "0.1",
                "experiment": manifest["experiment"],
                "stage": "reserved-before-traced-inference",
                "fixture_id": fixture_id,
                "variant_id": variant_id,
                "source_repeat_index": int(case["repeat_index"]),
                "request": request,
                "encoding_preflight": preflight,
                "hf_revision": revision,
                "runtime": runtime,
            }
            reserve_evidence(path, evidence)

            encoded = module.encode_record(
                processor.tokenizer,
                request,
                max_length=manifest["model"]["max_length"],
                processor=processor,
            )
            device = next(model.parameters()).device
            batch = module.collate_records(
                [encoded],
                processor.tokenizer.pad_token_id,
                device,
            )
            with torch.inference_mode():
                hidden_states, output_embedding_weight = _run_backbone(model, batch)
                logits = model.head(
                    hidden_states,
                    batch["input_ids"],
                    batch["attention_mask"],
                    batch["records"],
                    output_embedding_weight,
                )[0]

            response = _response_from_logits(module, request, encoded, logits)
            evidence.update(
                {
                    "stage": "traced-response-received",
                    "raw_response": response,
                    "response_sha256": _response_sha256(response),
                    "logits": _logit_record(encoded, logits),
                }
            )
            update_evidence(path, evidence)
            validate_response(
                response,
                request,
                probability_tolerance=probability_tolerance,
            )

            trace, tensors = _trace_components(
                module,
                model,
                processor,
                request,
                encoded,
                hidden_states,
                batch["input_ids"],
                output_embedding_weight,
            )
            evidence["trace"] = trace

            if variant_id == "packed-canonical":
                canonical_cache[fixture_id] = {
                    "request": request,
                    "encoded": encoded,
                    "batch": batch,
                    "hidden_states": hidden_states,
                    "output_embedding_weight": output_embedding_weight,
                    "response": response,
                    "trace": trace,
                    "tensors": tensors,
                }
                evidence["deltas_vs_canonical"] = None
            else:
                if fixture_id not in canonical_cache:
                    raise RuntimeError(
                        f"{fixture_id}: canonical trace must run before variants"
                    )
                canonical = canonical_cache[fixture_id]
                evidence["deltas_vs_canonical"] = _trace_delta(
                    trace,
                    tensors,
                    canonical["trace"],
                    canonical["tensors"],
                )

                target_order = list(request["questions"])
                head_only_record = _build_head_only_record(
                    module,
                    canonical["encoded"],
                    target_order,
                )
                head_only_path = (
                    output_dir
                    / fixture_id
                    / "head-only"
                    / f"{variant_id}.json"
                )
                head_only_evidence = {
                    "schema_version": "0.1",
                    "experiment": manifest["experiment"],
                    "stage": "reserved-before-head-only-counterfactual",
                    "fixture_id": fixture_id,
                    "variant_id": variant_id,
                    "target_question_order": target_order,
                    "only_intervention": (
                        "reorder canonical EncodedRecord.questions tuple; "
                        "canonical input_ids, attention_mask, hidden states, "
                        "semantic spans, and weights remain fixed"
                    ),
                    "hf_revision": revision,
                    "runtime": runtime,
                }
                reserve_evidence(head_only_path, head_only_evidence)
                with torch.inference_mode():
                    counter_logits = model.head(
                        canonical["hidden_states"],
                        canonical["batch"]["input_ids"],
                        canonical["batch"]["attention_mask"],
                        [head_only_record],
                        canonical["output_embedding_weight"],
                    )[0]
                counter_response = _response_from_logits(
                    module,
                    request,
                    head_only_record,
                    counter_logits,
                )
                validate_response(
                    counter_response,
                    request,
                    probability_tolerance=probability_tolerance,
                )
                head_only_evidence.update(
                    {
                        "stage": "validated",
                        "raw_response": counter_response,
                        "response_sha256": _response_sha256(counter_response),
                        "logits": _logit_record(
                            head_only_record,
                            counter_logits,
                        ),
                        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                    }
                )
                update_evidence(head_only_path, head_only_evidence)
                completed_head_only += 1

            evidence.update(
                {
                    "stage": "validated",
                    "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                }
            )
            update_evidence(path, evidence)
            completed_actual += 1

        if len(canonical_cache) != 3:
            raise RuntimeError(
                f"Phase 2B expected 3 canonical caches, got {len(canonical_cache)}"
            )
        if completed_actual != manifest["execution"]["traced_actual_conditions"]:
            raise RuntimeError(
                f"Phase 2B actual condition count drift: {completed_actual}"
            )
        if completed_head_only != manifest["execution"]["head_only_counterfactuals"]:
            raise RuntimeError(
                f"Phase 2B head-only count drift: {completed_head_only}"
            )

        run_evidence.update(
            {
                "stage": "validated",
                "completed_actual_conditions": completed_actual,
                "completed_head_only_counterfactuals": completed_head_only,
                "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                "runtime": runtime,
            }
        )
        update_evidence(run_path, run_evidence)
        print(output_dir)
        return 0

    except Exception as exc:
        run_evidence.update(
            {
                "stage": "failed",
                "error": f"{type(exc).__name__}: {exc}",
                "failed_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
        update_evidence(run_path, run_evidence)
        raise RuntimeError(
            f"Clef-Flash Phase 2B local run failed; evidence: {run_path}"
        ) from exc


if __name__ == "__main__":
    raise SystemExit(main())

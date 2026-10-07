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
from phase2b.run_local import (
    _logit_record,
    _response_from_logits,
    _trace_delta,
    run_trace_components_from_inference_hidden_states,
)
from phase2b.probes import resolve_pinned_path
from phase2c.probes import (
    DEFAULT_MANIFEST,
    git_blob_sha,
    load_manifest,
    materialize_case,
    validate_manifest,
)
from run_local_clef_flash_smoke import (
    inspect_state_encoding,
    load_joint_schema_module,
    sha256_file,
)


def _json_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _response_sha256(response: dict[str, Any]) -> str:
    return _json_sha256(response)


def _preserve_canary_error(
    canary_path: Path,
    canary_evidence: dict[str, Any],
    exc: Exception,
) -> None:
    canary_evidence.update(
        {
            "stage": "canary-error",
            "error": f"{type(exc).__name__}: {exc}",
            "failed_at_utc": datetime.now(timezone.utc).isoformat(),
        }
    )
    update_evidence(canary_path, canary_evidence)


def _run_canary(
    *,
    canary_path: Path,
    canary_evidence: dict[str, Any],
    canary_encoding: dict[str, Any],
    module: Any,
    model: Any,
    processor: Any,
    canary_request: dict[str, Any],
    max_length: int,
    probability_tolerance: float,
) -> dict[str, Any]:
    reserve_evidence(canary_path, canary_evidence)
    try:
        if canary_encoding["state_truncated"]:
            raise RuntimeError("Phase 2C canary state truncation is forbidden")
        canary_response = module.systemone(
            model,
            processor,
            canary_request,
            max_length=max_length,
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
        return canary_response
    except Exception as exc:
        _preserve_canary_error(canary_path, canary_evidence, exc)
        raise


def _token_sha256(values: Any) -> str:
    if hasattr(values, "detach"):
        values = values.detach().cpu().reshape(-1).tolist()
    raw = json.dumps(list(values), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _run_backbone(
    model: Any,
    batch: dict[str, Any],
    *,
    position_ids: Any | None,
) -> tuple[Any, Any]:
    base_model = (
        model.language_model.get_base_model()
        if hasattr(model.language_model, "get_base_model")
        else model.language_model
    )
    media = batch.get("media") or {}
    text_model = base_model.model
    if not media and hasattr(text_model, "language_model"):
        text_model = text_model.language_model
    kwargs = {
        "input_ids": batch["input_ids"],
        "attention_mask": batch["attention_mask"],
        "use_cache": False,
        "return_dict": True,
        **media,
    }
    if position_ids is not None:
        kwargs["position_ids"] = position_ids
    outputs = text_model(**kwargs)
    return outputs.last_hidden_state, base_model.get_output_embeddings().weight


def _state_suffix_boundary(module: Any, processor: Any, request: dict[str, Any], encoded: Any) -> int:
    prefix_ids = module._tokens(
        processor.tokenizer,
        f"<|im_start|>system\n{module.SYSTEM_PROMPT}<|im_end|>\n"
        "<|im_start|>user\nSTATE:\n",
    )
    state_ids = module._tokens(processor.tokenizer, module.render(request["state"]))
    start = len(prefix_ids)
    end = start + len(state_ids)
    if tuple(encoded.input_ids[start:end]) != tuple(state_ids):
        raise RuntimeError("Phase 2C could not recover the exact state span")
    return end


def _sequential_position_ids(torch: Any, input_ids: Any) -> Any:
    return torch.arange(
        input_ids.shape[1], dtype=torch.long, device=input_ids.device
    ).unsqueeze(0).expand_as(input_ids)


def _position_record(position_ids: Any | None, *, mode: str, **extra: Any) -> dict[str, Any]:
    record: dict[str, Any] = {"mode": mode, **extra}
    if position_ids is None:
        record.update({"explicit": False, "sha256": None, "min": None, "max": None})
        return record
    flat = position_ids.detach().cpu().reshape(-1)
    record.update(
        {
            "explicit": True,
            "sha256": _token_sha256(flat),
            "min": int(flat.min().item()),
            "max": int(flat.max().item()),
            "count": int(flat.numel()),
        }
    )
    return record


def dry_run(manifest: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    schedule = []
    for case in plan["conditions"]:
        schedule.append(
            {
                "mode": "standard",
                "fixture_id": case["fixture_id"],
                "variant_id": case["variant"]["id"],
            }
        )
    for case in plan["conditions"]:
        schedule.append(
            {
                "mode": "zero-position",
                "fixture_id": case["fixture_id"],
                "variant_id": case["variant"]["id"],
            }
        )
    for case in plan["canonical_conditions"]:
        for offset in plan["suffix_shift_offsets"]:
            schedule.append(
                {
                    "mode": "suffix-shift",
                    "fixture_id": case["fixture_id"],
                    "variant_id": case["variant"]["id"],
                    "offset": offset,
                }
            )
    return {
        "schema_version": "0.1",
        "protocol_version": plan["protocol_version"],
        "experiment": manifest["experiment"],
        "run_identity": manifest["execution"]["run_identity"],
        "mode": "dry-run-no-model-output",
        "standard_conditions": 18,
        "zero_position_conditions": 18,
        "suffix_shift_conditions": 6,
        "experimental_backbone_forwards": len(schedule),
        "schedule": schedule,
    }


def _run_condition(
    *,
    torch: Any,
    module: Any,
    model: Any,
    processor: Any,
    request: dict[str, Any],
    fixture_id: str,
    variant_id: str,
    mode: str,
    output_path: Path,
    runtime: dict[str, Any],
    revision: str,
    max_length: int,
    probability_tolerance: float,
    position_ids_factory: Any,
    baseline: dict[str, Any] | None,
    extra_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    preflight = inspect_state_encoding(module, processor, request, max_length=max_length)
    if preflight["state_truncated"]:
        raise RuntimeError(f"{fixture_id}/{mode}/{variant_id}: state truncation is forbidden")

    evidence: dict[str, Any] = {
        "schema_version": "0.1",
        "protocol_version": "0.1",
        "experiment": "clef-flash-phase2c-backbone-mechanism-isolation",
        "stage": "reserved-before-model-output",
        "fixture_id": fixture_id,
        "variant_id": variant_id,
        "control_mode": mode,
        "request": request,
        "encoding_preflight": preflight,
        "hf_revision": revision,
        "runtime": runtime,
    }
    if extra_evidence:
        evidence.update(extra_evidence)
    reserve_evidence(output_path, evidence)

    try:
        encoded = module.encode_record(
            processor.tokenizer,
            request,
            max_length=max_length,
            processor=processor,
        )
        device = next(model.parameters()).device
        batch = module.collate_records(
            [encoded], processor.tokenizer.pad_token_id, device
        )
        position_ids, position_meta = position_ids_factory(
            torch, module, processor, request, encoded, batch
        )
        evidence["position_control"] = position_meta
        evidence["input_ids_sha256"] = _token_sha256(batch["input_ids"])
        evidence["attention_mask_sha256"] = _token_sha256(batch["attention_mask"])
        update_evidence(output_path, evidence)

        with torch.inference_mode():
            inference_hidden_states, output_embedding_weight = _run_backbone(
                model, batch, position_ids=position_ids
            )
            logits = model.head(
                inference_hidden_states,
                batch["input_ids"],
                batch["attention_mask"],
                batch["records"],
                output_embedding_weight,
            )[0]

        response = _response_from_logits(module, request, encoded, logits)
        evidence.update(
            {
                "stage": "response-received",
                "raw_response": response,
                "response_sha256": _response_sha256(response),
                "logits": _logit_record(encoded, logits),
            }
        )
        update_evidence(output_path, evidence)
        validate_response(
            response, request, probability_tolerance=probability_tolerance
        )

        trace, tensors, hidden_states = run_trace_components_from_inference_hidden_states(
            torch,
            module=module,
            model=model,
            processor=processor,
            request=request,
            encoded=encoded,
            inference_hidden_states=inference_hidden_states,
            input_ids=batch["input_ids"],
            output_embedding_weight=output_embedding_weight,
        )
        evidence["trace"] = trace
        evidence["deltas_vs_control_baseline"] = (
            None
            if baseline is None
            else _trace_delta(trace, tensors, baseline["trace"], baseline["tensors"])
        )
        evidence.update(
            {
                "stage": "validated",
                "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
        update_evidence(output_path, evidence)
        return {
            "request": request,
            "encoded": encoded,
            "batch": batch,
            "hidden_states": hidden_states,
            "output_embedding_weight": output_embedding_weight,
            "response": response,
            "trace": trace,
            "tensors": tensors,
        }
    except Exception as exc:
        evidence.update(
            {
                "stage": "failed",
                "error": f"{type(exc).__name__}: {exc}",
                "failed_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )
        update_evidence(output_path, evidence)
        raise


def _standard_positions(torch: Any, module: Any, processor: Any, request: dict[str, Any], encoded: Any, batch: dict[str, Any]) -> tuple[Any | None, dict[str, Any]]:
    return None, _position_record(None, mode="model-default")


def _zero_positions(torch: Any, module: Any, processor: Any, request: dict[str, Any], encoded: Any, batch: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    position_ids = torch.zeros_like(batch["input_ids"], dtype=torch.long)
    return position_ids, _position_record(
        position_ids,
        mode="all-zero",
        only_intervention="replace request-native/default position IDs with zero; preserve input IDs and attention mask",
    )


def _suffix_shift_factory(offset: int, max_length: int):
    def factory(torch: Any, module: Any, processor: Any, request: dict[str, Any], encoded: Any, batch: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        position_ids = _sequential_position_ids(torch, batch["input_ids"]).clone()
        boundary = _state_suffix_boundary(module, processor, request, encoded)
        position_ids[:, boundary:] += offset
        if int(position_ids.max().item()) >= max_length:
            raise RuntimeError(
                f"suffix-shift position exceeds frozen max_length: max={int(position_ids.max().item())}"
            )
        return position_ids, _position_record(
            position_ids,
            mode="canonical-suffix-shift",
            offset=offset,
            suffix_boundary=boundary,
            only_intervention="add offset to explicit position IDs after exact rendered state span",
        )
    return factory


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
        result = dry_run(manifest, plan)
        if result["experimental_backbone_forwards"] != manifest["execution"]["experimental_backbone_forwards"]:
            raise RuntimeError("Phase 2C dry-run schedule count drift")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if not args.output_dir:
        parser.error("--output-dir is required unless --dry-run is used")
    output_dir = Path(args.output_dir)
    expected_run_identity = manifest["execution"]["run_identity"]
    if output_dir.name != expected_run_identity:
        raise SystemExit(
            f"Phase 2C run identity mismatch: expected={expected_run_identity} actual={output_dir.name}"
        )

    run_path = output_dir / "run.json"
    run_evidence: dict[str, Any] = {
        "schema_version": "0.1",
        "protocol_version": plan["protocol_version"],
        "experiment": manifest["experiment"],
        "run_identity": expected_run_identity,
        "stage": "reserved-before-model-preparation",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": manifest["provider"],
        "hf_repo": manifest["model"]["hf_repo"],
        "hf_revision_requested": manifest["model"]["hf_revision"],
        "expected_counts": {
            "standard": 18,
            "zero_position": 18,
            "suffix_shift": 6,
            "experimental_backbone_forwards": 42,
        },
        "source_blob_shas": {
            "manifest": git_blob_sha(manifest_path),
            "phase2c/run_local.py": git_blob_sha(ROOT / "run_local.py"),
            "phase2c/probes.py": git_blob_sha(ROOT / "probes.py"),
        },
    }
    try:
        reserve_evidence(run_path, run_evidence)
    except FileExistsError as exc:
        raise SystemExit(f"refusing to overwrite existing Phase 2C evidence: {run_path}") from exc

    try:
        from huggingface_hub import model_info, snapshot_download
        import torch
        import transformers

        revision = manifest["model"]["hf_revision"]
        info = model_info(manifest["model"]["hf_repo"], revision=revision)
        if info.sha != revision:
            raise RuntimeError(f"HF revision mismatch: requested={revision} resolved={info.sha}")
        snapshot = Path(
            snapshot_download(
                manifest["model"]["hf_repo"],
                revision=revision,
                cache_dir=args.cache_dir,
            )
        ).resolve()
        missing = [name for name in REQUIRED_SNAPSHOT_FILES if not (snapshot / name).is_file()]
        if missing:
            raise RuntimeError(f"snapshot is incomplete: missing={missing}")

        module = load_joint_schema_module(snapshot)
        runtime = _runtime_condition(torch, transformers, manifest)
        run_evidence.update(
            {
                "stage": "snapshot-and-runtime-validated",
                "hf_revision": info.sha,
                "snapshot_path": str(snapshot),
                "joint_schema_model_sha256": sha256_file(snapshot / "joint_schema_model.py"),
                "joint_head_sha256": sha256_file(snapshot / "joint_head.safetensors"),
                "runtime": runtime,
            }
        )
        update_evidence(run_path, run_evidence)

        model, processor = module.load_release_model(
            str(snapshot),
            device=manifest["runtime_contract"]["device"],
            dtype=torch.bfloat16,
        )
        devices = sorted({str(parameter.device) for parameter in model.parameters()})
        if not devices or any(not device.startswith("cuda") for device in devices):
            raise RuntimeError(f"Phase 2C forbids CPU/offloaded parameters: devices={devices}")
        if str(next(model.parameters()).dtype) != "torch.bfloat16":
            raise RuntimeError("Phase 2C loaded model dtype drift")
        runtime["loaded_parameter_devices"] = devices
        runtime["loaded_model_first_parameter_dtype"] = str(next(model.parameters()).dtype)
        update_evidence(run_path, run_evidence)

        canary_request = plan["canary_request"]
        canary_encoding = inspect_state_encoding(
            module, processor, canary_request, max_length=manifest["model"]["max_length"]
        )
        canary_fixture = load_fixture(
            resolve_pinned_path(manifest_path, manifest["frozen_pins"]["canary_fixture_path"])
        )
        probability_tolerance = float(
            canary_fixture["contract_expectations"]["probability_tolerance_after_rounding"]
        )
        canary_path = output_dir / "canary.json"
        canary_evidence = {
            "schema_version": "0.1",
            "protocol_version": "0.1",
            "experiment": manifest["experiment"],
            "run_identity": expected_run_identity,
            "stage": "reserved-before-canary-inference",
            "request": canary_request,
            "encoding_preflight": canary_encoding,
            "hf_revision": revision,
            "runtime": runtime,
        }
        _run_canary(
            canary_path=canary_path,
            canary_evidence=canary_evidence,
            canary_encoding=canary_encoding,
            module=module,
            model=model,
            processor=processor,
            canary_request=canary_request,
            max_length=manifest["model"]["max_length"],
            probability_tolerance=probability_tolerance,
        )
        run_evidence["stage"] = "canary-validated-before-controls"
        update_evidence(run_path, run_evidence)

        standard_baselines: dict[str, dict[str, Any]] = {}
        zero_baselines: dict[str, dict[str, Any]] = {}
        standard_count = 0
        zero_count = 0
        shift_count = 0

        for case in plan["conditions"]:
            fixture_id = case["fixture_id"]
            variant_id = case["variant"]["id"]
            request = materialize_case(case)
            baseline = None if variant_id == "packed-canonical" else standard_baselines[fixture_id]
            result = _run_condition(
                torch=torch, module=module, model=model, processor=processor,
                request=request, fixture_id=fixture_id, variant_id=variant_id,
                mode="standard",
                output_path=output_dir / fixture_id / "standard" / f"{variant_id}.json",
                runtime=runtime, revision=revision, max_length=manifest["model"]["max_length"],
                probability_tolerance=probability_tolerance,
                position_ids_factory=_standard_positions, baseline=baseline,
            )
            if variant_id == "packed-canonical":
                standard_baselines[fixture_id] = result
            standard_count += 1

        for case in plan["conditions"]:
            fixture_id = case["fixture_id"]
            variant_id = case["variant"]["id"]
            request = materialize_case(case)
            baseline = None if variant_id == "packed-canonical" else zero_baselines[fixture_id]
            result = _run_condition(
                torch=torch, module=module, model=model, processor=processor,
                request=request, fixture_id=fixture_id, variant_id=variant_id,
                mode="zero-position",
                output_path=output_dir / fixture_id / "zero-position" / f"{variant_id}.json",
                runtime=runtime, revision=revision, max_length=manifest["model"]["max_length"],
                probability_tolerance=probability_tolerance,
                position_ids_factory=_zero_positions, baseline=baseline,
            )
            if variant_id == "packed-canonical":
                zero_baselines[fixture_id] = result
            zero_count += 1

        for case in plan["canonical_conditions"]:
            fixture_id = case["fixture_id"]
            request = materialize_case(case)
            for offset in plan["suffix_shift_offsets"]:
                _run_condition(
                    torch=torch, module=module, model=model, processor=processor,
                    request=request, fixture_id=fixture_id,
                    variant_id=f"packed-canonical-offset-{offset}",
                    mode="suffix-shift",
                    output_path=output_dir / fixture_id / "suffix-shift" / f"offset-{offset}.json",
                    runtime=runtime, revision=revision, max_length=manifest["model"]["max_length"],
                    probability_tolerance=probability_tolerance,
                    position_ids_factory=_suffix_shift_factory(offset, manifest["model"]["max_length"]),
                    baseline=standard_baselines[fixture_id],
                    extra_evidence={"source_variant": "packed-canonical", "offset": offset},
                )
                shift_count += 1

        observed = {
            "standard": standard_count,
            "zero_position": zero_count,
            "suffix_shift": shift_count,
            "experimental_backbone_forwards": standard_count + zero_count + shift_count,
        }
        expected = {
            "standard": manifest["execution"]["standard_conditions"],
            "zero_position": manifest["execution"]["zero_position_conditions"],
            "suffix_shift": manifest["execution"]["suffix_shift_conditions"],
            "experimental_backbone_forwards": manifest["execution"]["experimental_backbone_forwards"],
        }
        if observed != expected:
            raise RuntimeError(f"Phase 2C execution count drift: observed={observed} expected={expected}")

        run_evidence.update(
            {
                "stage": "validated",
                "observed_counts": observed,
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
        raise RuntimeError(f"Clef-Flash Phase 2C local run failed; evidence: {run_path}") from exc


if __name__ == "__main__":
    raise SystemExit(main())

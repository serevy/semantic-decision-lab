from __future__ import annotations

import argparse
import hashlib
import json
import re
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
from phase2a.probes import (
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
from run_workers_ai_smoke import canonical_json, wire_json


REQUIRED_SNAPSHOT_FILES = (
    "joint_schema_model.py",
    "joint_head.safetensors",
    "joint_head_config.json",
    "model.safetensors.index.json",
    "config.json",
)


def response_bytes(response: dict[str, Any]) -> bytes:
    return json.dumps(
        response,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def response_sha256(response: dict[str, Any]) -> str:
    return hashlib.sha256(response_bytes(response)).hexdigest()


def request_hashes(request: dict[str, Any]) -> dict[str, str]:
    return {
        "canonical_request_sha256": hashlib.sha256(
            canonical_json(request)
        ).hexdigest(),
        "order_sensitive_request_sha256": hashlib.sha256(
            wire_json(request)
        ).hexdigest(),
    }


def _runtime_condition(torch: Any, transformers: Any, manifest: dict[str, Any]) -> dict[str, Any]:
    required = manifest["runtime_contract"]
    if not torch.cuda.is_available():
        raise RuntimeError("Phase 2A requires CUDA")
    if not bool(torch.cuda.is_bf16_supported()):
        raise RuntimeError("Phase 2A requires a BF16-capable CUDA GPU")

    torch_version = str(torch.__version__)
    transformers_version = str(transformers.__version__)
    if not torch_version.startswith(required["torch_version_prefix"]):
        raise RuntimeError(
            "torch version drift: "
            f"required_prefix={required['torch_version_prefix']} actual={torch_version}"
        )
    if transformers_version != required["transformers_version"]:
        raise RuntimeError(
            "transformers version drift: "
            f"required={required['transformers_version']} actual={transformers_version}"
        )

    gpu = torch.cuda.get_device_name(0)
    upstream_hardware_match = bool(re.search(r"\bH(?:100|200)\b", gpu, re.I))
    return {
        "python": sys.version.split()[0],
        "torch": torch_version,
        "transformers": transformers_version,
        "cuda": str(torch.version.cuda),
        "gpu": gpu,
        "bf16_supported": True,
        "requested_device": required["device"],
        "requested_dtype": required["requested_dtype"],
        "upstream_hardware_match_h100_h200": upstream_hardware_match,
        "hardware_condition": (
            "upstream-matched-h100-h200"
            if upstream_hardware_match
            else f"explicit-non-upstream-hardware:{gpu}"
        ),
    }


def _assert_no_truncation(label: str, encoding: dict[str, Any]) -> None:
    if encoding["state_truncated"]:
        raise RuntimeError(f"{label}: state truncation is forbidden in Phase 2A")


def _record_response(
    path: Path,
    evidence: dict[str, Any],
    response: dict[str, Any],
    request: dict[str, Any],
    *,
    probability_tolerance: float,
) -> None:
    evidence.update(
        {
            "stage": "local-response-received",
            "raw_response": response,
            "local_response_sha256": response_sha256(response),
            "local_response_hash_basis": "canonical-json-sort-keys",
        }
    )
    update_evidence(path, evidence)

    normalized = validate_response(
        response,
        request,
        probability_tolerance=probability_tolerance,
    )
    evidence.update(
        {
            "stage": "validated",
            "normalized_systemone_response": normalized,
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        }
    )
    update_evidence(path, evidence)


def dry_run(manifest: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    canary = plan["canary_request"]
    unique_conditions: dict[str, Any] = {}
    schedule = []
    for case in plan["cases"]:
        request = materialize_case(case)
        key = f"{case['fixture_id']}/{case['variant']['id']}"
        unique_conditions.setdefault(
            key,
            {
                "fixture_id": case["fixture_id"],
                "variant_id": case["variant"]["id"],
                **request_hashes(request),
            },
        )
        schedule.append(
            {
                "position": case["position"],
                "round": case["round"],
                "repeat_index": case["repeat_index"],
                "fixture_id": case["fixture_id"],
                "variant_id": case["variant"]["id"],
                "canonical_request_sha256": case["canonical_request_sha256"],
                "order_sensitive_request_sha256": case["wire_request_sha256"],
            }
        )

    return {
        "schema_version": "0.1",
        "experiment": manifest["experiment"],
        "mode": "dry-run-no-model-output",
        "hf_repo": manifest["model"]["hf_repo"],
        "hf_revision": manifest["model"]["hf_revision"],
        "max_length": manifest["model"]["max_length"],
        "canary": request_hashes(canary),
        "condition_count": len(unique_conditions),
        "scheduled_calls": len(schedule),
        "total_model_calls_if_executed": manifest["execution"]["total_model_calls"],
        "unique_conditions": list(unique_conditions.values()),
        "schedule": schedule,
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
        "hf_repo": manifest["model"]["hf_repo"],
        "hf_revision_requested": manifest["model"]["hf_revision"],
        "max_length": manifest["model"]["max_length"],
        "scheduled_experiment_calls": len(plan["cases"]),
        "total_model_calls": manifest["execution"]["total_model_calls"],
    }
    try:
        reserve_evidence(run_path, run_evidence)
    except FileExistsError as exc:
        raise SystemExit(
            f"refusing to overwrite existing Phase 2A run evidence: {run_path}"
        ) from exc

    try:
        from huggingface_hub import model_info, snapshot_download

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

        import torch
        import transformers

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

        parameter_devices = sorted({str(parameter.device) for parameter in model.parameters()})
        if not parameter_devices or any(
            not device.startswith("cuda") for device in parameter_devices
        ):
            raise RuntimeError(
                "Phase 2A forbids CPU/offloaded model parameters: "
                f"devices={parameter_devices}"
            )
        try:
            first_dtype = str(next(model.parameters()).dtype)
        except StopIteration as exc:
            raise RuntimeError("loaded model has no parameters") from exc
        if first_dtype != "torch.bfloat16":
            raise RuntimeError(
                f"loaded model dtype drift: expected=torch.bfloat16 actual={first_dtype}"
            )
        runtime["loaded_parameter_devices"] = parameter_devices
        runtime["loaded_model_first_parameter_dtype"] = first_dtype

        canary_request = plan["canary_request"]
        canary_encoding = inspect_state_encoding(
            module,
            processor,
            canary_request,
            max_length=manifest["model"]["max_length"],
        )
        _assert_no_truncation("canary", canary_encoding)

        unique_preflight: dict[tuple[str, str], dict[str, Any]] = {}
        for case in plan["cases"]:
            key = (case["fixture_id"], case["variant"]["id"])
            if key in unique_preflight:
                continue
            request = materialize_case(case)
            encoding = inspect_state_encoding(
                module,
                processor,
                request,
                max_length=manifest["model"]["max_length"],
            )
            _assert_no_truncation("/".join(key), encoding)
            unique_preflight[key] = encoding

        run_evidence.update(
            {
                "stage": "all-encodings-preflighted-before-first-output",
                "canary_encoding_preflight": canary_encoding,
                "unique_condition_preflight_count": len(unique_preflight),
                "runtime": runtime,
            }
        )
        update_evidence(run_path, run_evidence)

        canary_fixture_path = resolve_pinned_path(
            manifest_path,
            manifest["frozen_pins"]["canary_fixture_path"],
        )
        canary_fixture = load_fixture(canary_fixture_path)
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
            **request_hashes(canary_request),
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
            _record_response(
                canary_path,
                canary_evidence,
                canary_response,
                canary_request,
                probability_tolerance=probability_tolerance,
            )
        except Exception as exc:
            canary_evidence.update(
                {
                    "stage": "canary-error",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            update_evidence(canary_path, canary_evidence)
            raise

        run_evidence["stage"] = "canary-validated-before-experiment"
        update_evidence(run_path, run_evidence)

        completed = 0
        for case in plan["cases"]:
            fixture_id = case["fixture_id"]
            variant_id = case["variant"]["id"]
            repeat_index = int(case["repeat_index"])
            request = materialize_case(case)
            path = (
                output_dir
                / fixture_id
                / variant_id
                / f"repeat-{repeat_index}.json"
            )
            evidence = {
                "schema_version": "0.1",
                "experiment": manifest["experiment"],
                "stage": "reserved-before-local-inference",
                "position": case["position"],
                "round": case["round"],
                "repeat_index": repeat_index,
                "fixture_id": fixture_id,
                "variant_id": variant_id,
                "request": request,
                "canonical_request_sha256": case["canonical_request_sha256"],
                "order_sensitive_request_sha256": case["wire_request_sha256"],
                "encoding_preflight": unique_preflight[(fixture_id, variant_id)],
                "hf_revision": revision,
                "runtime": runtime,
            }
            reserve_evidence(path, evidence)
            try:
                response = module.systemone(
                    model,
                    processor,
                    request,
                    max_length=manifest["model"]["max_length"],
                )
                _record_response(
                    path,
                    evidence,
                    response,
                    request,
                    probability_tolerance=probability_tolerance,
                )
            except Exception as exc:
                evidence.update(
                    {
                        "stage": "local-inference-or-contract-error",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                update_evidence(path, evidence)
                raise
            completed += 1

        run_evidence.update(
            {
                "stage": "validated",
                "completed_experiment_calls": completed,
                "completed_at_utc": datetime.now(timezone.utc).isoformat(),
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
            f"Clef-Flash Phase 2A local run failed; evidence: {run_path}"
        ) from exc


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CLEF_ROOT = ROOT.parent
if str(CLEF_ROOT) not in sys.path:
    sys.path.insert(0, str(CLEF_ROOT))

from phase2a.probes import (
    build_canary_request as build_phase2a_canary_request,
    load_manifest as load_phase2a_manifest,
    materialize_case,
    resolve_pinned_path,
    validate_manifest as validate_phase2a_manifest,
)

DEFAULT_MANIFEST = ROOT / "source-localization-manifest.v0.2.json"
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def load_manifest(path: str | Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def _validate_file_pins(manifest: dict[str, Any], manifest_path: str | Path) -> None:
    pins = manifest["frozen_pins"]
    pairs = [
        ("phase2a_manifest_path", "phase2a_manifest_blob_sha"),
        ("phase2a_probes_path", "phase2a_probes_blob_sha"),
        ("phase2a_runner_path", "phase2a_runner_blob_sha"),
        ("local_smoke_runner_path", "local_smoke_runner_blob_sha"),
        ("contract_path", "contract_blob_sha"),
        ("canary_fixture_path", "canary_fixture_blob_sha"),
        ("phase2a_summary_path", "phase2a_summary_blob_sha"),
        ("phase2a_analysis_path", "phase2a_analysis_blob_sha"),
        ("phase2a_evidence_archive_path", "phase2a_evidence_archive_blob_sha"),
    ]
    if manifest.get("protocol_version") == "0.2":
        pairs.extend(
            [
                ("phase2b_v0_1_manifest_path", "phase2b_v0_1_manifest_blob_sha"),
                (
                    "phase2b_v0_1_failure_summary_path",
                    "phase2b_v0_1_failure_summary_blob_sha",
                ),
                (
                    "phase2b_v0_1_failure_run_path",
                    "phase2b_v0_1_failure_run_blob_sha",
                ),
                (
                    "phase2b_v0_1_failure_canary_path",
                    "phase2b_v0_1_failure_canary_blob_sha",
                ),
                (
                    "phase2b_v0_1_failure_first_actual_path",
                    "phase2b_v0_1_failure_first_actual_blob_sha",
                ),
            ]
        )

    for path_field, sha_field in pairs:
        path = resolve_pinned_path(manifest_path, pins[path_field])
        actual = git_blob_sha(path)
        expected = pins[sha_field]
        if actual != expected:
            raise ValueError(
                f"Phase 2B pinned blob mismatch for {path_field}: "
                f"expected={expected} actual={actual}"
            )


def _validate_freeze_generation(manifest: dict[str, Any]) -> str:
    version = str(manifest.get("protocol_version", "0.1"))
    if version == "0.1":
        if manifest.get("frozen_before_phase2b_internal_output") is not True:
            raise ValueError("Phase 2B v0.1 must freeze before internal output")
        if manifest.get("phase2b_internal_outputs_observed_before_freeze") != 0:
            raise ValueError("Phase 2B v0.1 must freeze before internal traces")
        return version

    if version == "0.2":
        if manifest.get("frozen_before_phase2b_v0_2_retry_output") is not True:
            raise ValueError("Phase 2B v0.2 must freeze before retry output")
        if manifest.get("successful_phase2b_trace_outputs_observed_before_freeze") != 0:
            raise ValueError(
                "Phase 2B v0.2 must freeze before any successful trace output"
            )
        attempts = manifest.get("prior_failed_attempts")
        if not isinstance(attempts, list) or len(attempts) != 1:
            raise ValueError("Phase 2B v0.2 must preserve exactly one v0.1 failure")
        prior = attempts[0]
        expected = {
            "run_identity": "clef-phase2b-local-v0.1",
            "freeze_commit": "08c16640320805aeaad7942079dfbe87ea8f8d7a",
            "outcome": "failed-after-first-actual-response-before-trace",
            "first_actual_stage": "trace-error",
            "failure_kind": "runner-inference-tensor-trace-context",
            "successful_trace_outputs": 0,
            "head_only_counterfactuals_completed": 0,
        }
        for key, value in expected.items():
            if prior.get(key) != value:
                raise ValueError(
                    f"Phase 2B v0.2 prior failure drift: "
                    f"{key}={prior.get(key)!r}"
                )
        if prior.get("first_actual_response_preserved") is not True:
            raise ValueError("Phase 2B v0.2 must preserve the failed raw response")
        return version

    raise ValueError(f"unsupported Phase 2B protocol version: {version}")


def validate_manifest(
    manifest: dict[str, Any],
    manifest_path: str | Path = DEFAULT_MANIFEST,
) -> dict[str, Any]:
    version = _validate_freeze_generation(manifest)

    model = manifest["model"]
    revision = model["hf_revision"]
    if not FULL_SHA_RE.fullmatch(revision):
        raise ValueError("Phase 2B HF revision must be a full immutable SHA")
    if not revision.startswith(model["discovery_prefix"]):
        raise ValueError("Phase 2B HF revision drifted outside discovery prefix")
    if model["max_length"] != 16384:
        raise ValueError("Phase 2B freezes max_length at 16384")

    provider = manifest["provider"]
    if provider["kind"] != "local-inference":
        raise ValueError("Phase 2B is a local-inference experiment")
    if provider["entrypoint"] != "joint_schema_model.py:systemone":
        raise ValueError("Phase 2B must retain the released SystemOne path")

    runtime = manifest["runtime_contract"]
    if runtime["device"] != "cuda" or runtime["requested_dtype"] != "bfloat16":
        raise ValueError("Phase 2B requires CUDA BF16")
    if runtime["torch_version_prefix"] != "2.11":
        raise ValueError("Phase 2B requires torch 2.11.x")
    if runtime["transformers_version"] != "5.10.2":
        raise ValueError("Phase 2B requires transformers 5.10.2")
    if runtime.get("no_quantization") is not True:
        raise ValueError("Phase 2B forbids quantization")
    if runtime.get("no_cpu_offload") is not True:
        raise ValueError("Phase 2B forbids CPU offload")

    execution = manifest["execution"]
    expected = {
        "canary_calls": 1,
        "traced_actual_conditions": 18,
        "actual_backbone_forwards": 18,
        "total_backbone_forwards_including_canary": 19,
        "head_only_counterfactuals": 15,
    }
    for key, value in expected.items():
        if execution[key] != value:
            raise ValueError(f"Phase 2B execution drift: {key}={execution[key]}")
    if execution.get("one_observation_per_condition") is not True:
        raise ValueError("Phase 2B freezes one observation per condition")
    if execution.get("reuse_single_loaded_model") is not True:
        raise ValueError("Phase 2B requires one loaded model")
    if execution.get("no_retries_inside_run") is not True:
        raise ValueError("Phase 2B does not retry inside a run")
    if execution.get("semantic_threshold") is not None:
        raise ValueError("Phase 2B freezes no semantic threshold")
    if execution.get("stage_delta_threshold") is not None:
        raise ValueError("Phase 2B freezes no stage-delta threshold")
    if version == "0.2" and execution.get("run_identity") != "clef-phase2b-local-v0.2":
        raise ValueError("Phase 2B v0.2 must use a fresh run identity")

    if version == "0.2":
        trace_fix = manifest.get("trace_runtime_fix", {})
        if trace_fix.get("actual_inference_context") != "torch.inference_mode":
            raise ValueError("Phase 2B v0.2 must preserve released inference context")
        if "clone" not in str(trace_fix.get("trace_bridge", "")).lower():
            raise ValueError("Phase 2B v0.2 must clone inference hidden states")
        if trace_fix.get("trace_context") != "torch.no_grad":
            raise ValueError("Phase 2B v0.2 tracing must run under torch.no_grad")

    _validate_file_pins(manifest, manifest_path)

    phase2a_path = resolve_pinned_path(
        manifest_path,
        manifest["frozen_pins"]["phase2a_manifest_path"],
    )
    phase2a = load_phase2a_manifest(phase2a_path)
    phase2a_plan = validate_phase2a_manifest(phase2a, phase2a_path)
    cases = phase2a_plan["cases"]

    phase1c = phase2a_plan["phase1c_manifest"]
    fixtures = list(phase1c["phase1b_fixture_pins"])
    variants = list(phase1c["question_order_variants"])
    if len(fixtures) != 3 or len(variants) != 6:
        raise ValueError("Phase 2B requires 3 fixtures x 6 question orders")
    if variants[0] != "packed-canonical":
        raise ValueError("Phase 2B requires canonical order first")

    repeat1: dict[tuple[str, str], dict[str, Any]] = {}
    for case in cases:
        if int(case["repeat_index"]) == 1:
            repeat1[(case["fixture_id"], case["variant"]["id"])] = case

    ordered_conditions = []
    for fixture_id in fixtures:
        for variant_id in variants:
            key = (fixture_id, variant_id)
            if key not in repeat1:
                raise ValueError(f"missing Phase 2B inherited condition: {key}")
            ordered_conditions.append(repeat1[key])

    if len(ordered_conditions) != 18:
        raise ValueError("Phase 2B must materialize exactly 18 conditions")

    canary_request = build_phase2a_canary_request(phase2a, phase2a_path)
    return {
        "protocol_version": version,
        "phase2a_manifest": phase2a,
        "phase2a_plan": phase2a_plan,
        "fixtures": fixtures,
        "variants": variants,
        "conditions": ordered_conditions,
        "canary_request": canary_request,
    }

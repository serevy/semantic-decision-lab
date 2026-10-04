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

DEFAULT_MANIFEST = ROOT / "source-localization-manifest.v0.1.json"
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
    for path_field, sha_field in pairs:
        path = resolve_pinned_path(manifest_path, pins[path_field])
        actual = git_blob_sha(path)
        expected = pins[sha_field]
        if actual != expected:
            raise ValueError(
                f"Phase 2B pinned blob mismatch for {path_field}: "
                f"expected={expected} actual={actual}"
            )


def validate_manifest(
    manifest: dict[str, Any],
    manifest_path: str | Path = DEFAULT_MANIFEST,
) -> dict[str, Any]:
    if manifest.get("frozen_before_phase2b_internal_output") is not True:
        raise ValueError("Phase 2B manifest must freeze before internal output")
    if manifest.get("phase2b_internal_outputs_observed_before_freeze") != 0:
        raise ValueError("Phase 2B v0.1 must freeze before internal traces")

    model = manifest["model"]
    revision = model["hf_revision"]
    if not FULL_SHA_RE.fullmatch(revision):
        raise ValueError("Phase 2B HF revision must be a full immutable SHA")
    if not revision.startswith(model["discovery_prefix"]):
        raise ValueError("Phase 2B HF revision drifted outside discovery prefix")
    if model["max_length"] != 16384:
        raise ValueError("Phase 2B v0.1 freezes max_length at 16384")

    provider = manifest["provider"]
    if provider["kind"] != "local-inference":
        raise ValueError("Phase 2B v0.1 is a local-inference experiment")
    if provider["entrypoint"] != "joint_schema_model.py:systemone":
        raise ValueError("Phase 2B must retain the released SystemOne path")

    runtime = manifest["runtime_contract"]
    if runtime["device"] != "cuda" or runtime["requested_dtype"] != "bfloat16":
        raise ValueError("Phase 2B v0.1 requires CUDA BF16")
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
        raise ValueError("Phase 2B v0.1 freezes one observation per condition")
    if execution.get("reuse_single_loaded_model") is not True:
        raise ValueError("Phase 2B requires one loaded model")
    if execution.get("no_retries_inside_run") is not True:
        raise ValueError("Phase 2B does not retry inside a run")
    if execution.get("semantic_threshold") is not None:
        raise ValueError("Phase 2B freezes no semantic threshold")
    if execution.get("stage_delta_threshold") is not None:
        raise ValueError("Phase 2B freezes no stage-delta threshold")

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
        "phase2a_manifest": phase2a,
        "phase2a_plan": phase2a_plan,
        "fixtures": fixtures,
        "variants": variants,
        "conditions": ordered_conditions,
        "canary_request": canary_request,
    }

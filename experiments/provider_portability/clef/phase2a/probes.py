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

from contract import load_fixture, validate_request
from phase1c.probes import (
    load_manifest as load_phase1c_manifest,
    materialize_case as materialize_phase1c_case,
    validate_manifest as validate_phase1c_manifest,
)


DEFAULT_MANIFEST = ROOT / "local-parity-manifest.v0.1.json"
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def load_manifest(path: str | Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def resolve_pinned_path(manifest_path: str | Path, relative: str) -> Path:
    return (Path(manifest_path).resolve().parent / relative).resolve()


def _validate_file_pins(
    manifest: dict[str, Any],
    manifest_path: str | Path,
) -> None:
    pins = manifest["frozen_pins"]
    pairs = [
        ("phase1c_manifest_path", "phase1c_manifest_blob_sha"),
        ("phase1c_probes_path", "phase1c_probes_blob_sha"),
        ("local_smoke_runner_path", "local_smoke_runner_blob_sha"),
        ("contract_path", "contract_blob_sha"),
        ("canary_fixture_path", "canary_fixture_blob_sha"),
        ("hosted_phase1c_bundle_path", "hosted_phase1c_bundle_blob_sha"),
        ("hosted_phase1c_analysis_path", "hosted_phase1c_analysis_blob_sha"),
    ]
    for path_field, sha_field in pairs:
        path = resolve_pinned_path(manifest_path, pins[path_field])
        actual = git_blob_sha(path)
        expected = pins[sha_field]
        if actual != expected:
            raise ValueError(
                f"Phase 2A pinned blob mismatch for {path_field}: "
                f"expected={expected} actual={actual}"
            )


def build_canary_request(
    manifest: dict[str, Any],
    manifest_path: str | Path = DEFAULT_MANIFEST,
) -> dict[str, Any]:
    path = resolve_pinned_path(
        manifest_path,
        manifest["frozen_pins"]["canary_fixture_path"],
    )
    fixture = load_fixture(path)
    request = json.loads(json.dumps(fixture["request"]))
    request["model"] = "clef-flash"
    validate_request(request)
    return request


def validate_manifest(
    manifest: dict[str, Any],
    manifest_path: str | Path = DEFAULT_MANIFEST,
) -> dict[str, Any]:
    if manifest.get("frozen_before_phase2a_local_output") is not True:
        raise ValueError("Phase 2A manifest must be frozen before local output")
    if manifest.get("local_outputs_observed_before_freeze") != 0:
        raise ValueError("Phase 2A v0.1 must freeze before any local output")

    model = manifest["model"]
    revision = model["hf_revision"]
    if not FULL_SHA_RE.fullmatch(revision):
        raise ValueError("Phase 2A HF revision must be a full immutable SHA")
    if not revision.startswith(model["discovery_prefix"]):
        raise ValueError("Phase 2A HF revision drifted outside discovery prefix")
    if model["max_length"] != 16384:
        raise ValueError("Phase 2A v0.1 freezes max_length at 16384")
    if model["decision_entrypoint"] != "joint_schema_model.py:systemone":
        raise ValueError("Phase 2A must use the released System One decision path")

    runtime = manifest["runtime_contract"]
    if runtime["device"] != "cuda" or runtime["requested_dtype"] != "bfloat16":
        raise ValueError("Phase 2A v0.1 requires CUDA BF16")
    if runtime.get("no_quantization") is not True:
        raise ValueError("Phase 2A v0.1 forbids quantization")
    if runtime.get("no_cpu_offload") is not True:
        raise ValueError("Phase 2A v0.1 forbids CPU offload")

    execution = manifest["execution"]
    if execution["canary_calls"] != 1:
        raise ValueError("Phase 2A requires exactly one canary")
    if execution["phase1c_schedule_calls"] != 54:
        raise ValueError("Phase 2A must inherit all 54 Phase 1C calls")
    if execution["total_model_calls"] != 55:
        raise ValueError("Phase 2A total model-call count must be 55")
    if execution["reuse_single_loaded_model"] is not True:
        raise ValueError("Phase 2A requires one loaded model per run")
    if execution["no_retries_inside_run"] is not True:
        raise ValueError("Phase 2A does not retry inside a run")
    if execution.get("semantic_canary_threshold") is not None:
        raise ValueError("Phase 2A canary must not freeze a semantic threshold")

    _validate_file_pins(manifest, manifest_path)

    phase1c_manifest_path = resolve_pinned_path(
        manifest_path,
        manifest["frozen_pins"]["phase1c_manifest_path"],
    )
    phase1c_manifest = load_phase1c_manifest(phase1c_manifest_path)
    cases = validate_phase1c_manifest(
        phase1c_manifest,
        phase1c_manifest_path,
    )
    if len(cases) != 54:
        raise ValueError("Phase 2A inherited schedule must contain 54 calls")

    condition_keys = {
        (case["fixture_id"], case["variant"]["id"])
        for case in cases
    }
    if len(condition_keys) != 18:
        raise ValueError("Phase 2A must inherit exactly 18 conditions")
    repeat_keys: dict[tuple[str, str], set[int]] = {}
    for case in cases:
        key = (case["fixture_id"], case["variant"]["id"])
        repeat_keys.setdefault(key, set()).add(int(case["repeat_index"]))
    if any(repeats != {1, 2, 3} for repeats in repeat_keys.values()):
        raise ValueError("Phase 2A must inherit three repeats per condition")

    canary_request = build_canary_request(manifest, manifest_path)
    return {
        "canary_request": canary_request,
        "phase1c_manifest": phase1c_manifest,
        "cases": cases,
    }


def materialize_case(case: dict[str, Any]) -> dict[str, Any]:
    request = materialize_phase1c_case(case)
    validate_request(request)
    return request

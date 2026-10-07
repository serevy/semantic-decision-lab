from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CLEF_ROOT = ROOT.parent
if str(CLEF_ROOT) not in sys.path:
    sys.path.insert(0, str(CLEF_ROOT))

from phase2b.probes import (
    git_blob_sha,
    load_manifest as load_phase2b_manifest,
    materialize_case,
    resolve_pinned_path,
    validate_manifest as validate_phase2b_manifest,
)

DEFAULT_MANIFEST = ROOT / "mechanism-isolation-manifest.v0.1.json"
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def load_manifest(path: str | Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _validate_file_pins(manifest: dict[str, Any], manifest_path: str | Path) -> None:
    pins = manifest["frozen_pins"]
    pairs = [
        ("phase2b_manifest_path", "phase2b_manifest_blob_sha"),
        ("phase2b_probes_path", "phase2b_probes_blob_sha"),
        ("phase2b_runner_path", "phase2b_runner_blob_sha"),
        ("phase2b_analyzer_path", "phase2b_analyzer_blob_sha"),
        ("phase2b_summary_path", "phase2b_summary_blob_sha"),
        ("phase2b_analysis_path", "phase2b_analysis_blob_sha"),
        ("phase2b_evidence_archive_path", "phase2b_evidence_archive_blob_sha"),
        ("contract_path", "contract_blob_sha"),
        ("canary_fixture_path", "canary_fixture_blob_sha"),
        ("local_smoke_runner_path", "local_smoke_runner_blob_sha"),
    ]
    for path_field, sha_field in pairs:
        path = resolve_pinned_path(manifest_path, pins[path_field])
        actual = git_blob_sha(path)
        expected = pins[sha_field]
        if actual != expected:
            raise ValueError(
                f"Phase 2C pinned blob mismatch for {path_field}: "
                f"expected={expected} actual={actual}"
            )


def validate_manifest(
    manifest: dict[str, Any],
    manifest_path: str | Path = DEFAULT_MANIFEST,
) -> dict[str, Any]:
    if manifest.get("protocol_version") != "0.1":
        raise ValueError("Phase 2C protocol version must be 0.1")
    if manifest.get("frozen_before_phase2c_output") is not True:
        raise ValueError("Phase 2C must freeze before model output")
    if manifest.get("phase2c_model_outputs_observed_before_freeze") != 0:
        raise ValueError("Phase 2C freeze requires zero prior model outputs")

    model = manifest["model"]
    revision = model["hf_revision"]
    if not FULL_SHA_RE.fullmatch(revision):
        raise ValueError("Phase 2C HF revision must be a full immutable SHA")
    if not revision.startswith(model["discovery_prefix"]):
        raise ValueError("Phase 2C HF revision drifted outside discovery prefix")
    if model["max_length"] != 16384:
        raise ValueError("Phase 2C freezes max_length at 16384")

    provider = manifest["provider"]
    if provider["kind"] != "local-inference":
        raise ValueError("Phase 2C is a local-inference experiment")
    if provider["entrypoint"] != "joint_schema_model.py:systemone":
        raise ValueError("Phase 2C must retain the released SystemOne path")

    runtime = manifest["runtime_contract"]
    if runtime["device"] != "cuda" or runtime["requested_dtype"] != "bfloat16":
        raise ValueError("Phase 2C requires CUDA BF16")
    if runtime["torch_version_prefix"] != "2.11":
        raise ValueError("Phase 2C requires torch 2.11.x")
    if runtime["transformers_version"] != "5.10.2":
        raise ValueError("Phase 2C requires transformers 5.10.2")
    if runtime.get("no_quantization") is not True:
        raise ValueError("Phase 2C forbids quantization")
    if runtime.get("no_cpu_offload") is not True:
        raise ValueError("Phase 2C forbids CPU offload")

    execution = manifest["execution"]
    expected = {
        "run_identity": "clef-phase2c-local-v0.1",
        "canary_calls": 1,
        "standard_conditions": 18,
        "zero_position_conditions": 18,
        "suffix_shift_conditions": 6,
        "experimental_backbone_forwards": 42,
        "suffix_shift_offsets": [32, 128],
    }
    for key, value in expected.items():
        if execution.get(key) != value:
            raise ValueError(f"Phase 2C execution drift: {key}={execution.get(key)!r}")
    for flag in ("one_observation_per_condition", "reuse_single_loaded_model", "no_retries_inside_run"):
        if execution.get(flag) is not True:
            raise ValueError(f"Phase 2C requires {flag}=true")
    for threshold in (
        "semantic_threshold",
        "numerical_noise_threshold",
        "sufficiency_threshold",
        "necessity_threshold",
        "causality_threshold",
    ):
        if execution.get(threshold) is not None:
            raise ValueError(f"Phase 2C freezes no {threshold}")

    controls = manifest["controls"]
    if controls["zero_position"].get("position_ids") != "all zero":
        raise ValueError("Phase 2C zero-position control drift")
    suffix = controls["canonical_suffix_shift"]
    if suffix.get("source_variant") != "packed-canonical":
        raise ValueError("Phase 2C suffix shift must start from packed-canonical")
    if suffix.get("offsets") != [32, 128]:
        raise ValueError("Phase 2C suffix-shift offsets drift")

    _validate_file_pins(manifest, manifest_path)

    phase2b_path = resolve_pinned_path(
        manifest_path, manifest["frozen_pins"]["phase2b_manifest_path"]
    )
    phase2b = load_phase2b_manifest(phase2b_path)
    phase2b_plan = validate_phase2b_manifest(phase2b, phase2b_path)
    if phase2b_plan["protocol_version"] != "0.2":
        raise ValueError("Phase 2C must inherit the successful Phase 2B v0.2 family")

    fixtures = list(phase2b_plan["fixtures"])
    variants = list(phase2b_plan["variants"])
    conditions = list(phase2b_plan["conditions"])
    if len(fixtures) != 3 or len(variants) != 6 or len(conditions) != 18:
        raise ValueError("Phase 2C requires exactly 3 fixtures x 6 question orders")
    if variants[0] != "packed-canonical":
        raise ValueError("Phase 2C requires packed-canonical first")

    canonical_conditions = [
        case for case in conditions if case["variant"]["id"] == "packed-canonical"
    ]
    if len(canonical_conditions) != 3:
        raise ValueError("Phase 2C requires one canonical condition per fixture")
    if len(canonical_conditions) * len(execution["suffix_shift_offsets"]) != 6:
        raise ValueError("Phase 2C suffix-shift schedule must contain 6 conditions")

    return {
        "protocol_version": "0.1",
        "phase2b_manifest": phase2b,
        "phase2b_plan": phase2b_plan,
        "fixtures": fixtures,
        "variants": variants,
        "conditions": conditions,
        "canonical_conditions": canonical_conditions,
        "suffix_shift_offsets": list(execution["suffix_shift_offsets"]),
        "canary_request": phase2b_plan["canary_request"],
    }


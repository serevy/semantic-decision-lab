from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CLEF_ROOT = ROOT.parent
if str(CLEF_ROOT) not in sys.path:
    sys.path.insert(0, str(CLEF_ROOT))

from contract import load_fixture, validate_request
from phase1a.probes import build_request, load_matrix as load_phase1a_matrix, materialize_fixture
from run_workers_ai_smoke import canonical_json, wire_json


DEFAULT_MANIFEST = ROOT / "repeatability-manifest.v0.1.json"
PHASE1A_MATRIX = CLEF_ROOT / "phase1a" / "probe-matrix.v0.1.json"


def load_manifest(path: str | Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def _validate_pins(manifest: dict[str, Any], manifest_path: str | Path) -> None:
    phase1a = manifest["phase1a_pins"]
    phase1a_paths = {
        "probe_matrix_blob_sha": PHASE1A_MATRIX,
        "probes_blob_sha": CLEF_ROOT / "phase1a" / "probes.py",
        "analyze_blob_sha": CLEF_ROOT / "phase1a" / "analyze.py",
        "hosted_runner_blob_sha": CLEF_ROOT / "run_workers_ai_smoke.py",
    }
    for field, path in phase1a_paths.items():
        actual = git_blob_sha(path)
        if actual != phase1a[field]:
            raise ValueError(
                f"pinned Phase 1A blob mismatch for {field}: "
                f"expected={phase1a[field]} actual={actual}"
            )

    manifest_root = Path(manifest_path).resolve().parent
    for fixture_id, entry in manifest["phase1b_fixture_pins"].items():
        path = (manifest_root / entry["path"]).resolve()
        actual = git_blob_sha(path)
        if actual != entry["blob_sha"]:
            raise ValueError(
                f"pinned fixture blob mismatch for {fixture_id}: "
                f"expected={entry['blob_sha']} actual={actual}"
            )


def load_fixture_map(
    manifest: dict[str, Any],
    manifest_path: str | Path = DEFAULT_MANIFEST,
) -> dict[str, dict[str, Any]]:
    manifest_root = Path(manifest_path).resolve().parent
    fixtures = {}
    for fixture_id, entry in manifest["phase1b_fixture_pins"].items():
        fixtures[fixture_id] = load_fixture((manifest_root / entry["path"]).resolve())
    return fixtures


def validate_manifest(
    manifest: dict[str, Any],
    manifest_path: str | Path = DEFAULT_MANIFEST,
) -> list[dict[str, Any]]:
    if manifest.get("frozen_before_phase1c_output") is not True:
        raise ValueError("Phase 1C manifest must be frozen before provider output")
    if manifest.get("repeats_per_condition") != 3:
        raise ValueError("Phase 1C v0.1 requires exactly three repeats")
    if manifest.get("condition_count") != 18:
        raise ValueError("Phase 1C v0.1 requires exactly 18 conditions")
    if manifest.get("expected_provider_calls") != 54:
        raise ValueError("Phase 1C v0.1 requires exactly 54 calls")

    _validate_pins(manifest, manifest_path)

    phase1a = load_phase1a_matrix(PHASE1A_MATRIX)
    variants_by_id = {variant["id"]: variant for variant in phase1a["variants"]}
    expected_variants = manifest["question_order_variants"]
    if len(expected_variants) != 6 or expected_variants[0] != "packed-canonical":
        raise ValueError("Phase 1C must freeze six packed question-order conditions")
    if any(variant_id not in variants_by_id for variant_id in expected_variants):
        raise ValueError("Phase 1C references an unknown Phase 1A variant")
    if any("choice-" in variant_id or variant_id.startswith("single-") for variant_id in expected_variants):
        raise ValueError("Phase 1C must not include choice-order or single-question variants")

    fixtures = load_fixture_map(manifest, manifest_path)
    schedule = manifest.get("schedule")
    if not isinstance(schedule, list) or len(schedule) != 54:
        raise ValueError("Phase 1C schedule must contain exactly 54 entries")

    condition_repeats: dict[tuple[str, str], set[int]] = {}
    cases = []
    for position, item in enumerate(schedule):
        fixture_id = item["fixture_id"]
        variant_id = item["variant_id"]
        repeat_index = int(item["repeat_index"])
        round_index = int(item["round"])
        if fixture_id not in fixtures:
            raise ValueError(f"unknown fixture in schedule: {fixture_id}")
        if variant_id not in expected_variants:
            raise ValueError(f"unexpected variant in schedule: {variant_id}")
        if repeat_index != round_index or repeat_index not in (1, 2, 3):
            raise ValueError("repeat_index must equal frozen round 1..3")

        key = (fixture_id, variant_id)
        condition_repeats.setdefault(key, set()).add(repeat_index)

        source = fixtures[fixture_id]
        variant = variants_by_id[variant_id]
        request = build_request(variant, source)
        validate_request(request)
        cases.append(
            {
                "position": position,
                "round": round_index,
                "repeat_index": repeat_index,
                "fixture_id": fixture_id,
                "variant": variant,
                "source_fixture": source,
                "canonical_request_sha256": hashlib.sha256(
                    canonical_json(request)
                ).hexdigest(),
                "wire_request_sha256": hashlib.sha256(wire_json(request)).hexdigest(),
            }
        )

    if len(condition_repeats) != 18:
        raise ValueError("Phase 1C condition count drifted")
    if any(repeats != {1, 2, 3} for repeats in condition_repeats.values()):
        raise ValueError("each condition must occur once in each repeat round")

    for fixture_id in fixtures:
        wire_by_variant = {}
        for case in cases:
            if case["fixture_id"] == fixture_id:
                wire_by_variant.setdefault(
                    case["variant"]["id"], case["wire_request_sha256"]
                )
                if (
                    wire_by_variant[case["variant"]["id"]]
                    != case["wire_request_sha256"]
                ):
                    raise ValueError("same condition produced different wire hashes")
        if len(set(wire_by_variant.values())) != 6:
            raise ValueError(f"question-order wires collapsed for fixture {fixture_id}")

    return cases


def materialize_case(case: dict[str, Any]) -> dict[str, Any]:
    return materialize_fixture(case["variant"], case["source_fixture"])

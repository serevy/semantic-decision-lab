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


DEFAULT_MANIFEST = ROOT / "replication-manifest.v0.1.json"
PHASE1A_MATRIX = CLEF_ROOT / "phase1a" / "probe-matrix.v0.1.json"
REFERENCE_FIXTURE = CLEF_ROOT / "systemone-contract.v0.1.json"


def load_manifest(path: str | Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def _validate_phase1a_pins(manifest: dict[str, Any]) -> None:
    pins = manifest["phase1a_freeze"]
    paths = {
        "probe_matrix_blob_sha": PHASE1A_MATRIX,
        "probes_blob_sha": CLEF_ROOT / "phase1a" / "probes.py",
        "analyze_blob_sha": CLEF_ROOT / "phase1a" / "analyze.py",
        "hosted_runner_blob_sha": CLEF_ROOT / "run_workers_ai_smoke.py",
        "contract_fixture_blob_sha": REFERENCE_FIXTURE,
    }
    for field, path in paths.items():
        actual = git_blob_sha(path)
        expected = pins[field]
        if actual != expected:
            raise ValueError(
                f"Phase 1A pinned blob mismatch for {field}: "
                f"expected={expected} actual={actual}"
            )


def load_replication_fixture(
    entry: dict[str, Any],
    manifest_path: str | Path = DEFAULT_MANIFEST,
) -> dict[str, Any]:
    manifest_root = Path(manifest_path).resolve().parent
    path = (manifest_root / entry["path"]).resolve()
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != entry["sha256"]:
        raise ValueError(
            f"fixture hash mismatch for {entry['id']}: "
            f"expected={entry['sha256']} actual={actual}"
        )
    return json.loads(raw.decode("utf-8"))


def validate_manifest(
    manifest: dict[str, Any],
    manifest_path: str | Path = DEFAULT_MANIFEST,
) -> list[dict[str, Any]]:
    if manifest.get("frozen_before_phase1b_output") is not True:
        raise ValueError("Phase 1B manifest must be frozen before provider output")
    if manifest.get("expected_provider_calls") != 42:
        raise ValueError("Phase 1B v0.1 must freeze exactly 42 provider calls")

    _validate_phase1a_pins(manifest)

    phase1a = load_phase1a_matrix(PHASE1A_MATRIX)
    variants = phase1a["variants"]
    variant_ids = [variant["id"] for variant in variants]
    if len(variants) != manifest.get("inherited_variant_count"):
        raise ValueError("Phase 1A variant count drifted")
    if variant_ids != manifest.get("inherited_variant_ids"):
        raise ValueError("Phase 1A variant order or identity drifted")

    fixture_entries = manifest.get("fixtures")
    if not isinstance(fixture_entries, list) or len(fixture_entries) != 3:
        raise ValueError("Phase 1B v0.1 must contain exactly three fixtures")

    reference = load_fixture(REFERENCE_FIXTURE)
    reference_questions = reference["request"]["questions"]
    reference_state_order = list(reference["request"]["state"])
    cases: list[dict[str, Any]] = []

    for entry in fixture_entries:
        source = load_replication_fixture(entry, manifest_path)
        if source["request"]["model"] != reference["request"]["model"]:
            raise ValueError(f"model selector drift in fixture {entry['id']}")
        if source["request"]["questions"] != reference_questions:
            raise ValueError(f"question contract drift in fixture {entry['id']}")
        if list(source["request"]["state"]) != reference_state_order:
            raise ValueError(f"state mapping order drift in fixture {entry['id']}")

        wire_hashes: set[str] = set()
        canonical_hashes: set[str] = set()
        for variant in variants:
            request = build_request(variant, source)
            validate_request(request)
            canonical_hash = hashlib.sha256(canonical_json(request)).hexdigest()
            wire_hash = hashlib.sha256(wire_json(request)).hexdigest()
            canonical_hashes.add(canonical_hash)
            wire_hashes.add(wire_hash)
            cases.append(
                {
                    "fixture_id": entry["id"],
                    "variant": variant,
                    "source_fixture": source,
                    "canonical_request_sha256": canonical_hash,
                    "wire_request_sha256": wire_hash,
                }
            )

        if len(wire_hashes) != 14:
            raise ValueError(f"wire variants collapsed in fixture {entry['id']}")
        if len(canonical_hashes) != 4:
            raise ValueError(
                f"unexpected canonical-content groups in fixture {entry['id']}"
            )

    if len(cases) != manifest["expected_provider_calls"]:
        raise ValueError("materialized Phase 1B call count mismatch")
    return cases


def materialize_case(case: dict[str, Any]) -> dict[str, Any]:
    return materialize_fixture(case["variant"], case["source_fixture"])

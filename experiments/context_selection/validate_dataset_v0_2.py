#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASES = ROOT / "cases.v0.2.json"
CASES_V01 = ROOT / "cases.v0.1.json"
REGISTRY = ROOT / "corpus-registry.v0.2.json"

ID_RE = re.compile(r"^id:\s*(PDDR-\d+)\s*$", re.MULTILINE)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str) -> None:
    raise SystemExit(message)


def record_ids_from_snapshot(snapshot_path: Path) -> set[str]:
    ids: set[str] = set()
    for path in sorted(snapshot_path.glob("PDDR-*.md")):
        match = ID_RE.search(path.read_text(encoding="utf-8"))
        if not match:
            fail(f"{path}: missing front-matter PDDR id")
        record_id = match.group(1)
        if record_id in ids:
            fail(f"{snapshot_path}: duplicate record id {record_id}")
        ids.add(record_id)
    return ids


def main() -> None:
    cases = load_json(CASES)
    registry = load_json(REGISTRY)

    if registry.get("dataset_version") != "0.2":
        fail("corpus registry dataset_version must be 0.2")
    snapshots = registry.get("snapshots")
    if not isinstance(snapshots, dict) or not snapshots:
        fail("corpus registry must define snapshots")

    snapshot_ids: dict[str, set[str]] = {}
    for snapshot_name, spec in snapshots.items():
        path = ROOT / spec["path"]
        if not path.is_dir():
            fail(f"{snapshot_name}: missing snapshot directory {path}")
        manifest = ROOT / spec["manifest"]
        if not manifest.is_file():
            fail(f"{snapshot_name}: missing manifest {manifest}")
        actual = record_ids_from_snapshot(path)
        declared = set(spec.get("record_ids", []))
        if actual != declared:
            fail(
                f"{snapshot_name}: record id mismatch "
                f"actual={sorted(actual)} declared={sorted(declared)}"
            )

        manifest_data = load_json(manifest)
        manifest_files = {
            record["file"]
            for record in manifest_data.get("records", [])
            if isinstance(record, dict) and "file" in record
        }
        actual_files = {p.name for p in path.glob("PDDR-*.md")}
        if manifest_files != actual_files:
            fail(
                f"{snapshot_name}: manifest/file mismatch "
                f"manifest={sorted(manifest_files)} actual={sorted(actual_files)}"
            )
        snapshot_ids[snapshot_name] = actual

    if len(cases) != 12:
        fail(f"v0.2 must freeze exactly 12 cases, found {len(cases)}")

    # The original three pilot cases are immutable in v0.2. Extra metadata may
    # be added, but the task, difficulty, corpus, and gold labels must not move.
    pilot = load_json(CASES_V01)
    for old, new in zip(pilot, cases[:3], strict=True):
        for key in ("case_id", "difficulty", "task", "corpus", "gold"):
            if new.get(key) != old.get(key):
                fail(
                    f"{old['case_id']}: v0.2 changed frozen pilot field {key}"
                )

    case_ids = [case.get("case_id") for case in cases]
    if len(case_ids) != len(set(case_ids)):
        fail("duplicate case_id in cases.v0.2.json")
    if case_ids != [f"ctx-{index:03d}" for index in range(1, 13)]:
        fail("case IDs must be ctx-001 through ctx-012 in order")

    required_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for case in cases:
        case_id = case["case_id"]
        snapshot = case.get("corpus_snapshot")
        if snapshot not in snapshot_ids:
            fail(f"{case_id}: unknown corpus_snapshot {snapshot!r}")

        corpus = case.get("corpus")
        if not isinstance(corpus, list) or not corpus:
            fail(f"{case_id}: corpus must be a non-empty list")
        if len(corpus) != len(set(corpus)):
            fail(f"{case_id}: corpus contains duplicate IDs")
        if set(corpus) != snapshot_ids[snapshot]:
            fail(
                f"{case_id}: case corpus must equal the frozen snapshot IDs "
                f"for {snapshot}"
            )

        gold = case.get("gold")
        if not isinstance(gold, dict):
            fail(f"{case_id}: missing gold")
        required = gold.get("required")
        useful = gold.get("useful")
        irrelevant = gold.get("irrelevant")
        if not all(isinstance(value, list) for value in (required, useful, irrelevant)):
            fail(f"{case_id}: gold partitions must be lists")
        if len(required) != 1:
            fail(f"{case_id}: v0.2 requires exactly one required record")

        partitions = [set(required), set(useful), set(irrelevant)]
        if partitions[0] & partitions[1] or partitions[0] & partitions[2] or partitions[1] & partitions[2]:
            fail(f"{case_id}: gold partitions overlap")
        if set().union(*partitions) != set(corpus):
            fail(f"{case_id}: gold partitions must cover the full corpus")

        if not case.get("task") or not case.get("notes"):
            fail(f"{case_id}: task and notes are required")

        required_counts[snapshot][required[0]] += 1

    # Design invariant for v0.2: every record in each snapshot is the required
    # record in exactly one case. This avoids a required-label frequency prior.
    for snapshot, ids in snapshot_ids.items():
        counts = required_counts[snapshot]
        if set(counts) != ids:
            fail(
                f"{snapshot}: required-label coverage mismatch "
                f"counts={dict(counts)} expected={sorted(ids)}"
            )
        repeated = {record_id: count for record_id, count in counts.items() if count != 1}
        if repeated:
            fail(f"{snapshot}: each record must be required exactly once: {repeated}")

    print(
        "dataset v0.2 valid: "
        f"{len(cases)} cases, {len(snapshot_ids)} corpus snapshots, "
        "each record required exactly once within its snapshot"
    )


if __name__ == "__main__":
    main()

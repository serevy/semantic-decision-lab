#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from evaluate_context_selection import evaluate
from run_baseline import keyword_select, load_docs


ROOT = Path(__file__).resolve().parent
CASES = ROOT / "cases.v0.2.json"
REGISTRY = ROOT / "corpus-registry.v0.2.json"
RESULTS = ROOT / "results" / "baseline-v0.2"
TOP_K = 2


def load_snapshot_docs(registry: dict) -> dict[str, dict[str, str]]:
    snapshots = {}
    for name, spec in registry["snapshots"].items():
        snapshots[name] = load_docs(ROOT / spec["path"])
    return snapshots


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    cases = json.loads(CASES.read_text())
    registry = json.loads(REGISTRY.read_text())
    snapshots = load_snapshot_docs(registry)

    full = {}
    keyword = {}
    for case in cases:
        docs = snapshots[case["corpus_snapshot"]]
        available = [record_id for record_id in case["corpus"] if record_id in docs]
        if set(available) != set(case["corpus"]):
            raise SystemExit(
                f"{case['case_id']}: frozen corpus IDs are missing from snapshot"
            )

        full[case["case_id"]] = available
        subset = {record_id: docs[record_id] for record_id in available}
        keyword[case["case_id"]] = keyword_select(case["task"], subset, TOP_K)

    full_metrics = [
        evaluate(case, full[case["case_id"]])
        for case in cases
    ]
    keyword_metrics = [
        evaluate(case, keyword[case["case_id"]])
        for case in cases
    ]

    write_json(RESULTS / "full-context.selections.json", full)
    write_json(RESULTS / "full-context.metrics.json", full_metrics)
    write_json(RESULTS / "keyword-top2.selections.json", keyword)
    write_json(RESULTS / "keyword-top2.metrics.json", keyword_metrics)

    required_hits = sum(row["required_recall"] == 1.0 for row in keyword_metrics)
    print(f"keyword Top-2 required hit: {required_hits}/{len(keyword_metrics)}")
    print((RESULTS / "keyword-top2.metrics.json").read_text())


if __name__ == "__main__":
    main()

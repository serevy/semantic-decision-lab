#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from evaluate_context_selection import evaluate
from run_baseline import keyword_select, load_docs


ROOT = Path(__file__).resolve().parent
CASES = ROOT / "cases.v0.2.json"
REGISTRY = ROOT / "corpus-registry.v0.2.json"
BASELINE_EVIDENCE = ROOT / "results" / "baseline-v0.2-evidence.json"
EMBEDDING_REQUIRED_RANKS = ROOT / "evidence" / "embedding-required-ranks.v0.2.json"
RESULTS = ROOT / "results" / "topk-frontier-v0.2"
TOP_K_VALUES = (1, 2, 3, 4, 5)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def load_snapshot_docs(registry: dict) -> dict[str, dict[str, str]]:
    snapshots = {}
    for name, spec in registry["snapshots"].items():
        snapshots[name] = load_docs(ROOT / spec["path"])
    return snapshots


def summarize_keyword(cases: list[dict], snapshots: dict, top_k: int) -> dict:
    rows = []
    selections = {}
    for case in cases:
        docs = snapshots[case["corpus_snapshot"]]
        subset = {record_id: docs[record_id] for record_id in case["corpus"]}
        selected = keyword_select(case["task"], subset, top_k)
        selections[case["case_id"]] = selected
        rows.append(evaluate(case, selected))

    required_misses = [
        row["case_id"] for row in rows if row["required_recall"] < 1.0
    ]
    return {
        "top_k": top_k,
        "required_hits": len(rows) - len(required_misses),
        "case_count": len(rows),
        "mean_required_recall": mean(row["required_recall"] for row in rows),
        "mean_reduction_ratio": mean(row["reduction_ratio"] for row in rows),
        "mean_selected_count": mean(row["selected_count"] for row in rows),
        "required_misses": required_misses,
        "selections": selections,
    }


def summarize_embedding(cases: list[dict], ranks: dict, top_k: int) -> dict:
    rows = []
    for case in cases:
        case_id = case["case_id"]
        rank_row = ranks["cases"][case_id]
        required = case["gold"]["required"]
        if len(required) != 1:
            raise SystemExit(f"{case_id}: expected exactly one required record")
        if rank_row["required"] != required[0]:
            raise SystemExit(f"{case_id}: required-rank evidence does not match gold")

        corpus_count = len(case["corpus"])
        selected_count = min(top_k, corpus_count)
        required_hit = rank_row["rank"] <= selected_count
        rows.append(
            {
                "case_id": case_id,
                "required_rank": rank_row["rank"],
                "required_hit": required_hit,
                "selected_count": selected_count,
                "corpus_count": corpus_count,
                "reduction_ratio": 1.0 - selected_count / corpus_count,
            }
        )

    required_misses = [row["case_id"] for row in rows if not row["required_hit"]]
    return {
        "top_k": top_k,
        "required_hits": len(rows) - len(required_misses),
        "case_count": len(rows),
        "mean_required_recall": mean(1.0 if row["required_hit"] else 0.0 for row in rows),
        "mean_reduction_ratio": mean(row["reduction_ratio"] for row in rows),
        "mean_selected_count": mean(row["selected_count"] for row in rows),
        "required_misses": required_misses,
        "required_ranks": {row["case_id"]: row["required_rank"] for row in rows},
    }


def first_full_recall(frontier: list[dict]) -> int | None:
    for row in frontier:
        if row["required_hits"] == row["case_count"]:
            return row["top_k"]
    return None


def main() -> None:
    cases = json.loads(CASES.read_text())
    registry = json.loads(REGISTRY.read_text())
    baseline = json.loads(BASELINE_EVIDENCE.read_text())
    ranks = json.loads(EMBEDDING_REQUIRED_RANKS.read_text())

    if ranks["dataset_version"] != "0.2":
        raise SystemExit("embedding required-rank evidence must target dataset v0.2")
    if ranks["source"]["result_file_sha256"] != baseline["source"]["artifacts"][1]["result_file_sha256"]["multilingual-e5-small-top2.scores.json"]:
        raise SystemExit("embedding score-file hash does not match frozen baseline evidence")

    snapshots = load_snapshot_docs(registry)
    keyword_frontier = [summarize_keyword(cases, snapshots, k) for k in TOP_K_VALUES]
    embedding_frontier = [summarize_embedding(cases, ranks, k) for k in TOP_K_VALUES]

    frozen_keyword_top2 = baseline["arms"]["keyword_top2"]
    keyword_top2 = next(row for row in keyword_frontier if row["top_k"] == 2)
    if keyword_top2["required_hits"] != int(frozen_keyword_top2["required_hits"].split("/")[0]):
        raise SystemExit("keyword Top-2 required hit does not reproduce frozen evidence")
    if keyword_top2["selections"] != frozen_keyword_top2["selections"]:
        raise SystemExit("keyword Top-2 selections do not reproduce frozen evidence")

    frozen_embedding_top2 = baseline["arms"]["multilingual_e5_small_top2"]
    embedding_top2 = next(row for row in embedding_frontier if row["top_k"] == 2)
    if embedding_top2["required_hits"] != int(frozen_embedding_top2["required_hits"].split("/")[0]):
        raise SystemExit("embedding Top-2 required hit does not reproduce frozen evidence")
    if sorted(embedding_top2["required_misses"]) != sorted(frozen_embedding_top2["required_misses"]):
        raise SystemExit("embedding Top-2 misses do not reproduce frozen evidence")

    result = {
        "schema_version": 1,
        "dataset_version": "0.2",
        "metric_priority": "required-context recall versus context reduction",
        "top_k_values": list(TOP_K_VALUES),
        "full_context_control": {
            "required_hits": 12,
            "case_count": 12,
            "mean_required_recall": 1.0,
            "mean_reduction_ratio": 0.0,
        },
        "keyword": {
            "method": "frozen normalized token overlap",
            "frontier": keyword_frontier,
            "minimum_top_k_for_full_required_recall_within_tested_range": first_full_recall(keyword_frontier),
        },
        "embedding": {
            "method": "frozen multilingual-e5-small score ordering from PR #65 artifact",
            "model": ranks["source"]["model"],
            "model_revision": ranks["source"]["model_revision"],
            "frontier": embedding_frontier,
            "minimum_top_k_for_full_required_recall_within_tested_range": first_full_recall(embedding_frontier),
        },
        "interpretation_limits": [
            "This replays only selection budget over frozen v0.2 evidence; it does not tune a provider or change gold.",
            "Keyword and embedding secondary quality metrics are not compared here; this slice targets the highest-priority required-recall/reduction frontier.",
            "The bounded 12-case dataset is diagnostic and does not establish population-level superiority.",
        ],
    }

    write_json(RESULTS / "frontier.json", result)

    print("Top-k required-recall / reduction frontier")
    for arm_name, frontier in (("keyword", keyword_frontier), ("embedding", embedding_frontier)):
        print(f"[{arm_name}]")
        for row in frontier:
            print(
                f"k={row['top_k']} required={row['required_hits']}/{row['case_count']} "
                f"mean_reduction={row['mean_reduction_ratio']:.6f} "
                f"misses={','.join(row['required_misses']) or '-'}"
            )
        print(f"minimum k for full required recall: {first_full_recall(frontier)}")


if __name__ == "__main__":
    main()

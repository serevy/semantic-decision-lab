#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def ratio(num, den):
    return 1.0 if den == 0 else num / den

def evaluate(case, selected):
    selected = set(selected)
    corpus = set(case["corpus"])
    unknown = sorted(selected - corpus)
    selected &= corpus
    gold = case["gold"]
    required = set(gold["required"])
    useful = set(gold["useful"])
    irrelevant = set(gold["irrelevant"])
    return {
        "case_id": case["case_id"],
        "selected": sorted(selected),
        "unknown": unknown,
        "required_recall": ratio(len(selected & required), len(required)),
        "useful_recall": ratio(len(selected & useful), len(useful)),
        "irrelevant_rate": ratio(len(selected & irrelevant), len(selected)),
        "selection_precision": ratio(len(selected & (required | useful)), len(selected)),
        "selected_count": len(selected),
        "corpus_count": len(corpus),
        "reduction_ratio": 1.0 - ratio(len(selected), len(corpus)),
    }

def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: evaluate_context_selection.py CASES.json SELECTIONS.json")
    cases = json.loads(Path(sys.argv[1]).read_text())
    selections = json.loads(Path(sys.argv[2]).read_text())
    by_id = {c["case_id"]: c for c in cases}
    results = []
    for case_id, selected in selections.items():
        if case_id not in by_id:
            raise SystemExit(f"unknown case_id: {case_id}")
        results.append(evaluate(by_id[case_id], selected))
    print(json.dumps(results, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()

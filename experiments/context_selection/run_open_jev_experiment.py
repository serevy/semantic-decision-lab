#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from evaluate_context_selection import evaluate
from open_jev_http_provider import OpenJevHttpProvider
from semantic_provider import select_top_k, validate_result


def load_docs(path: Path) -> dict[str, str]:
    docs = {}
    for file in sorted(path.glob("PDDR-*.md")):
        match = re.search(r"(PDDR-\d{4})", file.name)
        if match:
            docs[match.group(1)] = file.read_text()
    return docs


def serialize_result(result):
    return {
        "provider": result.provider,
        "abstained": result.abstained,
        "metadata": dict(result.metadata),
        "decisions": [
            {
                "pddr_id": d.pddr_id,
                "required_probability": d.required_probability,
                "useful_probability": d.useful_probability,
                "irrelevant_probability": d.irrelevant_probability,
                "label": d.label,
                "confidence": d.confidence,
                "metadata": dict(d.metadata),
            }
            for d in result.decisions
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cases")
    parser.add_argument("corpus_dir")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/decide")
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    cases = json.loads(Path(args.cases).read_text())
    docs = load_docs(Path(args.corpus_dir))
    provider = OpenJevHttpProvider(endpoint=args.endpoint)

    selections = {}
    raw_results = {}
    metrics = []

    for case in cases:
        available = {pddr_id: docs[pddr_id] for pddr_id in case["corpus"]}
        result = provider.classify(task=case["task"], records=available)
        validate_result(result, case["corpus"])
        selected = select_top_k(result, top_k=args.top_k)
        selections[case["case_id"]] = selected
        raw_results[case["case_id"]] = serialize_result(result)
        metrics.append(evaluate(case, selected))

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "selections.json").write_text(json.dumps(selections, indent=2, sort_keys=True) + "\n")
    (out / "provider-results.json").write_text(
        json.dumps(raw_results, indent=2, sort_keys=True) + "\n"
    )
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")

    print("=== selections ===")
    print(json.dumps(selections, indent=2, sort_keys=True))
    print("=== metrics ===")
    print(json.dumps(metrics, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

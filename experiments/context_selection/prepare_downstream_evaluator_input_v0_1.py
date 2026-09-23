#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUESTS = ROOT / "downstream-requests.v0.1.jsonl"
ALLOWED = {"A", "B", "C", "D", "ABSTAIN"}


def read_requests() -> dict[str, dict]:
    rows = {}
    for line in REQUESTS.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows[row["request_id"]] = row
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a validated raw-response envelope into the exact evaluator "
            "shape without consulting downstream gold."
        )
    )
    parser.add_argument("results", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    requests = read_requests()
    payload = json.loads(args.results.read_text())
    answers: dict[str, dict[str, dict[str, str]]] = {}

    for response in payload["responses"]:
        request_id = response["request_id"]
        frozen = requests[request_id]
        choice = response["choice"]
        if choice not in ALLOWED:
            raise SystemExit(f"{request_id}: invalid choice {choice!r}")
        answers.setdefault(frozen["arm"], {})[frozen["case_id"]] = {
            "choice": choice
        }

    output = {
        "run": payload["run"],
        "answers": answers,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(f"wrote evaluator input: {args.output}")


if __name__ == "__main__":
    main()

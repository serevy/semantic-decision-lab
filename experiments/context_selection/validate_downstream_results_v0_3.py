#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUESTS = ROOT / "downstream-requests.v0.3.jsonl"
ALLOWED = {"A", "B", "C", "D", "ABSTAIN"}


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument("--requests", type=Path, default=REQUESTS)
    args = parser.parse_args()

    requests = {row["request_id"]: row for row in read_jsonl(args.requests)}
    payload = json.loads(args.results.read_text())

    run = payload.get("run")
    if not isinstance(run, dict):
        raise SystemExit("results.run must be an object")
    for key in ("provider", "model", "executed_at", "sampling"):
        if key not in run:
            raise SystemExit(f"results.run missing {key}")

    responses = payload.get("responses")
    if not isinstance(responses, list):
        raise SystemExit("results.responses must be a list")
    if len(responses) != len(requests):
        raise SystemExit(f"expected {len(requests)} responses, got {len(responses)}")

    seen = set()
    for row in responses:
        request_id = row.get("request_id")
        if request_id not in requests:
            raise SystemExit(f"unknown request_id: {request_id}")
        if request_id in seen:
            raise SystemExit(f"duplicate request_id: {request_id}")
        seen.add(request_id)

        frozen = requests[request_id]
        if row.get("prompt_sha256") != frozen["prompt_sha256"]:
            raise SystemExit(f"{request_id}: prompt hash mismatch")
        if row.get("choice") not in ALLOWED:
            raise SystemExit(
                f"{request_id}: choice must be exactly one of {sorted(ALLOWED)}"
            )
        if "raw_response" not in row:
            raise SystemExit(f"{request_id}: raw_response is required")

    if seen != set(requests):
        raise SystemExit(f"missing responses: {sorted(set(requests) - seen)}")

    print(
        "downstream v0.3 result envelope valid: "
        f"{len(responses)} responses, one frozen prompt hash per request"
    )


if __name__ == "__main__":
    main()

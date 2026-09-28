#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REQUESTS=ROOT/"downstream-requests.v0.5.jsonl"
ALLOWED={"A","B","C","D","ABSTAIN"}

def read_jsonl(path:Path):
    rows=[]
    for no,line in enumerate(path.read_text().splitlines(),1):
        if not line.strip():
            continue
        try: rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{no}: invalid JSON: {exc}") from exc
    return rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("results",type=Path)
    ap.add_argument("--requests",type=Path,default=REQUESTS)
    args=ap.parse_args()

    requests={r["request_id"]:r for r in read_jsonl(args.requests)}
    payload=json.loads(args.results.read_text())
    run=payload.get("run")
    if not isinstance(run,dict):
        raise SystemExit("results.run must be an object")
    for key in ("provider","model","executed_at","sampling"):
        if key not in run:
            raise SystemExit(f"results.run missing {key}")

    responses=payload.get("responses")
    if not isinstance(responses,list) or len(responses)!=len(requests):
        raise SystemExit(f"expected {len(requests)} responses")

    seen=set()
    for row in responses:
        rid=row.get("request_id")
        if rid not in requests: raise SystemExit(f"unknown request_id: {rid}")
        if rid in seen: raise SystemExit(f"duplicate request_id: {rid}")
        seen.add(rid)
        if row.get("prompt_sha256")!=requests[rid]["prompt_sha256"]:
            raise SystemExit(f"{rid}: prompt hash mismatch")
        if row.get("choice") not in ALLOWED:
            raise SystemExit(f"{rid}: invalid choice")
        if "raw_response" not in row:
            raise SystemExit(f"{rid}: raw_response is required")

    print(f"downstream v0.5 result envelope valid: {len(responses)} responses")

if __name__=="__main__":
    main()

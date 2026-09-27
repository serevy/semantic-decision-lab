#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REQUESTS=ROOT/"downstream-requests.v0.5.jsonl"
ALLOWED={"A","B","C","D","ABSTAIN"}

def read_requests(path:Path):
    out={}
    for line in path.read_text().splitlines():
        if line.strip():
            row=json.loads(line); out[row["request_id"]]=row
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("results",type=Path)
    ap.add_argument("--requests",type=Path,default=REQUESTS)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    requests=read_requests(args.requests)
    payload=json.loads(args.results.read_text())
    answers={}
    for response in payload["responses"]:
        rid=response["request_id"]
        frozen=requests[rid]
        choice=response["choice"]
        if choice not in ALLOWED:
            raise SystemExit(f"{rid}: invalid choice")
        answers.setdefault(frozen["arm"],{})[frozen["case_id"]]={"choice":choice}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({"run":payload["run"],"answers":answers},indent=2,sort_keys=True)+"\n")
    print(f"wrote evaluator input: {args.output}")

if __name__=="__main__":
    main()

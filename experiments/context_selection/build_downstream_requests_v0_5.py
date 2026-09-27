#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CASES=ROOT/"downstream-cases.v0.5.json"
ARMS=ROOT/"downstream-arms.v0.5.json"
FIXTURES=ROOT/"downstream-counterfactual-fixtures.v0.5.json"
CONTRACT=ROOT/"downstream-evaluation-contract.v0.5.json"
REGISTRY=ROOT/"corpus-registry.v0.2.json"
DEFAULT_OUTPUT=ROOT/"downstream-requests.v0.5.jsonl"
MANIFEST=ROOT/"downstream-request-pack.v0.5.json"

PDDR_ID=re.compile(r"(PDDR-\d{4})")

def sha256_text(value:str)->str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def load_docs(path:Path)->dict[str,str]:
    docs={}
    for file in sorted(path.glob("PDDR-*.md")):
        m=PDDR_ID.search(file.name)
        if m:
            docs[m.group(1)]=file.read_text()
    return docs

def render_card(card:dict)->str:
    return (
        f"Status: {card['status']}\n"
        f"Decision: {card['decision']}\n"
        f"Rationale: {card['rationale']}"
    )

def render_pddrs(selected:list[str],docs:dict[str,str])->str:
    blocks=[]
    for record_id in sorted(selected):
        blocks.append(
            f"--- BEGIN {record_id} ---\n"
            f"{docs[record_id].rstrip()}\n"
            f"--- END {record_id} ---"
        )
    return "\n\n".join(blocks)

def render_task(case:dict)->str:
    return (
        f"Scenario: {case['scenario']}\n\n"
        f"Question: {case['question']}\n\n"
        "Options:\n"
        f"A: {case['choices']['A']}\n"
        f"B: {case['choices']['B']}\n"
        f"C: {case['choices']['C']}\n"
        f"D: {case['choices']['D']}"
    )

def build_rows()->list[dict]:
    cases=json.loads(CASES.read_text())
    arms=json.loads(ARMS.read_text())
    fixtures=json.loads(FIXTURES.read_text())
    contract=json.loads(CONTRACT.read_text())
    registry=json.loads(REGISTRY.read_text())["snapshots"]

    cards={}
    for pair in fixtures["pairs"]:
        for card in pair["cards"]:
            cards[card["card_id"]]=card

    snapshots={}
    for name,spec in registry.items():
        docs=load_docs(ROOT/spec["path"])
        if set(docs)!=set(spec["record_ids"]):
            raise SystemExit(f"{name}: corpus does not match frozen registry")
        snapshots[name]=docs

    by_id={c["case_id"]:c for c in cases}
    system=contract["prompt_contract"]["system"]
    rows=[]

    def add(arm_name:str,case_id:str,context_kind:str,selected:list[str],context:str):
        case=by_id[case_id]
        user=(
            "Decision Context records:\n\n"
            f"{context}\n\n"
            f"{render_task(case)}"
        )
        canonical=system+"\n\n--- USER ---\n"+user
        rows.append({
            "request_id":f"{arm_name}/{case_id}",
            "arm":arm_name,
            "case_id":case_id,
            "pair_id":case["pair_id"],
            "side":case["side"],
            "corpus_snapshot":case["corpus_snapshot"],
            "context_kind":context_kind,
            "selected_context":selected,
            "system":system,
            "user":user,
            "context_sha256":sha256_text(context),
            "prompt_sha256":sha256_text(canonical)
        })

    # Pair controls over all 12 matched cases.
    for case_id in arms["pair_controls"]["no_context"]["case_ids"]:
        add("no_context",case_id,"none",[],"(none)")
    for case_id in arms["pair_controls"]["correct_card"]["case_ids"]:
        case=by_id[case_id]
        card_id=case["gold"]["context_card"]
        add("correct_card",case_id,"normalized_card",[card_id],render_card(cards[card_id]))

    # Original PDDR Markdown controls/replays over the six real cases.
    for arm_name,spec in arms["real_side_controls"].items():
        for case_id in spec["case_ids"]:
            case=by_id[case_id]
            selected=spec["selections"][case_id]
            docs=snapshots[case["corpus_snapshot"]]
            if not set(selected).issubset(docs):
                raise SystemExit(f"{arm_name}/{case_id}: selection outside corpus")
            add(arm_name,case_id,"original_pddr_markdown",selected,render_pddrs(selected,docs))

    for arm_name,spec in arms["historical_retrieval"].items():
        for case_id in spec["case_ids"]:
            case=by_id[case_id]
            selected=spec["selections"][case_id]
            docs=snapshots[case["corpus_snapshot"]]
            if not set(selected).issubset(docs):
                raise SystemExit(f"{arm_name}/{case_id}: selection outside corpus")
            add(arm_name,case_id,"original_pddr_markdown",selected,render_pddrs(selected,docs))

    expected=12+12+6+6+6+6+6
    if len(rows)!=expected:
        raise SystemExit(f"expected {expected} requests, got {len(rows)}")
    ids=[r["request_id"] for r in rows]
    if len(ids)!=len(set(ids)):
        raise SystemExit("duplicate request_id")
    return rows

def serialize(rows:list[dict])->str:
    return "".join(
        json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n"
        for row in rows
    )

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,default=DEFAULT_OUTPUT)
    ap.add_argument("--check",action="store_true")
    args=ap.parse_args()

    rendered=serialize(build_rows())
    digest=sha256_text(rendered)
    count=len(rendered.splitlines())

    if args.check:
        manifest=json.loads(MANIFEST.read_text())
        if manifest["request_count"]!=count:
            raise SystemExit(f"request count mismatch: expected {manifest['request_count']}, got {count}")
        if manifest["request_file_sha256"]!=digest:
            raise SystemExit("downstream v0.5 request pack digest does not match frozen manifest")
        print(f"downstream v0.5 request pack valid: {count} requests, sha256={digest}")
        return

    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(rendered)
    print(f"wrote {count} requests to {args.output}; sha256={digest}")

if __name__=="__main__":
    main()

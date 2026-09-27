#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CASES=ROOT/"downstream-cases.v0.5.json"
ARMS=ROOT/"downstream-arms.v0.5.json"
CONTRACT=ROOT/"downstream-evaluation-contract.v0.5.json"
ALLOWED={"A","B","C","D","ABSTAIN"}

def choice_of(v):
    return v["choice"] if isinstance(v,dict) else v

def summarize(case_ids,answers,cases):
    correct=wrong=abstain=0
    details=[]
    for cid in case_ids:
        choice=choice_of(answers[cid])
        if choice not in ALLOWED:
            raise SystemExit(f"{cid}: invalid choice {choice!r}")
        gold=cases[cid]["gold"]["choice"]
        if choice==gold:
            outcome="correct"; correct+=1
        elif choice=="ABSTAIN":
            outcome="abstain"; abstain+=1
        else:
            outcome="wrong_action"; wrong+=1
        details.append({"case_id":cid,"choice":choice,"gold":gold,"outcome":outcome})
    n=len(case_ids)
    return {"correct":correct,"wrong_action":wrong,"abstain":abstain,
            "gold_action_accuracy":correct/n,"abstention_rate":abstain/n,"details":details}

def main():
    if len(sys.argv)!=2:
        raise SystemExit("usage: evaluate_downstream_v0_5.py RESULTS.json")
    cases={c["case_id"]:c for c in json.loads(CASES.read_text())}
    arms=json.loads(ARMS.read_text())
    contract=json.loads(CONTRACT.read_text())
    payload=json.loads(Path(sys.argv[1]).read_text())
    answers=payload["answers"]

    summaries={}
    for name,spec in arms["pair_controls"].items():
        summaries[name]=summarize(spec["case_ids"],answers[name],cases)
    for name,spec in arms["real_side_controls"].items():
        summaries[name]=summarize(spec["case_ids"],answers[name],cases)
    for name,spec in arms["historical_retrieval"].items():
        summaries[name]=summarize(spec["case_ids"],answers[name],cases)

    by_pair=defaultdict(list)
    for row in summaries["correct_card"]["details"]:
        by_pair[cases[row["case_id"]]["pair_id"]].append(row)
    flips=sum(
        len(rows)==2 and all(r["outcome"]=="correct" for r in rows) and rows[0]["choice"]!=rows[1]["choice"]
        for rows in by_pair.values()
    )

    required_ref={r["case_id"]:r["choice"] for r in summaries["required_full_pddr"]["details"]}
    coupling={}
    for name,spec in arms["historical_retrieval"].items():
        present=[]
        absent=[]
        for row in summaries[name]["details"]:
            cid=row["case_id"]
            required=cases[cid]["gold"]["required_record"]
            selected=spec["selections"][cid]
            enriched=dict(row)
            enriched["required_record"]=required
            enriched["required_record_present"]=required in selected
            enriched["preserves_required_only"]=row["choice"]==required_ref[cid]
            (present if enriched["required_record_present"] else absent).append(enriched)
        coupling[name]={
            "required_hits":len(present),
            "total":len(present)+len(absent),
            "required_hit_rate":len(present)/(len(present)+len(absent)),
            "accuracy_when_required_present":sum(r["outcome"]=="correct" for r in present)/len(present) if present else None,
            "gold_accuracy_when_required_absent":sum(r["outcome"]=="correct" for r in absent)/len(absent) if absent else None,
            "abstention_rate_when_required_absent":sum(r["outcome"]=="abstain" for r in absent)/len(absent) if absent else None,
            "wrong_action_rate_when_required_absent":sum(r["outcome"]=="wrong_action" for r in absent)/len(absent) if absent else None,
            "behavior_preservation_vs_required_only":sum(r["preserves_required_only"] for r in present+absent)/(len(present)+len(absent)),
            "details":present+absent
        }

    gate=contract["control_gate"]
    checks={
        "no_context_min_abstain":summaries["no_context"]["abstain"]>=gate["no_context_min_abstain"],
        "correct_card_min_correct":summaries["correct_card"]["correct"]>=gate["correct_card_min_correct"],
        "correct_card_min_pair_flips":flips>=gate["correct_card_min_pair_flips"],
        "required_full_pddr_min_correct":summaries["required_full_pddr"]["correct"]>=gate["required_full_pddr_min_correct"],
        "full_corpus_min_correct":summaries["full_corpus"]["correct"]>=gate["full_corpus_min_correct"]
    }

    print(json.dumps({
        "run":payload.get("run",{}),
        "summaries":summaries,
        "correct_card_matched_pair_flips":{"count":flips,"total":len(by_pair),"rate":flips/len(by_pair)},
        "historical_retrieval_coupling":coupling,
        "control_gate":{"checks":checks,"pass":all(checks.values())}
    },indent=2,sort_keys=True))

if __name__=="__main__":
    main()

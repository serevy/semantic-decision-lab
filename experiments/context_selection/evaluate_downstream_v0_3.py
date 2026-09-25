#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES = ROOT / "downstream-cases.v0.3.json"
ARMS = ROOT / "downstream-arms.v0.3.json"
FIXTURES = ROOT / "downstream-counterfactual-fixtures.v0.3.json"
CONTRACT = ROOT / "downstream-evaluation-contract.v0.3.json"
ALLOWED = {"A","B","C","D","ABSTAIN"}

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: evaluate_downstream_v0_3.py RESULTS.json")

    cases={c["case_id"]:c for c in json.loads(CASES.read_text())}
    arms=json.loads(ARMS.read_text())["arms"]
    fixtures=json.loads(FIXTURES.read_text())
    contract=json.loads(CONTRACT.read_text())
    payload=json.loads(Path(sys.argv[1]).read_text())
    answers=payload["answers"]

    if set(answers) != set(arms):
        raise SystemExit("result arm set mismatch")

    pair_cards={}
    card_to_choice={}
    for pair in fixtures["pairs"]:
        pair_cards[pair["pair_id"]] = {c["card_id"] for c in pair["cards"]}
    for case in cases.values():
        card_to_choice[case["gold"]["card_id"]] = case["gold"]["choice"]

    summaries={}
    for arm_name in arms:
        rows=answers[arm_name]
        if set(rows) != set(cases):
            raise SystemExit(f"{arm_name}: case coverage mismatch")
        correct=abstain=wrong=0
        details=[]
        for cid,case in cases.items():
            value=rows[cid]
            choice=value["choice"] if isinstance(value,dict) else value
            if choice not in ALLOWED:
                raise SystemExit(f"{arm_name}/{cid}: invalid choice {choice!r}")
            gold=case["gold"]["choice"]
            if choice == gold:
                outcome="correct"; correct+=1
            elif choice == "ABSTAIN":
                outcome="abstain"; abstain+=1
            else:
                outcome="wrong_action"; wrong+=1
            details.append({"case_id":cid,"pair_id":case["pair_id"],"choice":choice,"gold":gold,"outcome":outcome})
        n=len(cases)
        summaries[arm_name]={
            "correct":correct,
            "wrong_action":wrong,
            "abstain":abstain,
            "gold_action_accuracy":correct/n,
            "abstention_rate":abstain/n,
            "details":details
        }

    # Correct-context matched-pair flip: both members correct and choices differ.
    by_pair=defaultdict(list)
    for row in summaries["correct_context"]["details"]:
        by_pair[row["pair_id"]].append(row)
    correct_flips=0
    for pair_id,rows in by_pair.items():
        assert len(rows)==2
        if all(r["outcome"]=="correct" for r in rows) and rows[0]["choice"] != rows[1]["choice"]:
            correct_flips+=1

    # Wrong-context following: compare output with the sibling card's accepted choice.
    wrong_follow=0
    wrong_details=[]
    for cid,case in cases.items():
        supplied=arms["wrong_context"]["selections"][cid][0]
        expected=card_to_choice[supplied]
        observed=answers["wrong_context"][cid]["choice"] if isinstance(answers["wrong_context"][cid],dict) else answers["wrong_context"][cid]
        followed=observed==expected
        wrong_follow+=int(followed)
        wrong_details.append({"case_id":cid,"supplied_context_choice":expected,"observed":observed,"followed":followed})

    gate=contract["diagnostic_gate"]
    checks={
        "correct_context_min_correct": summaries["correct_context"]["correct"] >= gate["correct_context_min_correct"],
        "no_context_min_abstain": summaries["no_context"]["abstain"] >= gate["no_context_min_abstain"],
        "matched_pair_min_correct_flips": correct_flips >= gate["matched_pair_min_correct_flips"],
        "both_contexts_min_abstain": summaries["both_contexts"]["abstain"] >= gate["both_contexts_min_abstain"]
    }

    output={
        "run":payload.get("run",{}),
        "summaries":summaries,
        "matched_pair":{
            "correct_flip_count":correct_flips,
            "pair_count":len(by_pair),
            "correct_flip_rate":correct_flips/len(by_pair)
        },
        "wrong_context":{
            "supplied_context_follow_count":wrong_follow,
            "total":len(cases),
            "supplied_context_follow_rate":wrong_follow/len(cases),
            "details":wrong_details
        },
        "diagnostic_gate":{"checks":checks,"pass":all(checks.values())}
    }
    print(json.dumps(output,indent=2,sort_keys=True))

if __name__ == "__main__":
    main()

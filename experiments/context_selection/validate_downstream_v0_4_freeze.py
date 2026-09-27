#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def load(name):
    return json.loads((ROOT/name).read_text(encoding="utf-8"))

cases=load("downstream-cases.v0.4.json")
snapshots=load("downstream-snapshots.v0.4.json")["snapshots"]
fixtures=load("downstream-counterfactual-fixtures.v0.3.json")
contract=load("downstream-retrieval-contract.v0.4.json")

cards={}
pair_cards=defaultdict(set)
for pair in fixtures["pairs"]:
    for card in pair["cards"]:
        cards[card["card_id"]]=card
        pair_cards[pair["pair_id"]].add(card["card_id"])

assert len(cases)==12
assert set(snapshots)=={"snapshot-alpha","snapshot-beta"}
assert all(len(v)==6 for v in snapshots.values())
assert set(snapshots["snapshot-alpha"]).isdisjoint(snapshots["snapshot-beta"])
assert set(snapshots["snapshot-alpha"]) | set(snapshots["snapshot-beta"]) == set(cards)

by_pair=defaultdict(list)
gold_counts=Counter()
for c in cases:
    by_pair[c["pair_id"]].append(c)
    assert c["snapshot_id"] in snapshots
    required=c["gold"]["required_card"]
    assert required in snapshots[c["snapshot_id"]]
    assert required in pair_cards[c["pair_id"]]
    assert cards[required]["snapshot_id"] == c["snapshot_id"]
    assert c["gold"]["choice"] in {"A","B","C","D"}
    gold_counts[c["gold"]["choice"]]+=1

assert len(by_pair)==6
assert gold_counts==Counter({"A":3,"B":3,"C":3,"D":3})
for pair_id,rows in by_pair.items():
    assert len(rows)==2
    a,b=sorted(rows,key=lambda x:x["case_id"])
    assert a["scenario"]==b["scenario"]
    assert a["question"]==b["question"]
    assert a["choices"]==b["choices"]
    assert a["snapshot_id"] != b["snapshot_id"]
    assert a["gold"]["choice"] != b["gold"]["choice"]
    assert {a["gold"]["required_card"],b["gold"]["required_card"]} == pair_cards[pair_id]

sels=contract["selectors"]
assert sels["keyword_top1"]["top_k"]==1
assert sels["keyword_top2"]["top_k"]==2
assert sels["embedding_top1"]["top_k"]==1
assert sels["embedding_top2"]["top_k"]==2
assert sels["embedding_top1"]["model"]==sels["embedding_top2"]["model"]
assert sels["embedding_top1"]["model_revision"]==sels["embedding_top2"]["model_revision"]

print("downstream v0.4 retrieval freeze valid: 2 snapshots x 6 cards, 6 matched pairs / 12 cases")

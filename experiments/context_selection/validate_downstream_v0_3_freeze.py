#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))

cases = load("downstream-cases.v0.3.json")
fixtures = load("downstream-counterfactual-fixtures.v0.3.json")
arms = load("downstream-arms.v0.3.json")
contract = load("downstream-evaluation-contract.v0.3.json")

assert len(cases) == 12
assert len(fixtures["pairs"]) == 6
assert set(arms["arms"]) == {"no_context","correct_context","wrong_context","both_contexts"}

cards = {}
pair_cards = {}
for pair in fixtures["pairs"]:
    assert len(pair["cards"]) == 2
    ids = []
    kinds = set()
    for card in pair["cards"]:
        cid = card["card_id"]
        assert cid not in cards
        cards[cid] = card
        ids.append(cid)
        kinds.add(card["provenance"]["kind"])
        assert card["status"] == "accepted"
        assert card["decision"].strip()
        assert card["rationale"].strip()
    assert kinds == {"real-derived","synthetic-counterfactual"}
    pair_cards[pair["pair_id"]] = set(ids)

by_pair = defaultdict(list)
gold_counts = Counter()
for case in cases:
    by_pair[case["pair_id"]].append(case)
    assert set(case["choices"]) == {"A","B","C","D"}
    assert case["gold"]["choice"] in {"A","B","C","D"}
    assert case["gold"]["card_id"] in cards
    assert case["gold"]["card_id"] in pair_cards[case["pair_id"]]
    gold_counts[case["gold"]["choice"]] += 1

assert len(by_pair) == 6
assert gold_counts == Counter({"A":3,"B":3,"C":3,"D":3})
for pair_id, rows in by_pair.items():
    assert len(rows) == 2
    a,b = sorted(rows,key=lambda x:x["case_id"])
    assert a["scenario"] == b["scenario"]
    assert a["question"] == b["question"]
    assert a["choices"] == b["choices"]
    assert a["gold"]["choice"] != b["gold"]["choice"]
    assert a["gold"]["card_id"] != b["gold"]["card_id"]
    assert {a["gold"]["card_id"],b["gold"]["card_id"]} == pair_cards[pair_id]

case_ids={c["case_id"] for c in cases}
for arm_name, arm in arms["arms"].items():
    assert set(arm["selections"]) == case_ids

for case in cases:
    cid=case["case_id"]
    correct=case["gold"]["card_id"]
    siblings=pair_cards[case["pair_id"]] - {correct}
    assert len(siblings)==1
    wrong=next(iter(siblings))
    assert arms["arms"]["no_context"]["selections"][cid] == []
    assert arms["arms"]["correct_context"]["selections"][cid] == [correct]
    assert arms["arms"]["wrong_context"]["selections"][cid] == [wrong]
    assert set(arms["arms"]["both_contexts"]["selections"][cid]) == pair_cards[case["pair_id"]]

gate=contract["diagnostic_gate"]
assert gate["frozen_before_output"] is True
assert gate["correct_context_min_correct"] <= 12
assert gate["no_context_min_abstain"] <= 12
assert gate["matched_pair_min_correct_flips"] <= 6
assert gate["both_contexts_min_abstain"] <= 12

print(
    "downstream v0.3 freeze valid: "
    "6 matched pairs / 12 cases, byte-identical prompt-visible pair tasks, "
    f"balanced gold={dict(sorted(gold_counts.items()))}"
)

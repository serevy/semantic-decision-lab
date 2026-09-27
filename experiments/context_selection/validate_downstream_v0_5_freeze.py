#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def load(name):
    return json.loads((ROOT/name).read_text(encoding="utf-8"))

cases=load("downstream-cases.v0.5.json")
fixtures=load("downstream-counterfactual-fixtures.v0.5.json")
arms=load("downstream-arms.v0.5.json")
contract=load("downstream-evaluation-contract.v0.5.json")
old_arms=load("downstream-arms.v0.1.json")["arms"]
orig={c["case_id"]:c for c in load("cases.v0.2.json")}

assert len(cases)==12
assert len(fixtures["pairs"])==6
by_pair=defaultdict(list)
gold_counts=Counter()
real_by_source={}
for c in cases:
    by_pair[c["pair_id"]].append(c)
    gold_counts[c["gold"]["choice"]]+=1
    if c["side"]=="real":
        real_by_source[c["source_case_id"]]=c
        src=orig[c["source_case_id"]]
        assert c["gold"]["required_record"]==src["gold"]["required"][0]
        assert c["corpus_snapshot"]==src["corpus_snapshot"]
    else:
        assert c["gold"]["required_record"] is None

assert gold_counts==Counter({"A":3,"B":3,"C":3,"D":3})
assert len(by_pair)==6
for pair_id,rows in by_pair.items():
    assert len(rows)==2
    a,b=sorted(rows,key=lambda x:x["case_id"])
    assert a["scenario"]==b["scenario"]
    assert a["question"]==b["question"]
    assert a["choices"]==b["choices"]
    assert a["gold"]["choice"] != b["gold"]["choice"]
    assert {a["side"],b["side"]}=={"real","synthetic"}

expected_sources=contract["selected_source_cases"]
assert set(real_by_source)==set(expected_sources)
old_ds={"ctx-001":"ds-001","ctx-002":"ds-002","ctx-003":"ds-003","ctx-006":"ds-006","ctx-007":"ds-007","ctx-008":"ds-008"}
for source in expected_sources:
    real=real_by_source[source]
    rid=real["case_id"]
    src=orig[source]
    assert arms["real_side_controls"]["required_full_pddr"]["selections"][rid] == src["gold"]["required"]
    assert arms["real_side_controls"]["full_corpus"]["selections"][rid] == src["corpus"]
    for name in ("keyword_top2","embedding_first512_top2","embedding_chunked_top2"):
        assert arms["historical_retrieval"][name]["selections"][rid] == old_arms[name]["selections"][old_ds[source]]

for name,expected in contract["historical_expected_required_hits"].items():
    hits=0
    for source in expected_sources:
        real=real_by_source[source]
        rid=real["case_id"]
        required=real["gold"]["required_record"]
        hits += required in arms["historical_retrieval"][name]["selections"][rid]
    assert hits==expected["hits"], (name,hits,expected)

print("downstream v0.5 freeze valid: 6 matched pairs / 12 cases; historical retrieval hits 5/6, 4/6, 3/6")

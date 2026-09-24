#!/usr/bin/env python3
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))

cases = load("downstream-cases.v0.2.json")
audit = load("downstream-context-dependence-audit.v0.2.json")
contract = load("downstream-evaluation-contract.v0.2.json")
arms = load("downstream-arms.v0.2.json")

assert len(cases) == 12
case_ids = [c["case_id"] for c in cases]
assert len(case_ids) == len(set(case_ids))
assert case_ids == [f"ds2-{i:03d}" for i in range(1, 13)]

gold_counts = Counter()
for c in cases:
    assert set(c["choices"]) == {"A","B","C","D"}
    gold = c["gold"]["choice"]
    assert gold in {"A","B","C","D"}
    gold_counts[gold] += 1
    assert "PDDR-" not in c["scenario"]
    assert "PDDR-" not in c["question"]
    for text in c["choices"].values():
        assert "PDDR-" not in text
assert gold_counts == Counter({"A":3,"B":3,"C":3,"D":3})

assert len(audit) == 12
audit_by_id = {a["case_id"]: a for a in audit}
assert set(audit_by_id) == set(case_ids)
tension = 0
for c in cases:
    a = audit_by_id[c["case_id"]]
    plausible = a["no_context_plausible_choices"]
    assert len(set(plausible)) >= contract["context_dependence_audit"]["minimum_plausible_no_context_choices_per_case"]
    assert all(x in {"A","B","C","D"} for x in plausible)
    assert c["gold"]["choice"] in plausible
    assert a["required_record"] == c["gold"]["source_record"]
    assert a["decision_excerpt"].strip()
    assert a["context_dependency_reason"].strip()
    assert set(a["distractor_plausibility"]) == ({"A","B","C","D"} - {c["gold"]["choice"]})
    generic = a["generic_best_practice_choice"]
    if generic is not None:
        assert generic in {"A","B","C","D"}
        if generic != c["gold"]["choice"]:
            tension += 1
assert tension >= contract["context_dependence_audit"]["minimum_cases_with_generic_best_practice_tension"]

gate = contract["diagnostic_gate"]
assert gate["frozen_before_output"] is True
assert 0 <= gate["no_context_max_correct"] < 12
assert 0 < gate["required_only_min_correct"] <= 12
assert 0 < gate["full_context_min_correct"] <= 12
assert gate["required_only_minus_no_context_min_correct"] >= 1
assert gate["full_context_minus_no_context_min_correct"] >= 1

assert arms["dataset"] == contract["dataset"]
for arm_name, arm in arms["arms"].items():
    assert set(arm["selections"]) == set(case_ids), arm_name

print(
    "downstream v0.2 freeze valid: "
    f"{len(cases)} cases, balanced gold={dict(sorted(gold_counts.items()))}, "
    f"generic-tension cases={tension}, "
    f"gate=no_context<={gate['no_context_max_correct']}/12; "
    f"required_only>={gate['required_only_min_correct']}/12; "
    f"full_context>={gate['full_context_min_correct']}/12"
)

#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RETRIEVAL_CASES = ROOT / "cases.v0.2.json"
DOWNSTREAM_CASES = ROOT / "downstream-cases.v0.1.json"
ARMS = ROOT / "downstream-arms.v0.1.json"
CONTRACT = ROOT / "downstream-evaluation-contract.v0.1.json"

CHOICES = {"A", "B", "C", "D"}
PDDR_ID = re.compile(r"PDDR-\d{4}")


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    retrieval = {row["case_id"]: row for row in json.loads(RETRIEVAL_CASES.read_text())}
    downstream = json.loads(DOWNSTREAM_CASES.read_text())
    arms = json.loads(ARMS.read_text())
    contract = json.loads(CONTRACT.read_text())

    if len(downstream) != 12:
        fail(f"expected 12 downstream cases, got {len(downstream)}")
    if contract["dataset"] != DOWNSTREAM_CASES.name:
        fail("contract dataset mismatch")
    if contract["arms"] != ARMS.name:
        fail("contract arms mismatch")

    seen = set()
    label_counts = Counter()
    for case in downstream:
        case_id = case["case_id"]
        if case_id in seen:
            fail(f"duplicate case_id: {case_id}")
        seen.add(case_id)

        source_id = case["source_case_id"]
        source = retrieval.get(source_id)
        if source is None:
            fail(f"{case_id}: unknown source_case_id {source_id}")
        if case["corpus_snapshot"] != source["corpus_snapshot"]:
            fail(f"{case_id}: corpus snapshot mismatch")

        if set(case["choices"]) != CHOICES:
            fail(f"{case_id}: choices must be exactly A-D")
        gold = case["gold"]
        if gold["choice"] not in CHOICES:
            fail(f"{case_id}: invalid gold choice")
        label_counts[gold["choice"]] += 1

        required = source["gold"]["required"]
        if len(required) != 1 or gold["source_record"] != required[0]:
            fail(f"{case_id}: gold source record must match frozen required record")

        prompt_visible = "\n".join(
            [case["scenario"], case["question"], *case["choices"].values()]
        )
        if PDDR_ID.search(prompt_visible):
            fail(f"{case_id}: prompt-visible text leaks a PDDR id")
        if not case.get("rationale"):
            fail(f"{case_id}: missing rationale")

    if label_counts != Counter({"A": 3, "B": 3, "C": 3, "D": 3}):
        fail(f"gold choices are not balanced: {dict(label_counts)}")

    expected_arm_names = {
        "no_context",
        "required_only",
        "full_context",
        "keyword_top2",
        "embedding_first512_top2",
        "embedding_chunked_top2",
    }
    if set(arms["arms"]) != expected_arm_names:
        fail("unexpected downstream arm set")

    by_downstream = {row["case_id"]: row for row in downstream}
    for arm_name, arm in arms["arms"].items():
        selections = arm["selections"]
        if set(selections) != set(by_downstream):
            fail(f"{arm_name}: case coverage mismatch")
        for case_id, selected in selections.items():
            case = by_downstream[case_id]
            source = retrieval[case["source_case_id"]]
            if len(selected) != len(set(selected)):
                fail(f"{arm_name}/{case_id}: duplicate selected record")
            if not set(selected).issubset(set(source["corpus"])):
                fail(f"{arm_name}/{case_id}: selection outside frozen corpus")

            if arm_name == "no_context" and selected:
                fail(f"{case_id}: no_context must be empty")
            if arm_name == "required_only" and selected != [case["gold"]["source_record"]]:
                fail(f"{case_id}: required_only mismatch")
            if arm_name == "full_context" and selected != source["corpus"]:
                fail(f"{case_id}: full_context must match frozen corpus order")

    print(
        "downstream v0.1 valid: "
        "12 cases, balanced A-D gold, 6 frozen arms, no prompt-visible PDDR IDs"
    )


if __name__ == "__main__":
    main()

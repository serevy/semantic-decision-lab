#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CASES = ROOT / "downstream-cases.v0.1.json"
ARMS = ROOT / "downstream-arms.v0.1.json"
ALLOWED = {"A", "B", "C", "D", "ABSTAIN"}


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: evaluate_downstream_v0_1.py RESULTS.json")

    cases = {row["case_id"]: row for row in json.loads(CASES.read_text())}
    arm_spec = json.loads(ARMS.read_text())["arms"]
    result = json.loads(Path(sys.argv[1]).read_text())
    answers = result["answers"]

    if set(answers) != set(arm_spec):
        raise SystemExit("result arm set does not match frozen downstream arms")

    summaries = {}
    for arm_name in arm_spec:
        rows = answers[arm_name]
        if set(rows) != set(cases):
            raise SystemExit(f"{arm_name}: result case coverage mismatch")

        correct = wrong = abstain = 0
        details = []
        for case_id, case in cases.items():
            value = rows[case_id]
            choice = value["choice"] if isinstance(value, dict) else value
            if choice not in ALLOWED:
                raise SystemExit(f"{arm_name}/{case_id}: invalid choice {choice!r}")

            gold = case["gold"]["choice"]
            if choice == gold:
                outcome = "correct"
                correct += 1
            elif choice == "ABSTAIN":
                outcome = "abstain"
                abstain += 1
            else:
                outcome = "wrong_action"
                wrong += 1
            details.append(
                {
                    "case_id": case_id,
                    "choice": choice,
                    "gold": gold,
                    "outcome": outcome,
                }
            )

        n = len(cases)
        summaries[arm_name] = {
            "correct": correct,
            "wrong_action": wrong,
            "abstain": abstain,
            "gold_action_accuracy": correct / n,
            "wrong_action_rate": wrong / n,
            "abstention_rate": abstain / n,
            "details": details,
        }

    full = {
        row["case_id"]: row["choice"]
        for row in summaries["full_context"]["details"]
    }
    for arm_name, summary in summaries.items():
        choices = {row["case_id"]: row["choice"] for row in summary["details"]}
        summary["behavior_preservation_vs_full_context"] = (
            sum(choices[cid] == full[cid] for cid in cases) / len(cases)
        )

    output = {
        "run": result.get("run", {}),
        "summaries": summaries,
        "no_context_correct_rate_as_prompt_leakage_signal": summaries["no_context"][
            "gold_action_accuracy"
        ],
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

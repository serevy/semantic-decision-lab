#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES = ROOT / "downstream-cases.v0.2.json"
ARMS = ROOT / "downstream-arms.v0.2.json"
CONTRACT = ROOT / "downstream-evaluation-contract.v0.2.json"
ALLOWED = {"A", "B", "C", "D", "ABSTAIN"}


def ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: evaluate_downstream_v0_2.py RESULTS.json")

    cases = {row["case_id"]: row for row in json.loads(CASES.read_text())}
    arm_spec = json.loads(ARMS.read_text())["arms"]
    contract = json.loads(CONTRACT.read_text())
    result = json.loads(Path(sys.argv[1]).read_text())
    answers = result["answers"]

    if set(answers) != set(arm_spec):
        raise SystemExit("result arm set does not match frozen downstream arms")

    summaries = {}
    for arm_name, spec in arm_spec.items():
        rows = answers[arm_name]
        if set(rows) != set(cases):
            raise SystemExit(f"{arm_name}: result case coverage mismatch")

        correct = wrong = abstain = 0
        supported_correct = supported_total = 0
        unsupported_correct = unsupported_total = 0
        details = []

        for case_id, case in cases.items():
            value = rows[case_id]
            choice = value["choice"] if isinstance(value, dict) else value
            if choice not in ALLOWED:
                raise SystemExit(f"{arm_name}/{case_id}: invalid choice {choice!r}")

            gold = case["gold"]["choice"]
            required = case["gold"]["source_record"]
            selected = spec["selections"][case_id]
            required_present = required in selected

            if choice == gold:
                outcome = "correct"
                correct += 1
            elif choice == "ABSTAIN":
                outcome = "abstain"
                abstain += 1
            else:
                outcome = "wrong_action"
                wrong += 1

            if required_present:
                supported_total += 1
                if choice == gold:
                    supported_correct += 1
            else:
                unsupported_total += 1
                if choice == gold:
                    unsupported_correct += 1

            details.append(
                {
                    "case_id": case_id,
                    "choice": choice,
                    "gold": gold,
                    "outcome": outcome,
                    "required_record": required,
                    "required_record_present": required_present,
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
            "required_record_present_count": supported_total,
            "accuracy_when_required_record_present": ratio(supported_correct, supported_total),
            "accuracy_when_required_record_absent": ratio(unsupported_correct, unsupported_total),
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

    no_ctx = summaries["no_context"]
    no_ctx_commitments = len(cases) - no_ctx["abstain"]
    no_ctx["unsupported_commitment_count"] = no_ctx_commitments
    no_ctx["unsupported_commitment_rate"] = no_ctx_commitments / len(cases)
    no_ctx["answerability_success_count"] = no_ctx["abstain"]
    no_ctx["answerability_success_rate"] = no_ctx["abstention_rate"]

    gate = contract["diagnostic_gate"]
    gate_checks = {
        "no_context_max_correct": no_ctx["correct"] <= gate["no_context_max_correct"],
        "required_only_min_correct": summaries["required_only"]["correct"] >= gate["required_only_min_correct"],
        "full_context_min_correct": summaries["full_context"]["correct"] >= gate["full_context_min_correct"],
        "required_only_minus_no_context": (
            summaries["required_only"]["correct"] - no_ctx["correct"]
            >= gate["required_only_minus_no_context_min_correct"]
        ),
        "full_context_minus_no_context": (
            summaries["full_context"]["correct"] - no_ctx["correct"]
            >= gate["full_context_minus_no_context_min_correct"]
        ),
    }

    output = {
        "run": result.get("run", {}),
        "summaries": summaries,
        "answerability": {
            "no_context_expected_behavior": "ABSTAIN",
            "no_context_abstention_rate": no_ctx["abstention_rate"],
            "no_context_unsupported_commitment_rate": no_ctx["unsupported_commitment_rate"],
            "note": (
                "In v0.2, every no-context case is audited as project-policy "
                "unanswerable. A coincidentally correct A-D choice remains an "
                "unsupported commitment for this diagnostic."
            ),
        },
        "diagnostic_gate": {
            "checks": gate_checks,
            "pass": all(gate_checks.values()),
        },
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

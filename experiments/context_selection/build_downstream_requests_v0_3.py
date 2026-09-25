#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES = ROOT / "downstream-cases.v0.3.json"
ARMS = ROOT / "downstream-arms.v0.3.json"
FIXTURES = ROOT / "downstream-counterfactual-fixtures.v0.3.json"
CONTRACT = ROOT / "downstream-evaluation-contract.v0.3.json"
DEFAULT_OUTPUT = ROOT / "downstream-requests.v0.3.jsonl"
MANIFEST = ROOT / "downstream-request-pack.v0.3.json"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def render_card(card: dict) -> str:
    # Do not render card IDs, snapshot IDs, or provenance into model-visible context.
    return (
        f"Status: {card['status']}\n"
        f"Decision: {card['decision']}\n"
        f"Rationale: {card['rationale']}"
    )


def render_context(selected: list[str], cards: dict[str, dict], marker: str) -> str:
    if not selected:
        return marker
    return "\n\n---\n\n".join(render_card(cards[card_id]) for card_id in sorted(selected))


def render_task(case: dict, template: str) -> str:
    return template.format(
        scenario=case["scenario"],
        question=case["question"],
        A=case["choices"]["A"],
        B=case["choices"]["B"],
        C=case["choices"]["C"],
        D=case["choices"]["D"],
    )


def build_rows() -> list[dict]:
    cases = json.loads(CASES.read_text())
    arms = json.loads(ARMS.read_text())["arms"]
    fixtures = json.loads(FIXTURES.read_text())
    contract = json.loads(CONTRACT.read_text())

    cards: dict[str, dict] = {}
    for pair in fixtures["pairs"]:
        for card in pair["cards"]:
            cards[card["card_id"]] = card

    cases_by_id = {case["case_id"]: case for case in cases}
    prompt = contract["prompt_contract"]
    rows: list[dict] = []

    for arm_name, arm in arms.items():
        selections = arm["selections"]
        for case_id in sorted(cases_by_id):
            case = cases_by_id[case_id]
            selected = sorted(selections[case_id])
            unknown = set(selected) - set(cards)
            if unknown:
                raise SystemExit(f"{arm_name}/{case_id}: unknown cards: {sorted(unknown)}")

            context = render_context(selected, cards, prompt["no_context_marker"])
            task = render_task(case, prompt["user_template"])
            user = (
                f"{prompt['context_header']}\n\n"
                f"{context}\n\n"
                f"{task}"
            )
            system = prompt["system"]
            canonical_prompt = system + "\n\n--- USER ---\n" + user

            rows.append(
                {
                    "request_id": f"{arm_name}/{case_id}",
                    "arm": arm_name,
                    "case_id": case_id,
                    "pair_id": case["pair_id"],
                    "selected_cards": selected,
                    "system": system,
                    "user": user,
                    "context_sha256": sha256_text(context),
                    "prompt_sha256": sha256_text(canonical_prompt),
                }
            )

    expected = len(cases) * len(arms)
    if len(rows) != expected:
        raise SystemExit(f"expected {expected} rows, got {len(rows)}")
    return rows


def serialize(rows: list[dict]) -> str:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = serialize(build_rows())
    digest = sha256_text(rendered)
    count = len(rendered.splitlines())

    if args.check:
        manifest = json.loads(MANIFEST.read_text())
        if manifest["request_count"] != count:
            raise SystemExit(
                f"request count mismatch: expected {manifest['request_count']}, got {count}"
            )
        if manifest["request_file_sha256"] != digest:
            raise SystemExit("downstream v0.3 request pack digest does not match frozen manifest")
        print(f"downstream v0.3 request pack valid: {count} requests, sha256={digest}")
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered)
    print(f"wrote {count} requests to {args.output}; sha256={digest}")


if __name__ == "__main__":
    main()

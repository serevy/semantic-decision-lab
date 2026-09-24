#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES = ROOT / "downstream-cases.v0.2.json"
ARMS = ROOT / "downstream-arms.v0.2.json"
CONTRACT = ROOT / "downstream-evaluation-contract.v0.2.json"
REGISTRY = ROOT / "corpus-registry.v0.2.json"
DEFAULT_OUTPUT = ROOT / "downstream-requests.v0.2.jsonl"
MANIFEST = ROOT / "downstream-request-pack.v0.2.json"

PDDR_ID = re.compile(r"(PDDR-\d{4})")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_docs(path: Path) -> dict[str, str]:
    docs: dict[str, str] = {}
    for file in sorted(path.glob("PDDR-*.md")):
        match = PDDR_ID.search(file.name)
        if match:
            docs[match.group(1)] = file.read_text()
    return docs


def render_context(selected: list[str], docs: dict[str, str], marker: str) -> str:
    if not selected:
        return marker
    blocks = []
    for record_id in sorted(selected):
        blocks.append(
            f"--- BEGIN {record_id} ---\n"
            f"{docs[record_id].rstrip()}\n"
            f"--- END {record_id} ---"
        )
    return "\n\n".join(blocks)


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
    contract = json.loads(CONTRACT.read_text())
    registry = json.loads(REGISTRY.read_text())["snapshots"]

    cases_by_id = {case["case_id"]: case for case in cases}
    snapshots: dict[str, dict[str, str]] = {}
    for name, spec in registry.items():
        docs = load_docs(ROOT / spec["path"])
        if set(docs) != set(spec["record_ids"]):
            raise SystemExit(f"{name}: corpus does not match frozen registry")
        snapshots[name] = docs

    prompt = contract["prompt_contract"]
    rows: list[dict] = []

    for arm_name, arm in arms.items():
        selections = arm["selections"]
        for case_id in sorted(cases_by_id):
            case = cases_by_id[case_id]
            selected = sorted(selections[case_id])
            docs = snapshots[case["corpus_snapshot"]]
            if not set(selected).issubset(docs):
                raise SystemExit(f"{arm_name}/{case_id}: selection outside corpus")

            context = render_context(selected, docs, prompt["no_context_marker"])
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
                    "corpus_snapshot": case["corpus_snapshot"],
                    "selected_records": selected,
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
            raise SystemExit(
                "downstream v0.2 request pack digest does not match frozen manifest"
            )
        print(f"downstream v0.2 request pack valid: {count} requests, sha256={digest}")
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered)
    print(f"wrote {count} requests to {args.output}; sha256={digest}")


if __name__ == "__main__":
    main()

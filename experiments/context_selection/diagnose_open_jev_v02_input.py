#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import types
from collections import defaultdict
from pathlib import Path

from transformers import AutoTokenizer

from open_jev_independent_provider import build_independent_request


PINNED_REVISION = "78d3b3a171f24d8d9a8dea18e027f9d3373fda45"
MAX_LEN = 4096


def load_docs(path: Path) -> dict[str, str]:
    docs = {}
    for p in sorted(path.glob("PDDR-*.md")):
        if p.stem.startswith("PDDR-"):
            docs[p.stem[:9]] = p.read_text()
    return docs


def import_upstream_td_data(upstream: Path):
    torch_stub = types.ModuleType("torch")
    torch_utils_stub = types.ModuleType("torch.utils")
    torch_utils_data_stub = types.ModuleType("torch.utils.data")

    class Dataset:
        pass

    torch_utils_data_stub.Dataset = Dataset
    torch_utils_stub.data = torch_utils_data_stub
    torch_stub.utils = torch_utils_stub

    previous = {
        name: sys.modules.get(name)
        for name in ("torch", "torch.utils", "torch.utils.data")
    }
    sys.modules["torch"] = torch_stub
    sys.modules["torch.utils"] = torch_utils_stub
    sys.modules["torch.utils.data"] = torch_utils_data_stub

    sys.path.insert(0, str(upstream))
    try:
        import td_data
    finally:
        sys.path.remove(str(upstream))
        for name, module in previous.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    return td_data


def read_upstream_encoder_name(upstream: Path) -> str:
    source = (upstream / "model.py").read_text()
    match = re.search(r'^DEFAULT_ENCODER\s*=\s*["\']([^"\']+)["\']', source, re.M)
    if not match:
        raise RuntimeError("Could not read DEFAULT_ENCODER from pinned upstream model.py")
    return match.group(1)


def sha256_ints(values: list[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(int(value).to_bytes(4, "little", signed=False))
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cases")
    parser.add_argument("corpus_dir")
    parser.add_argument("--upstream-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    upstream = Path(args.upstream_dir).resolve()
    td_data = import_upstream_td_data(upstream)
    encoder_name = read_upstream_encoder_name(upstream)
    tok = AutoTokenizer.from_pretrained(encoder_name)
    _, qid, lid = td_data.add_markers(tok)

    cases = json.loads(Path(args.cases).read_text())
    docs = load_docs(Path(args.corpus_dir))

    results = []
    hashes_by_record: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for case in cases:
        for pddr_id in case["corpus"]:
            payload = build_independent_request(
                task=case["task"],
                pddr_id=pddr_id,
                record=docs[pddr_id],
                calibrated=True,
            )
            state = payload["state"]
            questions = payload["questions"]
            q = questions["relevance"]

            tail = [qid] + tok.encode(q["instructions"], add_special_tokens=False)
            for lab, desc in td_data.iter_labels(q):
                tail += [lid] + tok.encode(
                    td_data.label_text(lab, desc),
                    add_special_tokens=False,
                )

            budget = MAX_LEN - len(tail) - 2
            if budget < 32:
                raise SystemExit(
                    f"{case['case_id']} {pddr_id}: question tail leaves only {budget} "
                    "state tokens; upstream requires at least 32"
                )

            state_text = td_data.state_to_text(state)
            state_tokens = tok.encode(state_text, add_special_tokens=False)
            kept_state_tokens = state_tokens[:budget]
            dropped_state_tokens = max(0, len(state_tokens) - budget)
            if dropped_state_tokens:
                raise SystemExit(
                    f"{case['case_id']} {pddr_id}: full record does not fit; "
                    f"dropped_state_tokens={dropped_state_tokens}"
                )

            row = {
                "id": f"{case['case_id']}:{pddr_id}",
                "state": state,
                "questions": questions,
                "gold": {},
            }
            encoded = td_data.encode(
                row,
                tok,
                MAX_LEN,
                qid,
                lid,
                with_gold=False,
            )
            input_hash = sha256_ints(encoded["input_ids"])
            hashes_by_record[pddr_id].append((case["case_id"], input_hash))

            task_present = case["task"] in q["instructions"]
            if not task_present:
                raise SystemExit(f"{case['case_id']} {pddr_id}: task missing from question")

            results.append(
                {
                    "case_id": case["case_id"],
                    "pddr_id": pddr_id,
                    "question_tail_token_count": len(tail),
                    "state_token_count": len(state_tokens),
                    "state_budget": budget,
                    "kept_state_token_count": min(len(state_tokens), budget),
                    "dropped_state_token_count": dropped_state_tokens,
                    "task_in_question": True,
                    "input_ids_count": len(encoded["input_ids"]),
                    "input_ids_sha256": input_hash,
                }
            )

    cross_case_checks = {}
    for pddr_id, items in sorted(hashes_by_record.items()):
        hashes = [h for _, h in items]
        all_distinct = len(set(hashes)) == len(hashes)
        cross_case_checks[pddr_id] = {
            "cases": [{"case_id": c, "input_ids_sha256": h} for c, h in items],
            "all_case_inputs_distinct": all_distinct,
        }
        if not all_distinct:
            raise SystemExit(
                f"{pddr_id}: same record produced identical final input for different tasks"
            )

    output = {
        "experiment_version": "open-jev-v0.2",
        "provider_revision": PINNED_REVISION,
        "encoder": encoder_name,
        "max_len": MAX_LEN,
        "requests_checked": len(results),
        "all_tasks_in_question": all(r["task_in_question"] for r in results),
        "all_records_fully_preserved": all(
            r["dropped_state_token_count"] == 0 for r in results
        ),
        "cross_case_checks": cross_case_checks,
        "diagnostic": results,
    }

    Path(args.output).write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

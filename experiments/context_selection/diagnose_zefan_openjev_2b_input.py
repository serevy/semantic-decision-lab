#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from transformers import AutoTokenizer

from zefan_openjev_2b_provider import build_zefan_question


SOURCE_REVISION = "ed45657bf726c3b77408942830e5578f99df904e"
BASE_MODEL = "Qwen/Qwen3.5-2B"
BASE_REVISION = "15852e8c16360a2fea060d615a32b45270f8a8fc"
MAX_LENGTH = 4096


def load_docs(path: Path) -> dict[str, str]:
    docs = {}
    for p in sorted(path.glob("PDDR-*.md")):
        if p.stem.startswith("PDDR-"):
            docs[p.stem[:9]] = p.read_text()
    return docs


def combined_hash(rows: list[list[int]]) -> str:
    payload = json.dumps(rows, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cases")
    parser.add_argument("corpus_dir")
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source_dir = Path(args.source_dir).resolve()
    observed_revision = subprocess.check_output(
        ["git", "-C", str(source_dir), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    if observed_revision != SOURCE_REVISION:
        raise SystemExit(
            f"unexpected source revision: {observed_revision}; expected {SOURCE_REVISION}"
        )

    sys.path.insert(0, str(source_dir))
    try:
        from jev.api import candidate_prompts, compile_request
    finally:
        sys.path.remove(str(source_dir))

    tok = AutoTokenizer.from_pretrained(
        BASE_MODEL,
        revision=BASE_REVISION,
    )

    cases = json.loads(Path(args.cases).read_text())
    docs = load_docs(Path(args.corpus_dir))
    results = []
    hashes_by_record: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for case in cases:
        for pddr_id in case["corpus"]:
            state = docs[pddr_id]
            question = build_zefan_question(
                task=case["task"],
                pddr_id=pddr_id,
            )
            compiled = compile_request(
                state,
                {"relevance": question},
            )
            if len(compiled) != 1:
                raise SystemExit(
                    f"{case['case_id']} {pddr_id}: expected one compiled record"
                )
            record = compiled[0]
            if record.get("answer_keys") != ["required", "useful", "irrelevant"]:
                raise SystemExit(
                    f"{case['case_id']} {pddr_id}: candidate order changed: "
                    f"{record.get('answer_keys')}"
                )

            prompts = candidate_prompts(record)
            if len(prompts) != 3:
                raise SystemExit(
                    f"{case['case_id']} {pddr_id}: expected 3 candidate prompts, "
                    f"got {len(prompts)}"
                )

            encoded_rows = []
            prompt_rows = []
            for label, prompt in zip(record["answer_keys"], prompts):
                if state not in prompt:
                    raise SystemExit(
                        f"{case['case_id']} {pddr_id} {label}: PDDR text missing"
                    )
                if case["task"] not in prompt:
                    raise SystemExit(
                        f"{case['case_id']} {pddr_id} {label}: task text missing"
                    )
                if f"Proposed answer: {label}:" not in prompt:
                    raise SystemExit(
                        f"{case['case_id']} {pddr_id} {label}: candidate text missing"
                    )

                rendered = tok.apply_chat_template(
                    [{"role": "user", "content": prompt}],
                    tokenize=False,
                    add_generation_prompt=True,
                    enable_thinking=False,
                )
                input_ids = tok(
                    rendered,
                    truncation=False,
                )["input_ids"]
                if len(input_ids) > MAX_LENGTH:
                    raise SystemExit(
                        f"{case['case_id']} {pddr_id} {label}: "
                        f"{len(input_ids)} tokens exceeds max_length={MAX_LENGTH}"
                    )
                encoded_rows.append(input_ids)
                prompt_rows.append(
                    {
                        "label": label,
                        "input_ids_count": len(input_ids),
                        "input_ids_sha256": combined_hash([input_ids]),
                    }
                )

            input_hash = combined_hash(encoded_rows)
            hashes_by_record[pddr_id].append((case["case_id"], input_hash))
            results.append(
                {
                    "case_id": case["case_id"],
                    "pddr_id": pddr_id,
                    "candidate_count": len(prompts),
                    "candidate_inputs": prompt_rows,
                    "max_candidate_input_tokens": max(
                        row["input_ids_count"] for row in prompt_rows
                    ),
                    "max_length": MAX_LENGTH,
                    "task_present_in_all_candidates": True,
                    "record_present_in_all_candidates": True,
                    "all_candidate_text_present": True,
                    "combined_input_sha256": input_hash,
                }
            )

    cross_case_checks = {}
    for pddr_id, items in sorted(hashes_by_record.items()):
        hashes = [digest for _, digest in items]
        distinct = len(set(hashes)) == len(hashes)
        cross_case_checks[pddr_id] = {
            "cases": [
                {"case_id": case_id, "combined_input_sha256": digest}
                for case_id, digest in items
            ],
            "all_case_inputs_distinct": distinct,
        }
        if not distinct:
            raise SystemExit(
                f"{pddr_id}: identical final candidate inputs across different tasks"
            )

    output = {
        "experiment_version": "zefan-open-jev-2b-v0.1",
        "source_revision": SOURCE_REVISION,
        "base_model": BASE_MODEL,
        "base_revision": BASE_REVISION,
        "max_length": MAX_LENGTH,
        "requests_checked": len(results),
        "candidate_sequences_checked": sum(
            row["candidate_count"] for row in results
        ),
        "all_tasks_fully_preserved": all(
            row["task_present_in_all_candidates"] for row in results
        ),
        "all_records_fully_preserved": all(
            row["record_present_in_all_candidates"] for row in results
        ),
        "all_options_fully_preserved": all(
            row["all_candidate_text_present"] for row in results
        ),
        "all_candidates_within_max_length": all(
            row["max_candidate_input_tokens"] <= MAX_LENGTH
            for row in results
        ),
        "cross_case_checks": cross_case_checks,
        "diagnostic": results,
    }

    Path(args.output).write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n"
    )
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

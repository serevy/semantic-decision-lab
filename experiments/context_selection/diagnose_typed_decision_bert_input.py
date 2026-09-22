#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import types
from collections import defaultdict
from pathlib import Path

from huggingface_hub import snapshot_download
from transformers import AutoTokenizer

from typed_decision_bert_provider import CRITERIA, build_jevbert_question


SOURCE_REVISION = "f0994cd4c91e7516f0e2a8d9e04b71107c309642"
MODEL_ID = "MoritzLaurer/bge-m3-zeroshot-v2.0"
MODEL_REVISION = "9abf1c8aaeb82a2447809c20753ed0b106b76652"
MAX_SEQUENCE_TOKENS = 2048
TOKENIZER_DECLARED_LIMIT = 512

TOKENIZER_FILES = {
    "config.json": "5449085fe904cdb0715398c7abf7fd049c3fc057e06353aa6a4701a6180ae4a1",
    "sentencepiece.bpe.model": "cfc8146abe2a0488e9e2a0c56de7952f7c11ab059eca145a0a727afce0db2865",
    "special_tokens_map.json": "8c785abebea9ae3257b61681b4e6fd8365ceafde980c21970d001e834cf10835",
    "tokenizer.json": "6710678b12670bc442b99edc952c4d996ae309a7020c1fa0096dd245c2faf790",
    "tokenizer_config.json": "f90024142df07163e5e6c5b9a6ad7c8c68b22a9112af11e3db4559a9ff90f737",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_tokenizer_files(model_dir: Path) -> None:
    if not all((model_dir / name).is_file() for name in TOKENIZER_FILES):
        snapshot_download(
            repo_id=MODEL_ID,
            revision=MODEL_REVISION,
            local_dir=str(model_dir),
            allow_patterns=list(TOKENIZER_FILES),
        )
    for name, expected in TOKENIZER_FILES.items():
        path = model_dir / name
        if not path.is_file():
            raise SystemExit(f"missing pinned tokenizer artifact: {name}")
        observed = sha256_file(path)
        if observed != expected:
            raise SystemExit(
                f"{name} SHA-256 mismatch: {observed} != {expected}"
            )


def load_upstream(source_dir: Path):
    observed = subprocess.check_output(
        ["git", "-C", str(source_dir), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    if observed != SOURCE_REVISION:
        raise SystemExit(
            f"unexpected source revision: {observed}; expected {SOURCE_REVISION}"
        )

    sys.path.insert(0, str(source_dir / "src"))
    try:
        from jevbert.config import Limits
        from jevbert.contracts.validator import validate_request
        from jevbert.compiler.serializer_nli import compile_request

        # CI preflight only needs tokenizer-side helpers from backends/nli.py.
        # Avoid installing the full GPU PyTorch wheel solely to import those helpers.
        remove_torch_stub = False
        if importlib.util.find_spec("torch") is None:
            torch_stub = types.ModuleType("torch")
            torch_stub.__spec__ = importlib.util.spec_from_loader("torch", loader=None)
            torch_stub.float32 = object()
            torch_stub.float16 = object()
            torch_stub.bfloat16 = object()
            sys.modules["torch"] = torch_stub
            remove_torch_stub = True

        try:
            from jevbert.backends.nli import (
                escape_every_angle,
                escape_reserved,
                misplaced_control_token,
                normalizer_of,
                reserved_strings_for,
            )
        finally:
            if remove_torch_stub:
                sys.modules.pop("torch", None)
    finally:
        sys.path.remove(str(source_dir / "src"))

    return {
        "Limits": Limits,
        "validate_request": validate_request,
        "compile_request": compile_request,
        "escape_every_angle": escape_every_angle,
        "escape_reserved": escape_reserved,
        "misplaced_control_token": misplaced_control_token,
        "normalizer_of": normalizer_of,
        "reserved_strings_for": reserved_strings_for,
    }


def load_docs(path: Path) -> dict[str, str]:
    docs = {}
    for file in sorted(path.glob("PDDR-*.md")):
        docs[file.stem[:9]] = file.read_text()
    return docs


def hash_rows(rows: list[list[int]]) -> str:
    payload = json.dumps(rows, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cases")
    parser.add_argument("corpus_dir")
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source_dir = Path(args.source_dir).resolve()
    model_dir = Path(args.model_dir).resolve()
    ensure_tokenizer_files(model_dir)
    upstream = load_upstream(source_dir)

    tokenizer = AutoTokenizer.from_pretrained(
        model_dir,
        local_files_only=True,
        trust_remote_code=False,
        use_fast=True,
    )
    normalize = upstream["normalizer_of"](tokenizer)
    reserved = upstream["reserved_strings_for"](tokenizer)
    bos = int(tokenizer.bos_token_id if tokenizer.bos_token_id is not None else tokenizer.cls_token_id)
    eos = int(tokenizer.eos_token_id if tokenizer.eos_token_id is not None else tokenizer.sep_token_id)
    control_ids = frozenset(
        token_id
        for token_id in tokenizer.all_special_ids
        if token_id != tokenizer.unk_token_id
    )

    limits = upstream["Limits"](
        max_sequence_tokens=MAX_SEQUENCE_TOKENS,
        max_request_tokens=131072,
    )
    cases = json.loads(Path(args.cases).read_text())
    docs = load_docs(Path(args.corpus_dir))

    diagnostic = []
    hashes_by_record: dict[str, list[tuple[str, str]]] = defaultdict(list)
    over_declared_limit = 0
    max_observed = 0

    def encode_pair(premise: str, hypothesis: str) -> tuple[list[int], bool]:
        p_text = upstream["escape_reserved"](premise, normalize, reserved)
        h_text = upstream["escape_reserved"](hypothesis, normalize, reserved)
        p_ids = tokenizer(p_text, add_special_tokens=False)["input_ids"]
        h_ids = tokenizer(h_text, add_special_tokens=False)["input_ids"]
        ids = [bos, *p_ids, eos, eos, *h_ids, eos]
        fallback = False
        bad = upstream["misplaced_control_token"](
            ids,
            len(p_ids),
            bos_token_id=bos,
            eos_token_id=eos,
            control_ids=control_ids,
        )
        if bad is not None:
            fallback = True
            p_ids = tokenizer(
                upstream["escape_every_angle"](premise, normalize),
                add_special_tokens=False,
            )["input_ids"]
            h_ids = tokenizer(
                upstream["escape_every_angle"](hypothesis, normalize),
                add_special_tokens=False,
            )["input_ids"]
            ids = [bos, *p_ids, eos, eos, *h_ids, eos]
            bad = upstream["misplaced_control_token"](
                ids,
                len(p_ids),
                bos_token_id=bos,
                eos_token_id=eos,
                control_ids=control_ids,
            )
            if bad is not None:
                raise SystemExit(
                    "control token remained in data position after exact fallback escape"
                )
        return ids, fallback

    for case in cases:
        for pddr_id in case["corpus"]:
            state = docs[pddr_id]
            body = {
                "model": "jevbert-poc-nli-ja-en-0.2.0",
                "state": state,
                "questions": {
                    "relevance": build_jevbert_question(
                        task=case["task"],
                        pddr_id=pddr_id,
                    )
                },
            }
            validated = upstream["validate_request"](body, limits)
            compiled = upstream["compile_request"](validated)
            if len(compiled.questions) != 1:
                raise SystemExit(
                    f"{case['case_id']} {pddr_id}: expected one compiled question"
                )
            question = compiled.questions[0]
            if len(question.pairs) != 3:
                raise SystemExit(
                    f"{case['case_id']} {pddr_id}: expected 3 candidate pairs"
                )

            rows = []
            candidate_rows = []
            for label, pair in zip(question.option_keys, question.pairs, strict=True):
                if pair.premise != state:
                    raise SystemExit(
                        f"{case['case_id']} {pddr_id} {label}: complete PDDR not preserved"
                    )
                if case["task"] not in pair.hypothesis:
                    raise SystemExit(
                        f"{case['case_id']} {pddr_id} {label}: task missing"
                    )
                if label not in pair.hypothesis or CRITERIA[label] not in pair.hypothesis:
                    raise SystemExit(
                        f"{case['case_id']} {pddr_id} {label}: candidate text missing"
                    )

                ids, fallback = encode_pair(pair.premise, pair.hypothesis)
                count = len(ids)
                if count > MAX_SEQUENCE_TOKENS:
                    raise SystemExit(
                        f"{case['case_id']} {pddr_id} {label}: "
                        f"{count} > {MAX_SEQUENCE_TOKENS}; no truncation allowed"
                    )
                max_observed = max(max_observed, count)
                if count > TOKENIZER_DECLARED_LIMIT:
                    over_declared_limit += 1
                rows.append(ids)
                candidate_rows.append(
                    {
                        "label": label,
                        "input_ids_count": count,
                        "above_tokenizer_declared_512": count > TOKENIZER_DECLARED_LIMIT,
                        "fallback_escape_used": fallback,
                        "input_ids_sha256": hash_rows([ids]),
                    }
                )

            combined = hash_rows(rows)
            hashes_by_record[pddr_id].append((case["case_id"], combined))
            diagnostic.append(
                {
                    "case_id": case["case_id"],
                    "pddr_id": pddr_id,
                    "candidate_count": 3,
                    "candidate_inputs": candidate_rows,
                    "max_candidate_input_tokens": max(
                        row["input_ids_count"] for row in candidate_rows
                    ),
                    "combined_input_sha256": combined,
                }
            )

    cross_case = {}
    for pddr_id, items in sorted(hashes_by_record.items()):
        distinct = len({digest for _, digest in items}) == len(items)
        cross_case[pddr_id] = {
            "cases": [
                {"case_id": case_id, "combined_input_sha256": digest}
                for case_id, digest in items
            ],
            "all_case_inputs_distinct": distinct,
        }
        if not distinct:
            raise SystemExit(
                f"{pddr_id}: identical final inputs across different tasks"
            )

    output = {
        "experiment_version": "typed-decision-bert-v0.1",
        "source_revision": SOURCE_REVISION,
        "source_model": MODEL_ID,
        "source_model_revision": MODEL_REVISION,
        "max_sequence_tokens": MAX_SEQUENCE_TOKENS,
        "tokenizer_declared_model_max_length_reference": TOKENIZER_DECLARED_LIMIT,
        "tokenizer_runtime_model_max_length": tokenizer.model_max_length,
        "requests_checked": len(diagnostic),
        "candidate_sequences_checked": sum(
            row["candidate_count"] for row in diagnostic
        ),
        "all_candidates_within_server_limit": True,
        "sequences_above_tokenizer_declared_512": over_declared_limit,
        "max_observed_candidate_tokens": max_observed,
        "cross_case_checks": cross_case,
        "diagnostic": diagnostic,
    }
    Path(args.output).write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n"
    )
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import types
from pathlib import Path
from typing import Any, Mapping

from transformers import AutoTokenizer

from open_jev_http_provider import OpenJevHttpProvider


PINNED_REVISION = "78d3b3a171f24d8d9a8dea18e027f9d3373fda45"
MAX_LEN = 1024


def load_docs(path: Path) -> dict[str, str]:
    docs = {}
    for p in sorted(path.glob("PDDR-*.md")):
        if p.stem.startswith("PDDR-"):
            docs[p.stem[:9]] = p.read_text()
    return docs


def capture_payload(task: str, records: Mapping[str, str]) -> Mapping[str, Any]:
    captured: dict[str, Any] = {}

    def transport(endpoint: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        captured["payload"] = payload
        # Return a syntactically valid dummy response so classify() completes.
        return {
            pddr_id: {
                "label": "irrelevant",
                "confidence": 1.0,
                "probabilities": {
                    "required": 0.0,
                    "useful": 0.0,
                    "irrelevant": 1.0,
                },
            }
            for pddr_id in records
        }

    OpenJevHttpProvider(transport=transport).classify(task=task, records=records)
    return captured["payload"]


def import_upstream_td_data(upstream: Path):
    """Import upstream td_data without installing torch.

    td_data imports torch at module import time because its Dataset/collate helpers
    use it, but this diagnostic only calls pure-Python token packing helpers
    (add_markers/state_to_text/encode). Provide the minimum import-time stub
    instead of downloading a large framework that cannot affect this diagnostic.
    """
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
    model_source = (upstream / "model.py").read_text()
    match = re.search(r'^DEFAULT_ENCODER\s*=\s*["\']([^"\']+)["\']', model_source, re.M)
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
    for case in cases:
        records = {pddr_id: docs[pddr_id] for pddr_id in case["corpus"]}
        payload = capture_payload(case["task"], records)
        state = payload["state"]
        questions = payload["questions"]

        # Reconstruct the exact upstream budget calculation.
        qnames = sorted(questions)[: td_data.MAX_Q]
        tail: list[int] = []
        for qname in qnames:
            q = questions[qname]
            tail += [qid] + tok.encode(q["instructions"], add_special_tokens=False)
            for lab, desc in td_data.iter_labels(q):
                tail += [lid] + tok.encode(
                    td_data.label_text(lab, desc),
                    add_special_tokens=False,
                )

        state_text = td_data.state_to_text(state)
        state_tokens = tok.encode(state_text, add_special_tokens=False)
        budget = MAX_LEN - len(tail) - 2
        kept_state_tokens = state_tokens[:budget]
        kept_state_text = tok.decode(kept_state_tokens, skip_special_tokens=False)

        row = {
            "id": case["case_id"],
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

        task_tokens = tok.encode(case["task"], add_special_tokens=False)
        task_token_count = len(task_tokens)
        task_text_present_verbatim = case["task"] in kept_state_text

        results.append(
            {
                "case_id": case["case_id"],
                "state_json_key_order": list(json.loads(state_text).keys()),
                "state_token_count": len(state_tokens),
                "question_tail_token_count": len(tail),
                "state_budget": budget,
                "kept_state_token_count": len(kept_state_tokens),
                "dropped_state_token_count": max(0, len(state_tokens) - len(kept_state_tokens)),
                "task_token_count": task_token_count,
                "task_text_present_verbatim_after_truncation": task_text_present_verbatim,
                "kept_state_suffix": kept_state_text[-500:],
                "input_ids_sha256": sha256_ints(encoded["input_ids"]),
                "input_ids_count": len(encoded["input_ids"]),
            }
        )

    output = {
        "provider_revision": PINNED_REVISION,
        "encoder": encoder_name,
        "max_len": MAX_LEN,
        "diagnostic": results,
    }

    Path(args.output).write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

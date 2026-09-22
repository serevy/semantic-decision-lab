#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from statistics import mean

from sentence_transformers import SentenceTransformer

from run_embedding_experiment_v0_2 import (
    MODEL_NAME,
    MODEL_REVISION,
    load_docs,
)


ROOT = Path(__file__).resolve().parent
CASES = ROOT / "cases.v0.2.json"
REGISTRY = ROOT / "corpus-registry.v0.2.json"
RESULTS = ROOT / "results" / "embedding-input-diagnostics-v0.2"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def retained_char_end(tokenizer, text: str, max_length: int) -> int | None:
    if not getattr(tokenizer, "is_fast", False):
        return None

    encoded = tokenizer(
        text,
        add_special_tokens=True,
        truncation=True,
        max_length=max_length,
        return_offsets_mapping=True,
    )
    offsets = encoded.get("offset_mapping")
    if offsets is None:
        return None

    return max((end for start, end in offsets if end > start), default=0)


def inspect_text(model: SentenceTransformer, kind: str, key: str, text: str) -> dict:
    tokenizer = model.tokenizer
    effective_limit = int(model.max_seq_length)

    raw = tokenizer(
        text,
        add_special_tokens=True,
        truncation=False,
    )
    raw_ids = raw["input_ids"]
    raw_count = len(raw_ids)

    direct_truncated = tokenizer(
        text,
        add_special_tokens=True,
        truncation=True,
        max_length=effective_limit,
    )
    direct_count = len(direct_truncated["input_ids"])

    model_tokens = model.tokenize([text])
    model_count = int(model_tokens["input_ids"].shape[-1])
    if model_count != direct_count:
        raise SystemExit(
            f"{kind}:{key}: SentenceTransformer tokenized length {model_count} "
            f"does not match direct tokenizer truncation length {direct_count}"
        )

    char_end = retained_char_end(tokenizer, text, effective_limit)
    retained = text if char_end is None else text[:char_end]
    dropped = "" if char_end is None else text[char_end:]

    return {
        "kind": kind,
        "key": key,
        "text_sha256": sha256_text(text),
        "character_count": len(text),
        "raw_token_count": raw_count,
        "sentence_transformer_token_count": model_count,
        "effective_max_seq_length": effective_limit,
        "truncated": raw_count > model_count,
        "truncated_token_count": max(0, raw_count - model_count),
        "retained_character_end": char_end,
        "retained_character_count": len(retained) if char_end is not None else None,
        "dropped_character_count": len(dropped) if char_end is not None else None,
        "retained_text_sha256": sha256_text(retained) if char_end is not None else None,
        "dropped_text_sha256": sha256_text(dropped) if char_end is not None else None,
    }


def main() -> None:
    cases = json.loads(CASES.read_text())
    registry = json.loads(REGISTRY.read_text())

    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION)
    tokenizer = model.tokenizer

    rows = []

    for snapshot_name, spec in registry["snapshots"].items():
        docs = load_docs(ROOT / spec["path"])
        expected_ids = set(spec["record_ids"])
        if set(docs) != expected_ids:
            raise SystemExit(f"{snapshot_name}: frozen record IDs do not match loaded docs")
        for record_id in sorted(docs):
            rows.append(
                inspect_text(
                    model,
                    "passage",
                    f"{snapshot_name}:{record_id}",
                    f"passage: {docs[record_id]}",
                )
            )

    for case in cases:
        rows.append(
            inspect_text(
                model,
                "query",
                case["case_id"],
                f"query: {case['task']}",
            )
        )

    passages = [row for row in rows if row["kind"] == "passage"]
    queries = [row for row in rows if row["kind"] == "query"]

    result = {
        "schema_version": 1,
        "dataset_version": "0.2",
        "model": MODEL_NAME,
        "model_revision": MODEL_REVISION,
        "sentence_transformers_max_seq_length": int(model.max_seq_length),
        "tokenizer_class": tokenizer.__class__.__name__,
        "tokenizer_is_fast": bool(getattr(tokenizer, "is_fast", False)),
        "tokenizer_model_max_length": int(tokenizer.model_max_length),
        "prefixes": {
            "passage": "passage: ",
            "query": "query: ",
        },
        "summary": {
            "passage_count": len(passages),
            "passages_truncated": sum(row["truncated"] for row in passages),
            "query_count": len(queries),
            "queries_truncated": sum(row["truncated"] for row in queries),
            "passage_raw_tokens_min": min(row["raw_token_count"] for row in passages),
            "passage_raw_tokens_max": max(row["raw_token_count"] for row in passages),
            "passage_raw_tokens_mean": mean(row["raw_token_count"] for row in passages),
            "query_raw_tokens_min": min(row["raw_token_count"] for row in queries),
            "query_raw_tokens_max": max(row["raw_token_count"] for row in queries),
            "query_raw_tokens_mean": mean(row["raw_token_count"] for row in queries),
        },
        "inputs": rows,
        "interpretation_limits": [
            "This diagnostic measures the exact tokenizer/model stack used by the frozen embedding baseline; it does not rerun or change similarity scores.",
            "A truncation observation identifies missing input text, not its causal effect on retrieval quality.",
            "Offset-derived retained-character ranges are reported only when the tokenizer exposes fast offset mappings.",
        ],
    }

    write_json(RESULTS / "input-lengths.json", result)

    print(
        f"model={MODEL_NAME}@{MODEL_REVISION} "
        f"max_seq_length={model.max_seq_length} "
        f"tokenizer={tokenizer.__class__.__name__} "
        f"tokenizer_model_max_length={tokenizer.model_max_length}"
    )
    print(
        f"passages truncated: {result['summary']['passages_truncated']}/"
        f"{result['summary']['passage_count']} "
        f"raw_tokens={result['summary']['passage_raw_tokens_min']}.."
        f"{result['summary']['passage_raw_tokens_max']}"
    )
    print(
        f"queries truncated: {result['summary']['queries_truncated']}/"
        f"{result['summary']['query_count']} "
        f"raw_tokens={result['summary']['query_raw_tokens_min']}.."
        f"{result['summary']['query_raw_tokens_max']}"
    )
    for row in passages:
        print(
            f"{row['key']} raw={row['raw_token_count']} "
            f"used={row['sentence_transformer_token_count']} "
            f"truncated={row['truncated']} "
            f"dropped_chars={row['dropped_character_count']}"
        )


if __name__ == "__main__":
    main()

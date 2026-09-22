#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

from sentence_transformers import SentenceTransformer

from evaluate_context_selection import evaluate


ROOT = Path(__file__).resolve().parent
CASES = ROOT / "cases.v0.2.json"
REGISTRY = ROOT / "corpus-registry.v0.2.json"
CONDITION = ROOT / "embedding-chunked-condition.v0.2.json"
RESULTS = ROOT / "results" / "embedding-chunked-v0.2"


def load_docs(path: Path) -> dict[str, str]:
    docs = {}
    for file in sorted(path.glob("PDDR-*.md")):
        match = re.search(r"(PDDR-\d{4})", file.name)
        if match:
            docs[match.group(1)] = file.read_text()
    return docs


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def make_chunks(tokenizer, text: str, token_budget: int, overlap: int) -> list[dict]:
    if not getattr(tokenizer, "is_fast", False):
        raise SystemExit("chunked condition requires a fast tokenizer with offsets")
    if token_budget <= 0 or overlap < 0 or overlap >= token_budget:
        raise SystemExit("invalid chunk token budget/overlap")

    encoded = tokenizer(
        text,
        add_special_tokens=False,
        truncation=False,
        return_offsets_mapping=True,
    )
    offsets = encoded["offset_mapping"]
    if not offsets:
        return [{"index": 0, "token_start": 0, "token_end": 0, "char_start": 0, "char_end": 0, "text": ""}]

    step = token_budget - overlap
    chunks = []
    start = 0
    index = 0

    while start < len(offsets):
        end = min(start + token_budget, len(offsets))
        char_start = offsets[start][0]
        char_end = offsets[end - 1][1]
        chunk_text = text[char_start:char_end]
        chunks.append(
            {
                "index": index,
                "token_start": start,
                "token_end": end,
                "char_start": char_start,
                "char_end": char_end,
                "text": chunk_text,
            }
        )
        if end == len(offsets):
            break
        start += step
        index += 1

    if chunks[0]["char_start"] != 0:
        raise SystemExit("first chunk does not start at the beginning of the document")
    if chunks[-1]["char_end"] != len(text):
        raise SystemExit("last chunk does not reach the end of the document")
    for left, right in zip(chunks, chunks[1:]):
        if right["char_start"] > left["char_end"]:
            raise SystemExit("chunk windows leave a character gap")

    return chunks


def main() -> None:
    cases = json.loads(CASES.read_text())
    registry = json.loads(REGISTRY.read_text())
    condition = json.loads(CONDITION.read_text())

    model_spec = condition["model"]
    chunk_spec = condition["chunking"]
    selection_spec = condition["selection"]
    aggregation_spec = condition["aggregation"]

    model = SentenceTransformer(
        model_spec["name"],
        revision=model_spec["revision"],
    )
    tokenizer = model.tokenizer

    if not getattr(tokenizer, "is_fast", False):
        raise SystemExit("frozen condition requires a fast tokenizer")

    snapshots = {}
    chunk_manifest = {}

    for snapshot_name, spec in registry["snapshots"].items():
        docs = load_docs(ROOT / spec["path"])
        if set(docs) != set(spec["record_ids"]):
            raise SystemExit(f"{snapshot_name}: loaded docs do not match frozen registry")

        per_doc_embeddings = {}
        per_doc_chunks = {}

        for record_id in sorted(docs):
            chunks = make_chunks(
                tokenizer,
                docs[record_id],
                chunk_spec["content_token_budget"],
                chunk_spec["overlap_tokens"],
            )

            prefixed = []
            manifest_rows = []
            for chunk in chunks:
                passage = condition["encoding"]["passage_prefix"] + chunk["text"]
                token_count = len(
                    tokenizer(
                        passage,
                        add_special_tokens=True,
                        truncation=False,
                    )["input_ids"]
                )
                if token_count > model.max_seq_length:
                    raise SystemExit(
                        f"{snapshot_name}:{record_id}: chunk {chunk['index']} "
                        f"has {token_count} tokens > model max {model.max_seq_length}"
                    )
                prefixed.append(passage)
                manifest_rows.append(
                    {
                        "index": chunk["index"],
                        "token_start": chunk["token_start"],
                        "token_end": chunk["token_end"],
                        "char_start": chunk["char_start"],
                        "char_end": chunk["char_end"],
                        "prefixed_token_count": token_count,
                    }
                )

            embeddings = model.encode(
                prefixed,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            per_doc_embeddings[record_id] = embeddings
            per_doc_chunks[record_id] = manifest_rows

        snapshots[snapshot_name] = (docs, per_doc_embeddings, per_doc_chunks)
        chunk_manifest[snapshot_name] = per_doc_chunks

    selections = {}
    all_scores = {}

    for case in cases:
        docs, doc_embeddings, doc_chunks = snapshots[case["corpus_snapshot"]]
        available = set(case["corpus"])
        if available != set(docs):
            raise SystemExit(
                f"{case['case_id']}: case corpus does not match frozen snapshot"
            )

        query = condition["encoding"]["query_prefix"] + case["task"]
        query_tokens = len(
            tokenizer(query, add_special_tokens=True, truncation=False)["input_ids"]
        )
        if query_tokens > model.max_seq_length:
            raise SystemExit(
                f"{case['case_id']}: query exceeds model max sequence length"
            )

        query_embedding = model.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0]

        scored = []
        detailed = []
        for record_id in sorted(docs):
            chunk_embeddings = doc_embeddings[record_id]
            chunk_scores = [
                float(query_embedding @ chunk_embedding)
                for chunk_embedding in chunk_embeddings
            ]
            if aggregation_spec["document_score"] != "maximum chunk cosine similarity":
                raise SystemExit("unsupported frozen aggregation rule")
            best_index = max(
                range(len(chunk_scores)),
                key=lambda idx: (chunk_scores[idx], -idx),
            )
            document_score = chunk_scores[best_index]
            scored.append((document_score, record_id))
            detailed.append(
                {
                    "pddr_id": record_id,
                    "document_score": document_score,
                    "winning_chunk_index": best_index,
                    "chunk_scores": [
                        {
                            "chunk_index": idx,
                            "cosine_similarity": score,
                            "char_start": doc_chunks[record_id][idx]["char_start"],
                            "char_end": doc_chunks[record_id][idx]["char_end"],
                        }
                        for idx, score in enumerate(chunk_scores)
                    ],
                }
            )

        scored.sort(key=lambda item: (-item[0], item[1]))
        detailed.sort(key=lambda item: (-item["document_score"], item["pddr_id"]))

        top_k = selection_spec["top_k"]
        selections[case["case_id"]] = [
            record_id for _, record_id in scored[:top_k]
        ]
        all_scores[case["case_id"]] = detailed

    metrics = [
        evaluate(case, selections[case["case_id"]])
        for case in cases
    ]

    write_json(
        RESULTS / "multilingual-e5-small-chunked-top2.selections.json",
        selections,
    )
    write_json(
        RESULTS / "multilingual-e5-small-chunked-top2.scores.json",
        {
            "condition": condition,
            "model_max_seq_length": int(model.max_seq_length),
            "scores": all_scores,
        },
    )
    write_json(
        RESULTS / "multilingual-e5-small-chunked-top2.metrics.json",
        metrics,
    )
    write_json(
        RESULTS / "chunk-manifest.json",
        {
            "condition_id": condition["condition_id"],
            "model_max_seq_length": int(model.max_seq_length),
            "snapshots": chunk_manifest,
        },
    )

    required_hits = sum(row["required_recall"] == 1.0 for row in metrics)
    print(f"chunked embedding Top-2 required hit: {required_hits}/{len(metrics)}")
    for row in metrics:
        if row["required_recall"] < 1.0:
            print(
                f"MISS {row['case_id']}: selected={','.join(row['selected'])}"
            )
    print((RESULTS / "multilingual-e5-small-chunked-top2.metrics.json").read_text())


if __name__ == "__main__":
    main()

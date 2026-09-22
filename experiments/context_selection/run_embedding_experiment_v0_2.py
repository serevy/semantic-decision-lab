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
RESULTS = ROOT / "results" / "embedding-v0.2"

MODEL_NAME = "intfloat/multilingual-e5-small"
MODEL_REVISION = "fd1525a9fd15316a2d503bf26ab031a61d056e98"
TOP_K = 2


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


def main() -> None:
    cases = json.loads(CASES.read_text())
    registry = json.loads(REGISTRY.read_text())

    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION)

    snapshots = {}
    for snapshot_name, spec in registry["snapshots"].items():
        docs = load_docs(ROOT / spec["path"])
        doc_ids = sorted(docs)
        passages = [f"passage: {docs[record_id]}" for record_id in doc_ids]
        embeddings = model.encode(
            passages,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        snapshots[snapshot_name] = (docs, doc_ids, embeddings)

    selections = {}
    all_scores = {}

    for case in cases:
        docs, doc_ids, passage_embeddings = snapshots[case["corpus_snapshot"]]
        available = set(case["corpus"])
        if available != set(docs):
            raise SystemExit(
                f"{case['case_id']}: case corpus does not match frozen snapshot"
            )

        query_embedding = model.encode(
            [f"query: {case['task']}"],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0]

        scored = []
        for index, record_id in enumerate(doc_ids):
            score = float(query_embedding @ passage_embeddings[index])
            scored.append((score, record_id))

        scored.sort(key=lambda item: (-item[0], item[1]))
        selections[case["case_id"]] = [
            record_id for _, record_id in scored[:TOP_K]
        ]
        all_scores[case["case_id"]] = [
            {"pddr_id": record_id, "cosine_similarity": score}
            for score, record_id in scored
        ]

    metrics = [
        evaluate(case, selections[case["case_id"]])
        for case in cases
    ]

    write_json(RESULTS / "multilingual-e5-small-top2.selections.json", selections)
    write_json(
        RESULTS / "multilingual-e5-small-top2.scores.json",
        {
            "model": MODEL_NAME,
            "model_revision": MODEL_REVISION,
            "top_k": TOP_K,
            "query_prefix": "query: ",
            "passage_prefix": "passage: ",
            "scores": all_scores,
        },
    )
    write_json(RESULTS / "multilingual-e5-small-top2.metrics.json", metrics)

    required_hits = sum(row["required_recall"] == 1.0 for row in metrics)
    print(f"embedding Top-2 required hit: {required_hits}/{len(metrics)}")
    print((RESULTS / "multilingual-e5-small-top2.metrics.json").read_text())


if __name__ == "__main__":
    main()

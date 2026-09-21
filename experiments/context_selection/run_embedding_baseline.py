#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-small"
MODEL_REVISION = "fd1525a9fd15316a2d503bf26ab031a61d056e98"


def load_docs(path: Path):
    docs = {}
    for p in sorted(path.glob("PDDR-*.md")):
        m = re.search(r"(PDDR-\d{4})", p.name)
        if m:
            docs[m.group(1)] = p.read_text()
    return docs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cases")
    parser.add_argument("corpus_dir")
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--output-selections", required=True)
    parser.add_argument("--output-scores", required=True)
    args = parser.parse_args()

    cases = json.loads(Path(args.cases).read_text())
    docs = load_docs(Path(args.corpus_dir))

    model = SentenceTransformer(MODEL_NAME, revision=MODEL_REVISION)

    doc_ids = sorted(docs)
    passages = [f"passage: {docs[doc_id]}" for doc_id in doc_ids]
    passage_embeddings = model.encode(
        passages,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    selections = {}
    all_scores = {}

    for case in cases:
        available = set(case["corpus"])
        query_embedding = model.encode(
            [f"query: {case['task']}"],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )[0]

        scored = []
        for idx, doc_id in enumerate(doc_ids):
            if doc_id not in available:
                continue
            score = float(query_embedding @ passage_embeddings[idx])
            scored.append((score, doc_id))

        scored.sort(key=lambda item: (-item[0], item[1]))
        top = scored[: args.top_k]
        selections[case["case_id"]] = [doc_id for _, doc_id in top]
        all_scores[case["case_id"]] = [
            {"pddr_id": doc_id, "cosine_similarity": score}
            for score, doc_id in scored
        ]

    Path(args.output_selections).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_selections).write_text(
        json.dumps(selections, indent=2, sort_keys=True) + "\n"
    )
    Path(args.output_scores).write_text(
        json.dumps(
            {
                "model": MODEL_NAME,
                "model_revision": MODEL_REVISION,
                "top_k": args.top_k,
                "query_prefix": "query: ",
                "passage_prefix": "passage: ",
                "scores": all_scores,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()

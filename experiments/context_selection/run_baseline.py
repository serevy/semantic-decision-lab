#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

STOP = {
    "a","an","and","are","as","at","be","by","for","from","in","into","is","it",
    "of","on","or","that","the","their","this","to","using","we","which","with",
    "without","wants","need","needs","new","prior","decision","context","project"
}

def tokens(text):
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) >= 3 and t not in STOP}

def load_docs(path):
    docs = {}
    for p in sorted(Path(path).glob("PDDR-*.md")):
        m = re.search(r"(PDDR-\d{4})", p.name)
        if m:
            docs[m.group(1)] = p.read_text()
    return docs

def keyword_select(task, docs, top_k):
    q = tokens(task)
    scored = []
    for doc_id, text in docs.items():
        d = tokens(text)
        overlap = q & d
        score = len(overlap)
        scored.append((score, len(overlap), doc_id))
    scored.sort(key=lambda x: (-x[0], -x[1], x[2]))
    return [doc_id for score, _, doc_id in scored[:top_k] if score > 0]

def main():
    if len(sys.argv) != 5:
        raise SystemExit("usage: run_baseline.py CASES.json CORPUS_DIR MODE TOP_K")
    cases = json.loads(Path(sys.argv[1]).read_text())
    docs = load_docs(sys.argv[2])
    mode, top_k = sys.argv[3], int(sys.argv[4])
    if mode not in {"full", "keyword"}:
        raise SystemExit("MODE must be full or keyword")
    out = {}
    for case in cases:
        available = [x for x in case["corpus"] if x in docs]
        if mode == "full":
            out[case["case_id"]] = available
        else:
            subset = {k: docs[k] for k in available}
            out[case["case_id"]] = keyword_select(case["task"], subset, top_k)
    print(json.dumps(out, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()

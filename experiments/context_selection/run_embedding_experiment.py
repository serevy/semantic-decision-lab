#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results" / "embedding-v0.1"
SELECTIONS = RESULTS / "multilingual-e5-small-top2.selections.json"
SCORES = RESULTS / "multilingual-e5-small-top2.scores.json"
METRICS = RESULTS / "multilingual-e5-small-top2.metrics.json"

RESULTS.mkdir(parents=True, exist_ok=True)

subprocess.run(
    [
        sys.executable,
        str(ROOT / "run_embedding_baseline.py"),
        str(ROOT / "cases.v0.1.json"),
        str(ROOT / "corpus" / "pddr-kit-v0.1"),
        "--top-k",
        "2",
        "--output-selections",
        str(SELECTIONS),
        "--output-scores",
        str(SCORES),
    ],
    check=True,
)

with METRICS.open("w") as out:
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "evaluate_context_selection.py"),
            str(ROOT / "cases.v0.1.json"),
            str(SELECTIONS),
        ],
        check=True,
        stdout=out,
    )

print("=== embedding selections ===")
print(SELECTIONS.read_text())
print("=== embedding metrics ===")
print(METRICS.read_text())
print("=== embedding scores ===")
print(SCORES.read_text())

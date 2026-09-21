#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES = ROOT / "cases.v0.1.json"
CORPUS = ROOT / "corpus" / "pddr-kit-v0.1"
BASELINE = ROOT / "run_baseline.py"
EVAL = ROOT / "evaluate_context_selection.py"

def run(*args):
    return subprocess.check_output([sys.executable, *map(str, args)], text=True)

def main():
    outdir = ROOT / "results" / "baseline-v0.1"
    outdir.mkdir(parents=True, exist_ok=True)
    for name, mode, top_k in [
        ("full-context", "full", 7),
        ("keyword-top2", "keyword", 2),
    ]:
        selections = run(BASELINE, CASES, CORPUS, mode, top_k)
        selection_path = outdir / f"{name}.selections.json"
        selection_path.write_text(selections)
        metrics = run(EVAL, CASES, selection_path)
        (outdir / f"{name}.metrics.json").write_text(metrics)
        print(f"== {name} ==")
        print(metrics)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


UPSTREAM_REPO = "https://github.com/intikhab49/open-jev-typed-decision-engine.git"
UPSTREAM_REVISION = "78d3b3a171f24d8d9a8dea18e027f9d3373fda45"


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def require_gpu() -> None:
    if shutil.which("nvidia-smi") is None:
        raise SystemExit(
            "No NVIDIA GPU detected. In Colab choose Runtime -> Change runtime type -> T4 GPU."
        )
    run(["nvidia-smi"])


def wait_for_server(url: str, log_path: Path, timeout_s: int = 300) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if 200 <= response.status < 500:
                    return
        except Exception:
            pass
        time.sleep(2)

    tail = ""
    if log_path.exists():
        tail = "\n".join(log_path.read_text(errors="replace").splitlines()[-40:])
    raise SystemExit(f"Open Jev server did not become ready within {timeout_s}s.\n{tail}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-shot Colab/T4 runner for Experiment #2 Open Jev v0.1."
    )
    parser.add_argument(
        "--work-root",
        default="/content",
        help="Temporary work root for the upstream clone (default: /content).",
    )
    args = parser.parse_args()

    lab_root = Path(__file__).resolve().parents[2]
    work_root = Path(args.work_root).resolve()
    upstream = work_root / "open-jev-typed-decision-engine"
    results = lab_root / "experiments/context_selection/results/open-jev-v0.1"
    log_path = work_root / "open-jev-v0.1-server.log"

    require_gpu()

    if results.exists() and any(results.iterdir()):
        raise SystemExit(
            f"Refusing to overwrite existing first-run evidence: {results}. "
            "Version the experiment before rerunning."
        )

    if upstream.exists():
        raise SystemExit(
            f"{upstream} already exists. Use a fresh Colab runtime for the frozen first run."
        )

    run(["git", "clone", UPSTREAM_REPO, str(upstream)])
    run(["git", "checkout", UPSTREAM_REVISION], cwd=upstream)
    run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=upstream)

    run([sys.executable, "smoke_test.py", "--all"], cwd=upstream)

    run(
        [
            sys.executable,
            "02_train.py",
            "--epochs", "20",
            "--patience", "6",
            "--schedule", "cosine",
            "--bs", "4",
            "--accum", "4",
            "--max-len", "1024",
            "--lr", "3e-5",
            "--head-lr", "1e-3",
            "--brier", "1.0",
            "--config", "all",
            "--out", "jevlite.pt",
        ],
        cwd=upstream,
    )

    run(
        [
            sys.executable,
            "03_calibrate.py",
            "--ckpt", "jevlite.pt",
            "--bs", "8",
            "--config", "all",
        ],
        cwd=upstream,
    )

    checkpoint = upstream / "jevlite.pt"
    if not checkpoint.exists():
        raise SystemExit("Training completed without producing jevlite.pt")

    print("+ starting Open Jev server", flush=True)
    log_file = log_path.open("w")
    server = subprocess.Popen(
        [
            sys.executable,
            "05_serve.py",
            "--ckpt", "jevlite.pt",
            "--serve",
            "--port", "8000",
        ],
        cwd=upstream,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    try:
        wait_for_server("http://127.0.0.1:8000/docs", log_path)

        run(
            [
                sys.executable,
                str(lab_root / "experiments/context_selection/run_open_jev_experiment.py"),
                str(lab_root / "experiments/context_selection/cases.v0.1.json"),
                str(lab_root / "experiments/context_selection/corpus/pddr-kit-v0.1"),
                "--endpoint", "http://127.0.0.1:8000/decide",
                "--top-k", "2",
                "--provider-revision", UPSTREAM_REVISION,
                "--checkpoint-path", str(checkpoint),
                "--output-dir", str(results),
            ],
            cwd=lab_root,
        )
    finally:
        server.terminate()
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server.kill()
        log_file.close()

    print("\n=== Open Jev v0.1 complete ===")
    print(f"Results: {results}")
    print((results / "metrics.json").read_text())


if __name__ == "__main__":
    main()

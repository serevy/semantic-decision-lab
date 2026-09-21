#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


UPSTREAM_REPO = "https://github.com/intikhab49/open-jev-typed-decision-engine.git"
UPSTREAM_REVISION = "78d3b3a171f24d8d9a8dea18e027f9d3373fda45"
PREFERRED_V01_CHECKPOINT_SHA256 = "90f6e2766b6b1e9210d701340325b6379530046804ab53b88239fced40908115"


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def capture(cmd: list[str], *, cwd: Path | None = None) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def ensure_upstream(upstream: Path) -> tuple[Path, bool]:
    """Return checkpoint path and whether the exact v0.1 checkpoint was reused."""
    checkpoint = upstream / "jevlite.pt"

    if upstream.exists():
        if not (upstream / ".git").exists():
            raise SystemExit(f"{upstream} exists but is not the pinned upstream git checkout.")
        head = capture(["git", "rev-parse", "HEAD"], cwd=upstream)
        if head != UPSTREAM_REVISION:
            raise SystemExit(
                f"Existing upstream checkout is at {head}, expected {UPSTREAM_REVISION}. "
                "Use a fresh runtime or restore the pinned revision."
            )

        if checkpoint.exists():
            observed = sha256_file(checkpoint)
            if observed != PREFERRED_V01_CHECKPOINT_SHA256:
                raise SystemExit(
                    "Existing jevlite.pt is not the frozen v0.1 checkpoint. "
                    f"Observed {observed}; expected {PREFERRED_V01_CHECKPOINT_SHA256}. "
                    "Use a fresh runtime instead of silently changing the model."
                )
            print(
                "=== Reusing exact Open Jev v0.1 checkpoint ===\n"
                f"sha256={observed}",
                flush=True,
            )
            return checkpoint, True

        print("Pinned upstream checkout exists but checkpoint is absent; training it now.", flush=True)
    else:
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

    if not checkpoint.exists():
        raise SystemExit("Training completed without producing jevlite.pt")

    print(
        "=== New checkpoint trained for v0.2 run ===\n"
        f"sha256={sha256_file(checkpoint)}",
        flush=True,
    )
    return checkpoint, False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Colab/T4 runner for Experiment #2 Open Jev v0.2."
    )
    parser.add_argument("--work-root", default="/content")
    args = parser.parse_args()

    lab_root = Path(__file__).resolve().parents[2]
    work_root = Path(args.work_root).resolve()
    upstream = work_root / "open-jev-typed-decision-engine"
    results = lab_root / "experiments/context_selection/results/open-jev-v0.2"
    preflight = work_root / "open-jev-v0.2-input-preflight.json"
    log_path = work_root / "open-jev-v0.2-server.log"
    zip_path = work_root / "open-jev-v0.2-results"

    require_gpu()

    if results.exists() and any(results.iterdir()):
        raise SystemExit(
            f"Refusing to overwrite existing v0.2 evidence: {results}. "
            "Preserve it before any rerun."
        )

    checkpoint, reused = ensure_upstream(upstream)

    # Re-run the exact packing preflight in the same runtime and pinned upstream
    # immediately before inference.
    run(
        [
            sys.executable,
            str(lab_root / "experiments/context_selection/diagnose_open_jev_v02_input.py"),
            str(lab_root / "experiments/context_selection/cases.v0.1.json"),
            str(lab_root / "experiments/context_selection/corpus/pddr-kit-v0.1"),
            "--upstream-dir", str(upstream),
            "--output", str(preflight),
        ],
        cwd=lab_root,
    )

    preflight_json = json.loads(preflight.read_text())
    if preflight_json.get("requests_checked") != 21 or not preflight_json.get("all_tasks_in_question"):
        raise SystemExit("v0.2 packing preflight did not pass all 21 requests.")

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
                str(lab_root / "experiments/context_selection/run_open_jev_v02_experiment.py"),
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

    # Copy the preflight beside the run evidence before packaging.
    shutil.copy2(preflight, results / "input-preflight.json")
    archive = shutil.make_archive(str(zip_path), "zip", root_dir=results)

    print("\n=== Open Jev v0.2 complete ===")
    print(f"Checkpoint reused from v0.1: {reused}")
    print(f"Checkpoint SHA-256: {sha256_file(checkpoint)}")
    print(f"Results: {results}")
    print(f"ZIP: {archive}")
    print((results / "metrics.json").read_text())


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


SOURCE_REPO = "https://github.com/NandhaKishorM/laya.git"
SOURCE_REVISION = "42626c348753fbb17572a813127df2278a1ec527"
MODEL_ID = "convaiinnovations/laya-multilingual"
MODEL_REVISION = "4bb4d65403a3a7b8abd9e6876ccb5e75cf923b5c"
MODEL_SHA256 = "9d628fd971b700382ac6f65920a86f149777b2e748e0c955fb3b19695aa8f204"
MAX_LEN = 4096
HEAD_MAX_LEN = 256


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


def ensure_source(source: Path) -> None:
    if source.exists():
        if not (source / ".git").exists():
            raise SystemExit(f"{source} exists but is not a git checkout")
        head = capture(["git", "rev-parse", "HEAD"], cwd=source)
        if head != SOURCE_REVISION:
            raise SystemExit(
                f"Existing Laya checkout is at {head}, expected {SOURCE_REVISION}"
            )
        return

    run(["git", "clone", SOURCE_REPO, str(source)])
    run(["git", "checkout", "--detach", SOURCE_REVISION], cwd=source)


def ensure_model(model_dir: Path) -> None:
    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=MODEL_ID,
        revision=MODEL_REVISION,
        local_dir=str(model_dir),
    )
    checkpoint = model_dir / "model.safetensors"
    if not checkpoint.exists():
        raise SystemExit(f"model.safetensors missing after download: {checkpoint}")
    observed = sha256_file(checkpoint)
    if observed != MODEL_SHA256:
        raise SystemExit(
            f"model.safetensors SHA-256 mismatch: observed {observed}, expected {MODEL_SHA256}"
        )
    print(f"model.safetensors sha256={observed}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-shot Colab/T4 runner for Experiment #2 Laya multilingual v0.1."
    )
    parser.add_argument("--work-root", default="/content")
    args = parser.parse_args()

    lab_root = Path(__file__).resolve().parents[2]
    work_root = Path(args.work_root).resolve()
    source = work_root / "laya-source-v0.1"
    model_dir = work_root / "laya-multilingual-v0.1-model"
    preflight = work_root / "laya-multilingual-v0.1-input-preflight.json"
    results = lab_root / "experiments/context_selection/results/laya-multilingual-v0.1"
    zip_root = work_root / "laya-multilingual-v0.1-results"

    require_gpu()
    if results.exists() and any(results.iterdir()):
        raise SystemExit(
            f"Refusing to overwrite existing Laya evidence: {results}"
        )

    ensure_source(source)
    run([sys.executable, "-m", "pip", "install", "-e", str(source)])
    ensure_model(model_dir)

    run(
        [
            sys.executable,
            str(lab_root / "experiments/context_selection/diagnose_laya_multilingual_input.py"),
            str(lab_root / "experiments/context_selection/cases.v0.1.json"),
            str(lab_root / "experiments/context_selection/corpus/pddr-kit-v0.1"),
            "--source-dir", str(source),
            "--model-dir", str(model_dir),
            "--output", str(preflight),
        ],
        cwd=lab_root,
    )

    preflight_json = json.loads(preflight.read_text())
    if (
        preflight_json.get("requests_checked") != 21
        or not preflight_json.get("all_questions_fully_preserved")
        or not preflight_json.get("all_options_fully_preserved")
        or not preflight_json.get("all_records_fully_preserved")
    ):
        raise SystemExit(
            "Laya preflight did not preserve task + criteria + full PDDR for all 21 requests."
        )

    run(
        [
            sys.executable,
            str(lab_root / "experiments/context_selection/run_laya_multilingual_experiment.py"),
            str(lab_root / "experiments/context_selection/cases.v0.1.json"),
            str(lab_root / "experiments/context_selection/corpus/pddr-kit-v0.1"),
            "--model-dir", str(model_dir),
            "--source-revision", SOURCE_REVISION,
            "--model-revision", MODEL_REVISION,
            "--top-k", "2",
            "--max-len", str(MAX_LEN),
            "--head-max-len", str(HEAD_MAX_LEN),
            "--device", "cuda",
            "--output-dir", str(results),
        ],
        cwd=lab_root,
    )

    shutil.copy2(preflight, results / "input-preflight.json")
    archive = shutil.make_archive(str(zip_root), "zip", root_dir=results)

    print("\n=== Laya multilingual v0.1 complete ===")
    print(f"Results: {results}")
    print(f"ZIP: {archive}")
    print((results / "metrics.json").read_text())


if __name__ == "__main__":
    main()

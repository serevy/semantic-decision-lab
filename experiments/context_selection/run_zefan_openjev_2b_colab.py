#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


SOURCE_REPO = "https://github.com/Zefan-Cai/Open-Jev.git"
SOURCE_REVISION = "ed45657bf726c3b77408942830e5578f99df904e"
MODEL_ID = "ZefanCai/Open-Jev-2B"
MODEL_REVISION = "0c7aa498b1627be8da4acf34c863ff0ee0a92785"
BASE_REVISION = "15852e8c16360a2fea060d615a32b45270f8a8fc"
CHECKPOINT_SHA256 = "3076462e6356412082e79af909227b39b2863b90def79155ca0821aa506b7ded"
MAX_LENGTH = 4096


EXPECTED_FILES = {
    "package/checkpoint/adapter/adapter_model.safetensors":
        "2d23935b1a7380db444abac572c04646918ba794e59002d1588236182a3ca18f",
    "package/checkpoint/head.pt":
        "3532cd576c58d5ad5bf17c3e9f2df4be8c70e08c07fa6bb7fa673dcd7b401f2a",
    "package/checkpoint/model.json":
        "d985eafa4d635113ee8cc912e0512a95aac0bed3426e9256931235b75cb3d6c5",
    "package/checkpoint/temperature.json":
        "090fb330a616338210a924d1c370c934e934f30f53f92c8a52a5cc7852cadd99",
}


def run(cmd: list[str], *, cwd: Path | None = None, env=None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def capture(cmd: list[str], *, cwd: Path | None = None) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checkpoint_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for file in sorted(path.rglob("*")):
        if file.is_file():
            digest.update(str(file.relative_to(path)).encode() + b"\0")
            with file.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
    return digest.hexdigest()


def require_bf16_gpu() -> None:
    import torch

    if not torch.cuda.is_available():
        raise SystemExit(
            "CUDA GPU required. In Colab choose a GPU runtime."
        )
    name = torch.cuda.get_device_name(0)
    capability = torch.cuda.get_device_capability(0)
    print(
        f"GPU: {name} | capability={capability} | "
        f"bf16_supported={torch.cuda.is_bf16_supported()}",
        flush=True,
    )
    if not torch.cuda.is_bf16_supported():
        raise SystemExit(
            "Frozen Zefan Open-Jev 2B v0.1 preserves the upstream BF16 loader. "
            f"The current GPU ({name}) does not report BF16 support. "
            "Do not silently switch dtype; choose an L4, A100, or another "
            "BF16-capable CUDA runtime and rerun."
        )


def wait_for_server(url: str, log_path: Path, timeout_s: int = 1200) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                if 200 <= response.status < 500:
                    print(response.read().decode("utf-8", errors="replace"), flush=True)
                    return
        except Exception:
            pass
        time.sleep(3)

    tail = ""
    if log_path.exists():
        tail = "\n".join(log_path.read_text(errors="replace").splitlines()[-80:])
    raise SystemExit(
        f"Zefan Open-Jev server did not become ready within {timeout_s}s.\n{tail}"
    )


def ensure_source(source: Path) -> None:
    if source.exists():
        if not (source / ".git").exists():
            raise SystemExit(f"{source} exists but is not a git checkout")
        head = capture(["git", "rev-parse", "HEAD"], cwd=source)
        if head != SOURCE_REVISION:
            raise SystemExit(
                f"Existing source is at {head}, expected {SOURCE_REVISION}"
            )
        return

    run(["git", "clone", SOURCE_REPO, str(source)])
    run(["git", "checkout", "--detach", SOURCE_REVISION], cwd=source)


def ensure_model(model_dir: Path) -> Path:
    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=MODEL_ID,
        revision=MODEL_REVISION,
        local_dir=str(model_dir),
    )

    manifest_path = model_dir / "release-manifest.json"
    if not manifest_path.exists():
        raise SystemExit("release-manifest.json missing from pinned model snapshot")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("repo_id") != MODEL_ID:
        raise SystemExit(f"unexpected model repo id: {manifest.get('repo_id')}")
    if manifest.get("base_revision") != BASE_REVISION:
        raise SystemExit(
            f"unexpected base revision: {manifest.get('base_revision')}"
        )
    if manifest.get("packaged_inference_directory_sha256") != CHECKPOINT_SHA256:
        raise SystemExit(
            "release manifest packaged checkpoint digest does not match frozen value"
        )

    for relative, expected in EXPECTED_FILES.items():
        path = model_dir / relative
        if not path.exists():
            raise SystemExit(f"missing pinned model artifact: {relative}")
        observed = sha256_file(path)
        if observed != expected:
            raise SystemExit(
                f"{relative} SHA-256 mismatch: {observed} != {expected}"
            )

    checkpoint = model_dir / "package" / "checkpoint"
    observed_checkpoint = checkpoint_digest(checkpoint)
    if observed_checkpoint != CHECKPOINT_SHA256:
        raise SystemExit(
            "checkpoint directory digest mismatch: "
            f"{observed_checkpoint} != {CHECKPOINT_SHA256}"
        )

    print(f"checkpoint sha256={observed_checkpoint}", flush=True)
    return checkpoint


def cleanup_success(source: Path, model_dir: Path, hf_home: Path) -> None:
    print("\n=== Cleaning completed backend runtime ===", flush=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "-y", "open-jev"],
        check=False,
    )
    for path in (source, model_dir, hf_home):
        if path.exists():
            shutil.rmtree(path)
            print(f"removed {path}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-shot Colab runner for Experiment #2 Zefan Open-Jev 2B v0.1."
    )
    parser.add_argument("--work-root", default="/content")
    args = parser.parse_args()

    lab_root = Path(__file__).resolve().parents[2]
    work_root = Path(args.work_root).resolve()
    source = work_root / "zefan-open-jev-2b-v0.1-source"
    model_dir = work_root / "zefan-open-jev-2b-v0.1-model"
    hf_home = work_root / "zefan-open-jev-2b-v0.1-hf-cache"
    preflight = work_root / "zefan-open-jev-2b-v0.1-input-preflight.json"
    log_path = work_root / "zefan-open-jev-2b-v0.1-server.log"
    results = lab_root / "experiments/context_selection/results/zefan-open-jev-2b-v0.1"
    zip_root = work_root / "zefan-open-jev-2b-v0.1-results"

    if shutil.which("nvidia-smi") is None:
        raise SystemExit("No NVIDIA GPU detected.")
    run(["nvidia-smi"])

    if results.exists() and any(results.iterdir()):
        raise SystemExit(
            f"Refusing to overwrite existing Zefan Open-Jev evidence: {results}"
        )

    ensure_source(source)
    run([sys.executable, "-m", "pip", "install", "-e", str(source) + "[train]"])
    require_bf16_gpu()

    os.environ["HF_HOME"] = str(hf_home)
    checkpoint = ensure_model(model_dir)

    run(
        [
            sys.executable,
            str(lab_root / "experiments/context_selection/diagnose_zefan_openjev_2b_input.py"),
            str(lab_root / "experiments/context_selection/cases.v0.1.json"),
            str(lab_root / "experiments/context_selection/corpus/pddr-kit-v0.1"),
            "--source-dir", str(source),
            "--output", str(preflight),
        ],
        cwd=lab_root,
    )

    preflight_json = json.loads(preflight.read_text())
    if (
        preflight_json.get("requests_checked") != 21
        or preflight_json.get("candidate_sequences_checked") != 63
        or not preflight_json.get("all_tasks_fully_preserved")
        or not preflight_json.get("all_records_fully_preserved")
        or not preflight_json.get("all_options_fully_preserved")
        or not preflight_json.get("all_candidates_within_max_length")
    ):
        raise SystemExit(
            "Zefan Open-Jev preflight did not preserve all 21 x 3 candidate inputs."
        )

    server_env = {
        **os.environ,
        "HF_HOME": str(hf_home),
        "PYTHONUNBUFFERED": "1",
    }
    print("+ starting Zefan Open-Jev 2B server", flush=True)
    log_file = log_path.open("w")
    server = subprocess.Popen(
        [
            sys.executable,
            "-m", "jev.server",
            "--checkpoint", str(checkpoint),
            "--device", "cuda:0",
            "--max-length", str(MAX_LENGTH),
            "--batch-size", "1",
            "--no-prefix-cache",
            "--host", "127.0.0.1",
            "--port", "8791",
        ],
        cwd=source,
        env=server_env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    try:
        wait_for_server("http://127.0.0.1:8791/health", log_path)

        run(
            [
                sys.executable,
                str(lab_root / "experiments/context_selection/run_zefan_openjev_2b_experiment.py"),
                str(lab_root / "experiments/context_selection/cases.v0.1.json"),
                str(lab_root / "experiments/context_selection/corpus/pddr-kit-v0.1"),
                "--endpoint", "http://127.0.0.1:8791/v1/systemone",
                "--top-k", "2",
                "--source-revision", SOURCE_REVISION,
                "--model-revision", MODEL_REVISION,
                "--output-dir", str(results),
            ],
            cwd=lab_root,
            env=server_env,
        )
    finally:
        server.terminate()
        try:
            server.wait(timeout=30)
        except subprocess.TimeoutExpired:
            server.kill()
        log_file.close()

    shutil.copy2(preflight, results / "input-preflight.json")
    archive = shutil.make_archive(str(zip_root), "zip", root_dir=results)

    print("\n=== Zefan Open-Jev 2B v0.1 complete ===")
    print(f"Results: {results}")
    print(f"ZIP: {archive}")
    print((results / "metrics.json").read_text())

    cleanup_success(source, model_dir, hf_home)
    print("Backend runtime retired; evidence ZIP remains.", flush=True)


if __name__ == "__main__":
    main()

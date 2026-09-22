#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import yaml


SOURCE_REPO = "https://github.com/hawkymisc/typed-decision-bert.git"
SOURCE_REVISION = "f0994cd4c91e7516f0e2a8d9e04b71107c309642"
BUNDLE_ID = "jevbert-poc-nli-ja-en-0.2.0"


def run(cmd: list[str], *, cwd: Path | None = None, env=None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def capture(cmd: list[str], *, cwd: Path | None = None) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def server_log_tail(log_path: Path) -> str:
    if not log_path.exists():
        return ""
    return "\n".join(log_path.read_text(errors="replace").splitlines()[-100:])


def wait_for_server(
    url: str,
    log_path: Path,
    server: subprocess.Popen,
    timeout_s: int = 900,
) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        code = server.poll()
        if code is not None:
            raise SystemExit(
                "typed-decision-bert server exited before readiness "
                f"(exit={code}).\n{server_log_tail(log_path)}"
            )
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                if response.status == 200:
                    print(response.read().decode("utf-8", errors="replace"), flush=True)
                    return
        except Exception:
            pass
        time.sleep(3)
    raise SystemExit(
        f"typed-decision-bert server did not become ready within {timeout_s}s.\n"
        f"{server_log_tail(log_path)}"
    )


def ensure_source(source: Path) -> None:
    if source.exists():
        head = capture(["git", "rev-parse", "HEAD"], cwd=source)
        if head != SOURCE_REVISION:
            raise SystemExit(
                f"existing source revision {head} != frozen {SOURCE_REVISION}"
            )
        return
    run(["git", "clone", SOURCE_REPO, str(source)])
    run(["git", "checkout", "--detach", SOURCE_REVISION], cwd=source)


def require_cuda() -> dict[str, object]:
    import torch

    if not torch.cuda.is_available():
        raise SystemExit(
            "Frozen typed-decision-bert v0.1 run requires CUDA; choose a Colab GPU."
        )
    name = torch.cuda.get_device_name(0)
    capability = torch.cuda.get_device_capability(0)
    memory = torch.cuda.get_device_properties(0).total_memory
    print(
        f"GPU: {name} | capability={capability} | memory={memory / 2**30:.1f} GiB",
        flush=True,
    )
    return {
        "name": name,
        "capability": list(capability),
        "memory_bytes": int(memory),
    }


def make_cuda_config(source: Path) -> Path:
    original = source / "configs" / "jevbert.poc.yaml"
    payload = yaml.safe_load(original.read_text())
    payload["serving"]["device"] = "cuda"
    target = source / "configs" / "jevbert.semantic-lab.v0.1.yaml"
    target.write_text(yaml.safe_dump(payload, sort_keys=False))
    return target


def cleanup_success(source: Path, hf_home: Path) -> None:
    print("\n=== Cleaning completed backend runtime ===", flush=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "-y", "jevbert"],
        check=False,
    )
    for path in (source, hf_home):
        if path.exists():
            shutil.rmtree(path)
            print(f"removed {path}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-shot Colab runner for typed-decision-bert v0.1."
    )
    parser.add_argument("--work-root", default="/content")
    args = parser.parse_args()

    lab_root = Path(__file__).resolve().parents[2]
    work_root = Path(args.work_root).resolve()
    source = work_root / "typed-decision-bert-v0.1-source"
    hf_home = work_root / "typed-decision-bert-v0.1-hf-cache"
    preflight = work_root / "typed-decision-bert-v0.1-input-preflight.json"
    log_path = work_root / "typed-decision-bert-v0.1-server.log"
    results = (
        lab_root
        / "experiments/context_selection/results/typed-decision-bert-v0.1"
    )
    zip_root = work_root / "typed-decision-bert-v0.1-results"

    if shutil.which("nvidia-smi") is None:
        raise SystemExit("No NVIDIA GPU detected.")
    run(["nvidia-smi"])
    if results.exists() and any(results.iterdir()):
        raise SystemExit(
            f"Refusing to overwrite existing evidence directory: {results}"
        )

    ensure_source(source)
    run([sys.executable, "-m", "pip", "install", "-e", str(source)])
    gpu = require_cuda()

    os.environ["HF_HOME"] = str(hf_home)
    env = {
        **os.environ,
        "HF_HOME": str(hf_home),
        "PYTHONUNBUFFERED": "1",
    }

    run(
        [
            sys.executable,
            "-m", "jevbert",
            "fetch-model",
            "--manifests-dir", str(source / "manifests"),
            "--models-dir", str(source / "models"),
        ],
        cwd=source,
        env=env,
    )

    model_dir = source / "models" / "MoritzLaurer--bge-m3-zeroshot-v2.0"
    run(
        [
            sys.executable,
            str(
                lab_root
                / "experiments/context_selection/diagnose_typed_decision_bert_input.py"
            ),
            str(lab_root / "experiments/context_selection/cases.v0.1.json"),
            str(
                lab_root
                / "experiments/context_selection/corpus/pddr-kit-v0.1"
            ),
            "--source-dir", str(source),
            "--model-dir", str(model_dir),
            "--output", str(preflight),
        ],
        cwd=lab_root,
        env=env,
    )

    preflight_data = json.loads(preflight.read_text())
    if (
        preflight_data.get("requests_checked") != 21
        or preflight_data.get("candidate_sequences_checked") != 63
        or not preflight_data.get("all_candidates_within_server_limit")
    ):
        raise SystemExit("typed-decision-bert preflight did not validate 21 x 3 inputs")

    api_key = secrets.token_urlsafe(32)
    env["JEVBERT_API_KEYS"] = api_key
    config_path = make_cuda_config(source)

    print("+ starting typed-decision-bert server", flush=True)
    log_file = log_path.open("w")
    server = subprocess.Popen(
        [
            sys.executable,
            "-m", "jevbert",
            "serve",
            "--config", str(config_path),
            "--host", "127.0.0.1",
            "--port", "8765",
        ],
        cwd=source,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    try:
        wait_for_server(
            "http://127.0.0.1:8765/readyz",
            log_path,
            server,
        )
        run(
            [
                sys.executable,
                str(
                    lab_root
                    / "experiments/context_selection/run_typed_decision_bert_experiment.py"
                ),
                str(lab_root / "experiments/context_selection/cases.v0.1.json"),
                str(
                    lab_root
                    / "experiments/context_selection/corpus/pddr-kit-v0.1"
                ),
                "--base-url", "http://127.0.0.1:8765",
                "--api-key", api_key,
                "--top-k", "2",
                "--source-code-revision", SOURCE_REVISION,
                "--output-dir", str(results),
            ],
            cwd=lab_root,
            env=env,
        )
    finally:
        server.terminate()
        try:
            server.wait(timeout=30)
        except subprocess.TimeoutExpired:
            server.kill()
        log_file.close()

    shutil.copy2(preflight, results / "input-preflight.json")

    provenance_path = results / "provenance.json"
    provenance = json.loads(provenance_path.read_text())
    provenance["gpu"] = gpu
    provenance_path.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n"
    )

    archive = shutil.make_archive(str(zip_root), "zip", root_dir=results)
    print("\n=== typed-decision-bert v0.1 complete ===")
    print(f"Results: {results}")
    print(f"ZIP: {archive}")
    print((results / "metrics.json").read_text())
    print(
        "Preflight sequences above tokenizer-declared 512: "
        f"{preflight_data['sequences_above_tokenizer_declared_512']} / 63"
    )

    cleanup_success(source, hf_home)
    print("Backend runtime retired; evidence ZIP remains.", flush=True)


if __name__ == "__main__":
    main()

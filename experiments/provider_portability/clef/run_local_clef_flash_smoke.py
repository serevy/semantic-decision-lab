from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from contract import load_fixture, validate_response


ROOT = Path(__file__).resolve().parent


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_joint_schema_module(snapshot: Path):
    module_path = snapshot / "joint_schema_model.py"
    if not module_path.is_file():
        raise SystemExit(f"missing released joint_schema_model.py: {module_path}")
    spec = importlib.util.spec_from_file_location("clef_joint_schema_model", module_path)
    if spec is None or spec.loader is None:
        raise SystemExit("could not load joint_schema_model.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True)
    parser.add_argument(
        "--fixture",
        default=str(ROOT / "systemone-contract.v0.1.json"),
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-length", type=int, default=16384)
    args = parser.parse_args()

    snapshot = Path(args.snapshot).resolve()
    output = Path(args.output)
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing evidence: {output}")

    required_files = [
        "joint_schema_model.py",
        "joint_head.safetensors",
        "joint_head_config.json",
        "model.safetensors.index.json",
        "config.json",
    ]
    missing = [name for name in required_files if not (snapshot / name).is_file()]
    if missing:
        raise SystemExit(f"snapshot is incomplete: missing={missing}")

    fixture = load_fixture(args.fixture)
    request = json.loads(json.dumps(fixture["request"]))
    request["model"] = "clef-flash"

    module = load_joint_schema_module(snapshot)
    model, processor = module.load_release_model(str(snapshot), device="cuda")
    response = module.systemone(
        model,
        processor,
        request,
        max_length=args.max_length,
    )
    validate_response(
        response,
        request,
        probability_tolerance=float(
            fixture["contract_expectations"]["probability_tolerance_after_rounding"]
        ),
    )

    import torch
    import transformers

    evidence = {
        "schema_version": "0.1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "cloudflare-clef-local-release",
        "model": "clef-flash",
        "snapshot_path": str(snapshot),
        "joint_schema_model_sha256": sha256_file(snapshot / "joint_schema_model.py"),
        "joint_head_sha256": sha256_file(snapshot / "joint_head.safetensors"),
        "max_length": args.max_length,
        "runtime": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "cuda": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        },
        "request": request,
        "raw_response": response,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contract import load_fixture, validate_request, validate_response
from evidence_io import reserve_evidence, update_evidence


ROOT = Path(__file__).resolve().parent
HF_REPO = "Cloudflare/clef-flash"
APPROVED_REVISION_PREFIX = "17f0b0a"
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
FROZEN_MAX_LENGTH = 16384


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_approved_revision(revision: str) -> None:
    if not FULL_SHA_RE.fullmatch(revision):
        raise ValueError("hf revision must be a full 40-character lowercase commit SHA")
    if not revision.startswith(APPROVED_REVISION_PREFIX):
        raise ValueError(
            "hf revision does not match the discovery-time approved prefix "
            f"{APPROVED_REVISION_PREFIX}"
        )


def load_joint_schema_module(snapshot: Path):
    module_path = snapshot / "joint_schema_model.py"
    if not module_path.is_file():
        raise RuntimeError(f"missing released joint_schema_model.py: {module_path}")
    spec = importlib.util.spec_from_file_location("clef_joint_schema_model", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load joint_schema_model.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def inspect_state_encoding(
    module: Any,
    processor: Any,
    request: dict[str, Any],
    *,
    max_length: int,
) -> dict[str, Any]:
    tokenizer = processor.tokenizer
    rendered_state = module.render(request["state"])
    raw_state_tokens = len(
        tokenizer(rendered_state, add_special_tokens=False).input_ids
    )

    empty_request = copy.deepcopy(request)
    empty_request["state"] = ""
    empty_state_tokens = len(
        tokenizer(module.render(empty_request["state"]), add_special_tokens=False).input_ids
    )

    empty_encoded = module.encode_record(
        tokenizer,
        empty_request,
        max_length=max_length,
        processor=processor,
    )
    encoded = module.encode_record(
        tokenizer,
        request,
        max_length=max_length,
        processor=processor,
    )

    fixed_tokens = len(empty_encoded.input_ids) - empty_state_tokens
    retained_state_tokens = max(0, len(encoded.input_ids) - fixed_tokens)
    input_ids_json = json.dumps(
        list(encoded.input_ids),
        separators=(",", ":"),
    ).encode("utf-8")

    return {
        "max_length": max_length,
        "state_tokens_original": raw_state_tokens,
        "state_tokens_retained": retained_state_tokens,
        "state_truncated": retained_state_tokens < raw_state_tokens,
        "encoded_input_tokens": len(encoded.input_ids),
        "encoded_input_ids_sha256": hashlib.sha256(input_ids_json).hexdigest(),
    }


def runtime_snapshot(torch: Any, transformers: Any) -> dict[str, Any]:
    cuda_available = bool(torch.cuda.is_available())
    return {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "cuda": torch.version.cuda,
        "cuda_available": cuda_available,
        "gpu": torch.cuda.get_device_name(0) if cuda_available else None,
        "requested_device": "cuda",
        "requested_dtype": "bfloat16",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--hf-revision",
        required=True,
        help="Full immutable Cloudflare/clef-flash commit SHA approved before inference.",
    )
    parser.add_argument("--cache-dir")
    parser.add_argument(
        "--fixture",
        default=str(ROOT / "systemone-contract.v0.1.json"),
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output = Path(args.output)
    fixture = load_fixture(args.fixture)
    request = json.loads(json.dumps(fixture["request"]))
    request["model"] = "clef-flash"

    evidence = {
        "schema_version": "0.1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "cloudflare-clef-local-release",
        "model": "clef-flash",
        "hf_repo": HF_REPO,
        "hf_revision_requested": args.hf_revision,
        "approved_revision_prefix": APPROVED_REVISION_PREFIX,
        "max_length": FROZEN_MAX_LENGTH,
        "request": request,
        "stage": "reserved-before-validation",
    }
    try:
        reserve_evidence(output, evidence)
    except FileExistsError as exc:
        raise SystemExit(f"refusing to overwrite existing evidence: {output}") from exc

    try:
        validate_request(request)
        validate_approved_revision(args.hf_revision)
    except Exception as exc:
        evidence.update(
            {
                "stage": "request-or-revision-validation-error",
                "validation_error": f"{type(exc).__name__}: {exc}",
            }
        )
        update_evidence(output, evidence)
        raise RuntimeError(
            f"Clef-Flash preflight validation failed; evidence: {output}"
        ) from exc

    try:
        from huggingface_hub import model_info, snapshot_download

        info = model_info(HF_REPO, revision=args.hf_revision)
        resolved_revision = info.sha
        if resolved_revision != args.hf_revision:
            raise ValueError(
                "Hugging Face resolved a different revision: "
                f"requested={args.hf_revision} resolved={resolved_revision}"
            )
        validate_approved_revision(resolved_revision)
        evidence.update(
            {
                "hf_revision": resolved_revision,
                "stage": "revision-validated-before-inference",
            }
        )
        update_evidence(output, evidence)

        snapshot = Path(
            snapshot_download(
                HF_REPO,
                revision=resolved_revision,
                cache_dir=args.cache_dir,
            )
        ).resolve()
    except Exception as exc:
        evidence.update(
            {
                "stage": "revision-or-snapshot-error",
                "pre_inference_error": f"{type(exc).__name__}: {exc}",
            }
        )
        update_evidence(output, evidence)
        raise RuntimeError(f"Clef-Flash revision/snapshot preparation failed; evidence: {output}") from exc

    required_files = [
        "joint_schema_model.py",
        "joint_head.safetensors",
        "joint_head_config.json",
        "model.safetensors.index.json",
        "config.json",
    ]
    missing = [name for name in required_files if not (snapshot / name).is_file()]
    if missing:
        evidence.update(
            {
                "stage": "snapshot-incomplete",
                "snapshot_path": str(snapshot),
                "pre_inference_error": f"snapshot is incomplete: missing={missing}",
            }
        )
        update_evidence(output, evidence)
        raise RuntimeError(f"Clef-Flash snapshot is incomplete; evidence: {output}")

    evidence.update(
        {
            "snapshot_path": str(snapshot),
            "joint_schema_model_sha256": sha256_file(snapshot / "joint_schema_model.py"),
            "joint_head_sha256": sha256_file(snapshot / "joint_head.safetensors"),
            "stage": "snapshot-validated-before-inference",
        }
    )
    update_evidence(output, evidence)

    try:
        module = load_joint_schema_module(snapshot)
        import torch
        import transformers
        from transformers import AutoProcessor

        runtime = runtime_snapshot(torch, transformers)
        evidence["runtime"] = runtime
        if not runtime["cuda_available"]:
            raise RuntimeError("CUDA is required for the exact Clef-Flash smoke")

        processor = AutoProcessor.from_pretrained(snapshot)
        encoding = inspect_state_encoding(
            module,
            processor,
            request,
            max_length=FROZEN_MAX_LENGTH,
        )
        evidence.update(
            {
                "encoding_preflight": encoding,
                "stage": "encoding-preflight-completed",
            }
        )
        update_evidence(output, evidence)

        if encoding["state_truncated"]:
            evidence.update(
                {
                    "stage": "state-truncation-rejected",
                    "pre_inference_error": (
                        "state would be truncated by upstream encode_record; "
                        "first exact smoke requires complete state"
                    ),
                }
            )
            update_evidence(output, evidence)
            raise RuntimeError(
                f"Clef-Flash state truncation rejected before inference; evidence: {output}"
            )

        model, processor = module.load_release_model(str(snapshot), device="cuda")
        try:
            evidence["runtime"]["loaded_model_first_parameter_dtype"] = str(
                next(model.parameters()).dtype
            )
        except StopIteration:
            evidence["runtime"]["loaded_model_first_parameter_dtype"] = None
        evidence["stage"] = "runtime-recorded-before-inference"
        update_evidence(output, evidence)

        response = module.systemone(
            model,
            processor,
            request,
            max_length=FROZEN_MAX_LENGTH,
        )
    except Exception as exc:
        if evidence.get("stage") not in {
            "state-truncation-rejected",
            "request-or-revision-validation-error",
        }:
            evidence.update(
                {
                    "stage": "inference-or-runtime-error",
                    "inference_error": f"{type(exc).__name__}: {exc}",
                }
            )
            update_evidence(output, evidence)
        raise RuntimeError(f"Clef-Flash local smoke failed; evidence: {output}") from exc

    evidence.update(
        {
            "stage": "raw-response-received",
            "raw_response": response,
        }
    )
    update_evidence(output, evidence)

    try:
        validate_response(
            response,
            request,
            probability_tolerance=float(
                fixture["contract_expectations"]["probability_tolerance_after_rounding"]
            ),
        )
    except Exception as exc:
        evidence.update(
            {
                "stage": "contract-validation-error",
                "validation_error": f"{type(exc).__name__}: {exc}",
            }
        )
        update_evidence(output, evidence)
        raise RuntimeError(f"Clef-Flash contract validation failed; evidence: {output}") from exc

    evidence.update(
        {
            "stage": "validated",
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        }
    )
    update_evidence(output, evidence)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

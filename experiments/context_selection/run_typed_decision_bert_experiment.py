#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request as urllib_request

from evaluate_context_selection import evaluate
from semantic_provider import select_top_k, validate_result
from typed_decision_bert_provider import TypedDecisionBertHttpProvider


EXPECTED = {
    "bundle_id": "jevbert-poc-nli-ja-en-0.2.0",
    "bundle_digest": "sha256:61dbb2190c473fa8925a523e28f32a1ec83df1dcbb2f52f832fdbdea0cb1d494",
    "backend": "a0-nli-zeroshot-v2",
    "serializer": "serializer-nli-v1+nli-template-v1",
    "source_model": "MoritzLaurer/bge-m3-zeroshot-v2.0",
    "source_revision": "9abf1c8aaeb82a2447809c20753ed0b106b76652",
    "dtype": "float32",
    "max_sequence_tokens": 2048,
    "max_request_tokens": 131072,
}


def load_docs(path: Path) -> dict[str, str]:
    docs = {}
    for file in sorted(path.glob("PDDR-*.md")):
        docs[file.stem[:9]] = file.read_text()
    return docs


def get_json(url: str, api_key: str) -> tuple[dict[str, Any], dict[str, str]]:
    req = urllib_request.Request(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    with urllib_request.urlopen(req, timeout=60) as response:
        body = json.loads(response.read().decode("utf-8"))
        headers = {key.lower(): value for key, value in response.headers.items()}
    return body, headers


def validate_capabilities(base_url: str, api_key: str) -> dict[str, Any]:
    payload, headers = get_json(
        base_url.rstrip("/") + "/jevbert/v1/capabilities",
        api_key,
    )
    bundles = payload.get("bundles")
    if not isinstance(bundles, list):
        raise SystemExit("capabilities response has no bundles")
    bundle = next(
        (item for item in bundles if item.get("id") == EXPECTED["bundle_id"]),
        None,
    )
    if not isinstance(bundle, dict):
        raise SystemExit("frozen JevBERT bundle is not registered")

    checks = {
        "digest": EXPECTED["bundle_digest"],
        "backend": EXPECTED["backend"],
        "serializer": EXPECTED["serializer"],
        "dtype": EXPECTED["dtype"],
    }
    for key, expected in checks.items():
        if bundle.get(key) != expected:
            raise SystemExit(
                f"capabilities {key} mismatch: {bundle.get(key)} != {expected}"
            )

    source = bundle.get("source_model") or {}
    if source.get("repo") != EXPECTED["source_model"]:
        raise SystemExit(f"unexpected source model: {source}")
    if source.get("revision") != EXPECTED["source_revision"]:
        raise SystemExit(f"unexpected source revision: {source}")

    calibration = bundle.get("calibration") or {}
    if calibration.get("state") != "uncalibrated":
        raise SystemExit(f"unexpected calibration state: {calibration}")
    expected_temps = {"noul": 1.0, "choice": 1.0, "score": 1.0}
    if calibration.get("temperature") != expected_temps:
        raise SystemExit(
            f"unexpected calibration temperatures: {calibration.get('temperature')}"
        )

    limits = bundle.get("limits") or {}
    if int(limits.get("max_sequence_tokens", 0)) != EXPECTED["max_sequence_tokens"]:
        raise SystemExit(f"unexpected sequence limit: {limits}")
    if int(limits.get("max_request_tokens", 0)) != EXPECTED["max_request_tokens"]:
        raise SystemExit(f"unexpected request limit: {limits}")

    return {"bundle": bundle, "headers": headers, "capabilities": payload}


def serialize_result(result):
    return {
        "provider": result.provider,
        "abstained": result.abstained,
        "metadata": dict(result.metadata),
        "decisions": [
            {
                "pddr_id": d.pddr_id,
                "required_probability": d.required_probability,
                "useful_probability": d.useful_probability,
                "irrelevant_probability": d.irrelevant_probability,
                "label": d.label,
                "confidence": d.confidence,
                "metadata": dict(d.metadata),
            }
            for d in result.decisions
        ],
    }


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cases")
    parser.add_argument("corpus_dir")
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--source-code-revision", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    runtime_identity = validate_capabilities(args.base_url, args.api_key)
    cases = json.loads(Path(args.cases).read_text())
    docs = load_docs(Path(args.corpus_dir))
    provider = TypedDecisionBertHttpProvider(
        api_key=args.api_key,
        endpoint=args.base_url.rstrip("/") + "/v1/systemone",
    )

    selections = {}
    raw_results = {}
    metrics = []
    total_http_seconds = 0.0
    total_input_tokens = 0

    for case in cases:
        available = {pddr_id: docs[pddr_id] for pddr_id in case["corpus"]}
        result = provider.classify(task=case["task"], records=available)
        validate_result(result, case["corpus"])
        selected = select_top_k(result, top_k=args.top_k)
        selections[case["case_id"]] = selected
        raw_results[case["case_id"]] = serialize_result(result)
        metrics.append(evaluate(case, selected))
        total_http_seconds += float(result.metadata.get("total_http_seconds", 0.0))
        total_input_tokens += int(result.metadata.get("total_input_tokens", 0))

    out = Path(args.output_dir)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"Refusing to overwrite evidence directory: {out}")
    out.mkdir(parents=True, exist_ok=True)

    (out / "selections.json").write_text(
        json.dumps(selections, indent=2, sort_keys=True) + "\n"
    )
    (out / "provider-results.json").write_text(
        json.dumps(raw_results, indent=2, sort_keys=True) + "\n"
    )
    (out / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n"
    )

    provenance = {
        "experiment_version": "typed-decision-bert-v0.1",
        "provider": provider.name,
        "source_repository": "hawkymisc/typed-decision-bert",
        "source_revision": args.source_code_revision,
        "bundle_id": EXPECTED["bundle_id"],
        "bundle_digest": EXPECTED["bundle_digest"],
        "backend": EXPECTED["backend"],
        "serializer": EXPECTED["serializer"],
        "source_model": EXPECTED["source_model"],
        "source_model_revision": EXPECTED["source_revision"],
        "dtype": EXPECTED["dtype"],
        "calibration": {
            "state": "uncalibrated",
            "temperature": {"noul": 1.0, "choice": 1.0, "score": 1.0},
        },
        "max_sequence_tokens": EXPECTED["max_sequence_tokens"],
        "max_request_tokens": EXPECTED["max_request_tokens"],
        "top_k": args.top_k,
        "runtime_identity": runtime_identity,
        "total_provider_http_seconds": total_http_seconds,
        "total_provider_input_tokens": total_input_tokens,
        "runtime_versions": {
            "python": platform.python_version(),
            "torch": package_version("torch"),
            "transformers": package_version("transformers"),
            "tokenizers": package_version("tokenizers"),
            "huggingface_hub": package_version("huggingface_hub"),
            "jevbert": package_version("jevbert"),
        },
        "cases": str(Path(args.cases)),
        "corpus_dir": str(Path(args.corpus_dir)),
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    (out / "provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n"
    )

    print("=== selections ===")
    print(json.dumps(selections, indent=2, sort_keys=True))
    print("=== metrics ===")
    print(json.dumps(metrics, indent=2, sort_keys=True))
    print(f"=== provider HTTP seconds ===\n{total_http_seconds:.6f}")
    print(f"=== provider input tokens ===\n{total_input_tokens}")


if __name__ == "__main__":
    main()

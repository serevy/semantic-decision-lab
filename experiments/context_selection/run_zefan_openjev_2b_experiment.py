#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import re
from datetime import datetime, timezone
from pathlib import Path

from evaluate_context_selection import evaluate
from semantic_provider import select_top_k, validate_result
from zefan_openjev_2b_provider import ZefanOpenJev2BHttpProvider


EXPECTED_CHECKPOINT_SHA = (
    "3076462e6356412082e79af909227b39b2863b90def79155ca0821aa506b7ded"
)
EXPECTED_BASE_REVISION = "15852e8c16360a2fea060d615a32b45270f8a8fc"
EXPECTED_SOURCE_REVISION = "ed45657bf726c3b77408942830e5578f99df904e"
EXPECTED_MAX_LENGTH = 4096


def load_docs(path: Path) -> dict[str, str]:
    docs = {}
    for file in sorted(path.glob("PDDR-*.md")):
        match = re.search(r"(PDDR-\d{4})", file.name)
        if match:
            docs[match.group(1)] = file.read_text()
    return docs


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


def validate_identity(identity: dict) -> None:
    if identity.get("checkpoint_sha256") != EXPECTED_CHECKPOINT_SHA:
        raise SystemExit(
            "provider checkpoint SHA mismatch: "
            f"{identity.get('checkpoint_sha256')} != {EXPECTED_CHECKPOINT_SHA}"
        )
    if identity.get("base_revision") != EXPECTED_BASE_REVISION:
        raise SystemExit(
            "provider base revision mismatch: "
            f"{identity.get('base_revision')} != {EXPECTED_BASE_REVISION}"
        )
    if int(identity.get("max_length", 0)) != EXPECTED_MAX_LENGTH:
        raise SystemExit(
            f"provider max_length mismatch: {identity.get('max_length')}"
        )
    if identity.get("code_commit") != EXPECTED_SOURCE_REVISION:
        raise SystemExit(
            "provider source revision mismatch: "
            f"{identity.get('code_commit')} != {EXPECTED_SOURCE_REVISION}"
        )
    if identity.get("method") != "lora_decision_head":
        raise SystemExit(f"unexpected provider method: {identity.get('method')}")
    if identity.get("prefix_cache_enabled") is not False:
        raise SystemExit("prefix cache must remain disabled for v0.1")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cases")
    parser.add_argument("corpus_dir")
    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:8791/v1/systemone",
    )
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    cases = json.loads(Path(args.cases).read_text())
    docs = load_docs(Path(args.corpus_dir))
    provider = ZefanOpenJev2BHttpProvider(endpoint=args.endpoint)

    selections = {}
    raw_results = {}
    metrics = []
    total_inference_seconds = 0.0
    total_input_tokens = 0
    observed_identity = None

    for case in cases:
        available = {pddr_id: docs[pddr_id] for pddr_id in case["corpus"]}
        result = provider.classify(task=case["task"], records=available)
        validate_result(result, case["corpus"])
        identity = dict(result.metadata.get("identity", {}))
        validate_identity(identity)
        if observed_identity is None:
            observed_identity = identity
        elif identity != observed_identity:
            raise SystemExit("provider identity changed between cases")

        selected = select_top_k(result, top_k=args.top_k)
        selections[case["case_id"]] = selected
        raw_results[case["case_id"]] = serialize_result(result)
        metrics.append(evaluate(case, selected))
        total_inference_seconds += float(
            result.metadata.get("total_inference_seconds", 0.0)
        )
        total_input_tokens += int(result.metadata.get("total_input_tokens", 0))

    out = Path(args.output_dir)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"Refusing to overwrite existing evidence directory: {out}")
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
        "experiment_version": "zefan-open-jev-2b-v0.1",
        "provider": provider.name,
        "source_repository": "Zefan-Cai/Open-Jev",
        "source_revision": args.source_revision,
        "model_repository": "ZefanCai/Open-Jev-2B",
        "model_revision": args.model_revision,
        "base_model": "Qwen/Qwen3.5-2B",
        "base_revision": EXPECTED_BASE_REVISION,
        "checkpoint_sha256": EXPECTED_CHECKPOINT_SHA,
        "inference_max_length": EXPECTED_MAX_LENGTH,
        "batch_size": 1,
        "prefix_cache": False,
        "top_k": args.top_k,
        "runtime_identity": observed_identity or {},
        "total_provider_inference_seconds": total_inference_seconds,
        "total_provider_input_tokens": total_input_tokens,
        "runtime_versions": {
            "python": platform.python_version(),
            "torch": package_version("torch"),
            "transformers": package_version("transformers"),
            "peft": package_version("peft"),
            "open_jev": package_version("open-jev"),
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
    print(
        "=== provider inference seconds ===\n"
        f"{total_inference_seconds:.6f}"
    )


if __name__ == "__main__":
    main()

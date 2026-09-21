#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from evaluate_context_selection import evaluate
from laya_multilingual_provider import LayaMultilingualProvider
from semantic_provider import select_top_k, validate_result


def load_docs(path: Path) -> dict[str, str]:
    docs = {}
    for file in sorted(path.glob("PDDR-*.md")):
        match = re.search(r"(PDDR-\d{4})", file.name)
        if match:
            docs[match.group(1)] = file.read_text()
    return docs


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--max-len", type=int, default=4096)
    parser.add_argument("--head-max-len", type=int, default=256)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    from laya.agent import Agent

    model_dir = Path(args.model_dir)
    checkpoint = model_dir / "model.safetensors"
    if not checkpoint.exists():
        raise SystemExit(f"model.safetensors not found: {checkpoint}")

    agent = Agent(str(model_dir), device=args.device)
    default_max_len = int(agent.cfg.get("max_len", 0))
    default_head_max_len = int(agent.cfg.get("head_max_len", 0))
    temperature = list(agent.cfg.get("temperature", []))
    temperature_by_options = dict(agent.cfg.get("temperature_by_options", {}))

    agent.cfg["max_len"] = args.max_len
    agent.cfg["head_max_len"] = args.head_max_len

    cases = json.loads(Path(args.cases).read_text())
    docs = load_docs(Path(args.corpus_dir))
    provider = LayaMultilingualProvider(agent)

    selections = {}
    raw_results = {}
    metrics = []

    for case in cases:
        available = {pddr_id: docs[pddr_id] for pddr_id in case["corpus"]}
        result = provider.classify(task=case["task"], records=available)
        validate_result(result, case["corpus"])
        selected = select_top_k(result, top_k=args.top_k)
        selections[case["case_id"]] = selected
        raw_results[case["case_id"]] = serialize_result(result)
        metrics.append(evaluate(case, selected))

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
        "experiment_version": "laya-multilingual-v0.1",
        "provider": provider.name,
        "source_repository": "NandhaKishorM/laya",
        "source_revision": args.source_revision,
        "model_repository": "convaiinnovations/laya-multilingual",
        "model_revision": args.model_revision,
        "model_safetensors_sha256": sha256_file(checkpoint),
        "checkpoint_default_max_len": default_max_len,
        "checkpoint_default_head_max_len": default_head_max_len,
        "inference_max_len": args.max_len,
        "inference_head_max_len": args.head_max_len,
        "temperature": temperature,
        "temperature_by_options": temperature_by_options,
        "device": str(agent.device),
        "dtype": str(agent.dtype),
        "top_k": args.top_k,
        "runtime_versions": {
            "python": package_version("pip"),
            "torch": package_version("torch"),
            "transformers": package_version("transformers"),
            "huggingface_hub": package_version("huggingface_hub"),
            "laya": package_version("laya"),
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


if __name__ == "__main__":
    main()

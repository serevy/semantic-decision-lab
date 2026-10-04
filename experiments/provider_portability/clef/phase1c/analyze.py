from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .probes import DEFAULT_MANIFEST, PHASE1A_MATRIX, load_manifest, validate_manifest
except ImportError:
    from probes import DEFAULT_MANIFEST, PHASE1A_MATRIX, load_manifest, validate_manifest

from phase1a.analyze import compare_answer, load_normalized


def _aggregate_metric_dicts(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {}
    answer_type = items[0]["type"]
    result: dict[str, Any] = {"type": answer_type}
    for key in items[0]:
        if key == "type":
            continue
        values = [item[key] for item in items]
        if isinstance(values[0], bool):
            result[key] = {
                "any": any(values),
                "count_true": sum(int(value) for value in values),
            }
        else:
            numeric = [float(value) for value in values]
            result[key] = {
                "min": min(numeric),
                "mean": sum(numeric) / len(numeric),
                "max": max(numeric),
            }
    return result


def _repeat_paths(results_dir: Path, fixture_id: str, variant_id: str) -> list[Path]:
    return [
        results_dir / fixture_id / variant_id / f"repeat-{repeat_index}.json"
        for repeat_index in (1, 2, 3)
    ]


def _load_evidence(path: Path) -> dict[str, Any]:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    if evidence.get("stage") != "validated":
        raise ValueError(f"evidence is not validated: {path}")
    return evidence


def _within_condition(paths: list[Path]) -> dict[str, Any]:
    evidence = [_load_evidence(path) for path in paths]
    responses = [item["normalized_systemone_response"] for item in evidence]
    first = responses[0]["answers"]

    comparisons = []
    for response in responses[1:]:
        current = response["answers"]
        comparisons.append(
            {
                question_id: compare_answer(first[question_id], current[question_id])
                for question_id in first
            }
        )

    aggregated = {}
    for question_id in first:
        aggregated[question_id] = _aggregate_metric_dicts(
            [comparison[question_id] for comparison in comparisons]
        )

    return {
        "unique_raw_response_sha256_count": len(
            {item["raw_response_sha256"] for item in evidence}
        ),
        "raw_response_sha256": [item["raw_response_sha256"] for item in evidence],
        "observed_owner_choices": [
            response["answers"]["owner"]["choice"]
            for response in responses
            if "owner" in response["answers"]
        ],
        "repeat1_vs_repeat2_and_3": aggregated,
    }


def _between_conditions(
    canonical_paths: list[Path],
    variant_paths: list[Path],
) -> dict[str, Any]:
    canonical = [load_normalized(path)["answers"] for path in canonical_paths]
    variant = [load_normalized(path)["answers"] for path in variant_paths]

    pairwise = []
    for baseline in canonical:
        for current in variant:
            pairwise.append(
                {
                    question_id: compare_answer(
                        baseline[question_id], current[question_id]
                    )
                    for question_id in baseline
                }
            )

    aggregated = {}
    for question_id in canonical[0]:
        aggregated[question_id] = _aggregate_metric_dicts(
            [comparison[question_id] for comparison in pairwise]
        )
    return {
        "pairwise_comparison_count": len(pairwise),
        "metrics": aggregated,
    }


def analyze(results_dir: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    validate_manifest(manifest, manifest_path)
    variants = manifest["question_order_variants"]
    fixtures = list(manifest["phase1b_fixture_pins"])

    output_fixtures = {}
    byte_identical_conditions = 0

    for fixture_id in fixtures:
        conditions = {}
        for variant_id in variants:
            paths = _repeat_paths(results_dir, fixture_id, variant_id)
            condition = _within_condition(paths)
            conditions[variant_id] = condition
            byte_identical_conditions += int(
                condition["unique_raw_response_sha256_count"] == 1
            )

        canonical_paths = _repeat_paths(
            results_dir, fixture_id, "packed-canonical"
        )
        between = {}
        for variant_id in variants[1:]:
            between[variant_id] = _between_conditions(
                canonical_paths,
                _repeat_paths(results_dir, fixture_id, variant_id),
            )

        output_fixtures[fixture_id] = {
            "conditions": conditions,
            "canonical_vs_question_order": between,
        }

    return {
        "schema_version": "0.1",
        "experiment": manifest["experiment"],
        "condition_count": manifest["condition_count"],
        "repeat_count_per_condition": manifest["repeats_per_condition"],
        "repeatability_summary": {
            "byte_identical_repeat_conditions": byte_identical_conditions,
            "total_conditions": manifest["condition_count"],
        },
        "fixtures": output_fixtures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output")
    args = parser.parse_args()

    report = analyze(Path(args.results_dir), Path(args.manifest))
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

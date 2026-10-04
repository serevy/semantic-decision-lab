from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from .probes import DEFAULT_MANIFEST, PHASE1A_MATRIX, load_manifest, validate_manifest
except ImportError:
    from probes import DEFAULT_MANIFEST, PHASE1A_MATRIX, load_manifest, validate_manifest

from phase1a.analyze import analyze as analyze_phase1a, load_normalized
from phase1a.probes import load_matrix as load_phase1a_matrix


def _metric_is_nonzero(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return float(value) != 0.0
    return False


def _answer_metrics_are_zero(metrics: dict[str, Any]) -> bool:
    return not any(
        _metric_is_nonzero(value)
        for key, value in metrics.items()
        if key != "type"
    )


def _max_metric(
    comparisons: dict[str, Any],
    variant_ids: list[str],
    question_id: str,
    metric_name: str,
) -> float:
    values = []
    for variant_id in variant_ids:
        metrics = comparisons[variant_id].get(question_id)
        if metrics is not None and metric_name in metrics:
            values.append(float(metrics[metric_name]))
    return max(values, default=0.0)


def analyze(results_dir: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    validate_manifest(manifest, manifest_path)
    phase1a = load_phase1a_matrix(PHASE1A_MATRIX)

    choice_variants = phase1a["comparison_sets"]["choice_order"]["variants"]
    question_variants = phase1a["comparison_sets"]["question_order"]["variants"]

    fixtures: dict[str, Any] = {}
    choice_zero_count = 0
    question_nonzero_count = 0

    for entry in manifest["fixtures"]:
        fixture_id = entry["id"]
        fixture_dir = results_dir / fixture_id
        report = analyze_phase1a(fixture_dir, PHASE1A_MATRIX)
        comparisons = report["comparisons"]
        baseline = load_normalized(fixture_dir / "packed-canonical.json")

        choice_zero = all(
            _answer_metrics_are_zero(metrics)
            for variant_id in choice_variants
            for metrics in comparisons[variant_id].values()
        )
        question_nonzero = any(
            not _answer_metrics_are_zero(metrics)
            for variant_id in question_variants
            for metrics in comparisons[variant_id].values()
        )
        choice_zero_count += int(choice_zero)
        question_nonzero_count += int(question_nonzero)

        fixtures[fixture_id] = {
            "baseline_answers": baseline["answers"],
            "choice_order_all_zero_delta": choice_zero,
            "question_order_any_nonzero_delta": question_nonzero,
            "question_order_top_choice_flips": sum(
                int(
                    comparisons[variant_id]
                    .get("owner", {})
                    .get("top_choice_flip", False)
                )
                for variant_id in question_variants
            ),
            "question_order_maxima": {
                "outage_absolute_probability_delta": _max_metric(
                    comparisons,
                    question_variants,
                    "outage",
                    "absolute_probability_delta",
                ),
                "owner_per_option_max_absolute_delta": _max_metric(
                    comparisons,
                    question_variants,
                    "owner",
                    "per_option_max_absolute_delta",
                ),
                "owner_confidence_absolute_delta": _max_metric(
                    comparisons,
                    question_variants,
                    "owner",
                    "confidence_absolute_delta",
                ),
                "severity_reported_score_absolute_delta": _max_metric(
                    comparisons,
                    question_variants,
                    "severity",
                    "reported_score_absolute_delta",
                ),
                "severity_per_bin_max_absolute_delta": _max_metric(
                    comparisons,
                    question_variants,
                    "severity",
                    "per_bin_max_absolute_delta",
                ),
                "severity_confidence_absolute_delta": _max_metric(
                    comparisons,
                    question_variants,
                    "severity",
                    "confidence_absolute_delta",
                ),
            },
            "packed_vs_single": {
                "outage": comparisons["single-outage"]["outage"],
                "owner": comparisons["single-owner"]["owner"],
                "severity": comparisons["single-severity"]["severity"],
            },
            "phase1a_metrics": comparisons,
        }

    return {
        "schema_version": "0.1",
        "experiment": manifest["experiment"],
        "fixture_count": len(manifest["fixtures"]),
        "replication_summary": {
            "choice_order_zero_delta_fixtures": choice_zero_count,
            "question_order_nonzero_delta_fixtures": question_nonzero_count,
        },
        "fixtures": fixtures,
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

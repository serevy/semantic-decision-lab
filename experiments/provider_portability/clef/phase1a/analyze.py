from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping

try:
    from .probes import load_matrix
except ImportError:
    from probes import load_matrix


def _distribution(answer: Mapping[str, Any]) -> dict[str, float]:
    return {str(key): float(value) for key, value in answer["probabilities"].items()}


def _jsd_base2(first: Mapping[str, float], second: Mapping[str, float]) -> float:
    keys = sorted(set(first) | set(second))
    p = [float(first.get(key, 0.0)) for key in keys]
    q = [float(second.get(key, 0.0)) for key in keys]
    m = [(a + b) / 2.0 for a, b in zip(p, q)]

    def kl(values: list[float], midpoint: list[float]) -> float:
        total = 0.0
        for value, mid in zip(values, midpoint):
            if value > 0.0:
                total += value * math.log2(value / mid)
        return total

    return (kl(p, m) + kl(q, m)) / 2.0


def _expected_score(probabilities: Mapping[str, float]) -> float:
    return sum(float(level) * probability for level, probability in probabilities.items())


def compare_answer(
    baseline: Mapping[str, Any],
    variant: Mapping[str, Any],
) -> dict[str, Any]:
    if baseline["type"] != variant["type"]:
        raise ValueError("answer type mismatch")

    answer_type = baseline["type"]
    if answer_type == "noul":
        return {
            "type": "noul",
            "absolute_probability_delta": abs(
                float(variant["noul"]) - float(baseline["noul"])
            ),
        }

    first = _distribution(baseline)
    second = _distribution(variant)
    common_keys = sorted(set(first) | set(second))
    max_delta = max(abs(first.get(key, 0.0) - second.get(key, 0.0)) for key in common_keys)

    if answer_type == "choice":
        return {
            "type": "choice",
            "per_option_max_absolute_delta": max_delta,
            "jensen_shannon_divergence_base2": _jsd_base2(first, second),
            "top_choice_flip": variant["choice"] != baseline["choice"],
            "confidence_absolute_delta": abs(
                float(variant["confidence"]) - float(baseline["confidence"])
            ),
        }

    return {
        "type": "score",
        "reported_score_absolute_delta": abs(
            float(variant["score"]) - float(baseline["score"])
        ),
        "expected_score_absolute_delta": abs(
            _expected_score(second) - _expected_score(first)
        ),
        "per_bin_max_absolute_delta": max_delta,
        "jensen_shannon_divergence_base2": _jsd_base2(first, second),
        "confidence_absolute_delta": abs(
            float(variant["confidence"]) - float(baseline["confidence"])
        ),
    }


def load_normalized(path: Path) -> Mapping[str, Any]:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    if evidence.get("stage") != "validated":
        raise ValueError(f"evidence is not validated: {path}")
    response = evidence.get("normalized_systemone_response")
    if not isinstance(response, Mapping):
        raise ValueError(f"missing normalized response: {path}")
    return response


def analyze(results_dir: Path, matrix_path: Path) -> dict[str, Any]:
    matrix = load_matrix(matrix_path)
    baseline_id = matrix["baseline_variant"]
    baseline = load_normalized(results_dir / f"{baseline_id}.json")
    baseline_answers = baseline["answers"]

    comparisons: dict[str, Any] = {}
    for variant in matrix["variants"]:
        variant_id = variant["id"]
        if variant_id == baseline_id:
            continue
        response = load_normalized(results_dir / f"{variant_id}.json")
        answer_metrics = {}
        for question_id in sorted(set(baseline_answers) & set(response["answers"])):
            answer_metrics[question_id] = compare_answer(
                baseline_answers[question_id],
                response["answers"][question_id],
            )
        comparisons[variant_id] = answer_metrics

    return {
        "schema_version": "0.1",
        "experiment": matrix["experiment"],
        "baseline_variant": baseline_id,
        "comparisons": comparisons,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--matrix", default=str(Path(__file__).with_name("probe-matrix.v0.1.json")))
    parser.add_argument("--output")
    args = parser.parse_args()

    report = analyze(Path(args.results_dir), Path(args.matrix))
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

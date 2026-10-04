from __future__ import annotations

import argparse
import base64
import gzip
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parent
CLEF_ROOT = ROOT.parent
if str(CLEF_ROOT) not in sys.path:
    sys.path.insert(0, str(CLEF_ROOT))

from contract import load_fixture, unwrap_cloudflare_rest, validate_response
from phase1a.analyze import compare_answer
from phase2a.probes import (
    DEFAULT_MANIFEST,
    load_manifest,
    materialize_case,
    resolve_pinned_path,
    validate_manifest,
)


def _aggregate_metric_dicts(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {}
    result: dict[str, Any] = {"type": items[0]["type"]}
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


def _evidence_path(
    results_dir: Path,
    fixture_id: str,
    variant_id: str,
    repeat_index: int,
) -> Path:
    return (
        results_dir
        / fixture_id
        / variant_id
        / f"repeat-{repeat_index}.json"
    )


def _load_local(path: Path) -> dict[str, Any]:
    evidence = json.loads(path.read_text(encoding="utf-8"))
    if evidence.get("stage") != "validated":
        raise ValueError(f"local evidence is not validated: {path}")
    response = evidence.get("normalized_systemone_response")
    if not isinstance(response, Mapping):
        raise ValueError(f"missing normalized local response: {path}")
    if not isinstance(evidence.get("local_response_sha256"), str):
        raise ValueError(f"missing local response hash: {path}")
    return evidence


def _load_hosted_records(
    bundle_path: Path,
    cases: list[dict[str, Any]],
    probability_tolerance: float,
) -> dict[tuple[str, str, int], Mapping[str, Any]]:
    compressed = base64.b64decode(bundle_path.read_bytes())
    bundle = json.loads(gzip.decompress(compressed))
    records = bundle.get("records")
    if not isinstance(records, list):
        raise ValueError("pinned Phase 1C hosted bundle has no records list")

    requests = {
        (
            case["fixture_id"],
            case["variant"]["id"],
            int(case["repeat_index"]),
        ): materialize_case(case)
        for case in cases
    }

    hosted: dict[tuple[str, str, int], Mapping[str, Any]] = {}
    for record in records:
        key = (
            str(record["fixture"]),
            str(record["variant"]),
            int(record["repeat"]),
        )
        if key not in requests:
            continue
        raw = base64.b64decode(record["raw_response_base64"])
        payload = json.loads(raw)
        response = unwrap_cloudflare_rest(payload)
        validate_response(
            response,
            requests[key],
            probability_tolerance=probability_tolerance,
        )
        hosted[key] = response

    if set(hosted) != set(requests):
        missing = sorted(set(requests) - set(hosted))
        extra = sorted(set(hosted) - set(requests))
        raise ValueError(
            f"hosted reference coverage mismatch: missing={missing} extra={extra}"
        )
    return hosted


def _within_condition(
    evidences: list[dict[str, Any]],
) -> dict[str, Any]:
    responses = [
        evidence["normalized_systemone_response"]
        for evidence in evidences
    ]
    first = responses[0]["answers"]
    comparisons = []
    for response in responses[1:]:
        answers = response["answers"]
        comparisons.append(
            {
                question_id: compare_answer(
                    first[question_id],
                    answers[question_id],
                )
                for question_id in first
            }
        )

    metrics = {
        question_id: _aggregate_metric_dicts(
            [comparison[question_id] for comparison in comparisons]
        )
        for question_id in first
    }
    return {
        "unique_local_response_sha256_count": len(
            {evidence["local_response_sha256"] for evidence in evidences}
        ),
        "local_response_sha256": [
            evidence["local_response_sha256"]
            for evidence in evidences
        ],
        "observed_owner_choices": [
            response["answers"]["owner"]["choice"]
            for response in responses
            if "owner" in response["answers"]
        ],
        "repeat1_vs_repeat2_and_3": metrics,
    }


def _between_conditions(
    canonical: list[dict[str, Any]],
    variant: list[dict[str, Any]],
) -> dict[str, Any]:
    first = [
        evidence["normalized_systemone_response"]["answers"]
        for evidence in canonical
    ]
    second = [
        evidence["normalized_systemone_response"]["answers"]
        for evidence in variant
    ]
    pairwise = []
    for baseline in first:
        for current in second:
            pairwise.append(
                {
                    question_id: compare_answer(
                        baseline[question_id],
                        current[question_id],
                    )
                    for question_id in baseline
                }
            )
    return {
        "pairwise_comparison_count": len(pairwise),
        "metrics": {
            question_id: _aggregate_metric_dicts(
                [comparison[question_id] for comparison in pairwise]
            )
            for question_id in first[0]
        },
    }


def analyze(
    results_dir: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    plan = validate_manifest(manifest, manifest_path)
    cases = plan["cases"]

    run_evidence = json.loads(
        (results_dir / "run.json").read_text(encoding="utf-8")
    )
    if run_evidence.get("stage") != "validated":
        raise ValueError("Phase 2A run.json is not validated")

    canary = json.loads(
        (results_dir / "canary.json").read_text(encoding="utf-8")
    )
    if canary.get("stage") != "validated":
        raise ValueError("Phase 2A canary is not validated")

    canary_fixture = load_fixture(
        resolve_pinned_path(
            manifest_path,
            manifest["frozen_pins"]["canary_fixture_path"],
        )
    )
    probability_tolerance = float(
        canary_fixture["contract_expectations"][
            "probability_tolerance_after_rounding"
        ]
    )

    hosted = _load_hosted_records(
        resolve_pinned_path(
            manifest_path,
            manifest["frozen_pins"]["hosted_phase1c_bundle_path"],
        ),
        cases,
        probability_tolerance,
    )
    hosted_analysis = json.loads(
        resolve_pinned_path(
            manifest_path,
            manifest["frozen_pins"]["hosted_phase1c_analysis_path"],
        ).read_text(encoding="utf-8")
    )

    case_map = {
        (
            case["fixture_id"],
            case["variant"]["id"],
            int(case["repeat_index"]),
        ): case
        for case in cases
    }
    local = {
        key: _load_local(_evidence_path(results_dir, *key))
        for key in case_map
    }

    variants = plan["phase1c_manifest"]["question_order_variants"]
    fixtures = list(plan["phase1c_manifest"]["phase1b_fixture_pins"])

    local_fixtures: dict[str, Any] = {}
    byte_identical_conditions = 0
    for fixture_id in fixtures:
        conditions = {}
        for variant_id in variants:
            evidences = [
                local[(fixture_id, variant_id, repeat_index)]
                for repeat_index in (1, 2, 3)
            ]
            condition = _within_condition(evidences)
            conditions[variant_id] = condition
            byte_identical_conditions += int(
                condition["unique_local_response_sha256_count"] == 1
            )

        canonical = [
            local[(fixture_id, "packed-canonical", repeat_index)]
            for repeat_index in (1, 2, 3)
        ]
        between = {
            variant_id: _between_conditions(
                canonical,
                [
                    local[(fixture_id, variant_id, repeat_index)]
                    for repeat_index in (1, 2, 3)
                ],
            )
            for variant_id in variants[1:]
        }
        local_fixtures[fixture_id] = {
            "conditions": conditions,
            "canonical_vs_question_order": between,
        }

    local_vs_hosted = []
    owner_mismatch_count = 0
    metrics_by_question: dict[str, list[dict[str, Any]]] = {}
    for key in sorted(case_map):
        local_response = local[key]["normalized_systemone_response"]
        hosted_response = hosted[key]
        answer_metrics = {}
        for question_id in local_response["answers"]:
            metric = compare_answer(
                hosted_response["answers"][question_id],
                local_response["answers"][question_id],
            )
            answer_metrics[question_id] = metric
            metrics_by_question.setdefault(question_id, []).append(metric)

        if "owner" in local_response["answers"]:
            owner_mismatch_count += int(
                local_response["answers"]["owner"]["choice"]
                != hosted_response["answers"]["owner"]["choice"]
            )

        local_vs_hosted.append(
            {
                "fixture_id": key[0],
                "variant_id": key[1],
                "repeat_index": key[2],
                "metrics": answer_metrics,
                "local_owner_choice": (
                    local_response["answers"].get("owner", {}).get("choice")
                ),
                "hosted_owner_choice": (
                    hosted_response["answers"].get("owner", {}).get("choice")
                ),
            }
        )

    return {
        "schema_version": "0.1",
        "experiment": manifest["experiment"],
        "runtime": run_evidence["runtime"],
        "hf_revision": run_evidence["hf_revision"],
        "canary": {
            "stage": canary["stage"],
            "local_response_sha256": canary["local_response_sha256"],
        },
        "local_repeatability_summary": {
            "byte_identical_repeat_conditions": byte_identical_conditions,
            "total_conditions": 18,
        },
        "local_fixtures": local_fixtures,
        "hosted_reference_summary": hosted_analysis,
        "local_vs_hosted": {
            "comparison_count": len(local_vs_hosted),
            "owner_top_choice_mismatch_count": owner_mismatch_count,
            "aggregate_metrics": {
                question_id: _aggregate_metric_dicts(items)
                for question_id, items in metrics_by_question.items()
            },
            "comparisons": local_vs_hosted,
        },
        "interpretation_boundary": [
            "No semantic parity threshold was frozen before local output.",
            "No causality conclusion is emitted by this analyzer.",
            "Confidence deltas remain provider/runtime semantics observations and are not assumed equivalent to probability calibration.",
            "Non-H100/H200 hardware remains a distinct recorded runtime condition.",
        ],
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

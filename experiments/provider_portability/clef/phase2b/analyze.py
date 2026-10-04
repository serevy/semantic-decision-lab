from __future__ import annotations

import argparse
import json
import sys
import tarfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CLEF_ROOT = ROOT.parent
if str(CLEF_ROOT) not in sys.path:
    sys.path.insert(0, str(CLEF_ROOT))

from phase2b.probes import (
    DEFAULT_MANIFEST,
    load_manifest,
    resolve_pinned_path,
    validate_manifest,
)


def _load_validated(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("stage") != "validated":
        raise ValueError(f"evidence is not validated: {path}")
    return value


def _probability_delta(
    canonical: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    per_question: dict[str, Any] = {}
    overall = 0.0
    for question_id, first in canonical.items():
        second = current[question_id]
        if first["option_ids"] != second["option_ids"]:
            raise ValueError(
                f"option IDs drifted for {question_id}: "
                f"{first['option_ids']} != {second['option_ids']}"
            )
        option_delta = {
            option_id: abs(
                float(first["probabilities"][option_id])
                - float(second["probabilities"][option_id])
            )
            for option_id in first["option_ids"]
        }
        maximum = max(option_delta.values(), default=0.0)
        overall = max(overall, maximum)
        per_question[question_id] = {
            "per_option_absolute_delta": option_delta,
            "max_absolute_probability_delta": maximum,
        }
    return {
        "max_absolute_probability_delta": overall,
        "questions": per_question,
    }


def _collect_numeric(values: list[float]) -> dict[str, float]:
    if not values:
        return {"min": 0.0, "mean": 0.0, "max": 0.0}
    return {
        "min": min(values),
        "mean": sum(values) / len(values),
        "max": max(values),
    }


def _load_phase2a_repeat1_hashes(
    archive_path: Path,
    fixtures: list[str],
    variants: list[str],
) -> dict[tuple[str, str], str]:
    expected = {
        (fixture_id, variant_id)
        for fixture_id in fixtures
        for variant_id in variants
    }
    found: dict[tuple[str, str], str] = {}
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile() or not member.name.endswith("/repeat-1.json"):
                continue
            parts = Path(member.name).parts
            if len(parts) < 4:
                continue
            fixture_id = parts[-3]
            variant_id = parts[-2]
            key = (fixture_id, variant_id)
            if key not in expected:
                continue
            handle = archive.extractfile(member)
            if handle is None:
                continue
            evidence = json.load(handle)
            value = evidence.get("local_response_sha256")
            if not isinstance(value, str):
                raise ValueError(
                    f"Phase 2A repeat-1 evidence missing response hash: {member.name}"
                )
            found[key] = value
    if set(found) != expected:
        raise ValueError(
            f"Phase 2A repeat-1 coverage mismatch: "
            f"missing={sorted(expected - set(found))}"
        )
    return found


def analyze(results_dir: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    plan = validate_manifest(manifest, manifest_path)

    run = _load_validated(results_dir / "run.json")
    canary = _load_validated(results_dir / "canary.json")

    fixtures = plan["fixtures"]
    variants = plan["variants"]
    noncanonical = variants[1:]

    phase2a_hashes = _load_phase2a_repeat1_hashes(
        resolve_pinned_path(
            manifest_path,
            manifest["frozen_pins"]["phase2a_evidence_archive_path"],
        ),
        fixtures,
        variants,
    )

    actual: dict[tuple[str, str], dict[str, Any]] = {}
    head_only: dict[tuple[str, str], dict[str, Any]] = {}
    for fixture_id in fixtures:
        for variant_id in variants:
            actual[(fixture_id, variant_id)] = _load_validated(
                results_dir / fixture_id / "actual" / f"{variant_id}.json"
            )
            if variant_id != "packed-canonical":
                head_only[(fixture_id, variant_id)] = _load_validated(
                    results_dir / fixture_id / "head-only" / f"{variant_id}.json"
                )

    phase2a_response_hash_matches = 0
    actual_probability_deltas: list[float] = []
    head_only_probability_deltas: list[float] = []

    state_raw_max: list[float] = []
    state_normalized_max: list[float] = []
    global_raw_max: list[float] = []
    global_normalized_max: list[float] = []
    question_raw_max: list[float] = []
    question_normalized_max: list[float] = []
    option_raw_max: list[float] = []
    option_normalized_max: list[float] = []
    lexical_max: list[float] = []

    state_token_hash_mismatches = 0
    state_span_mismatches = 0
    instruction_token_hash_mismatches = 0
    option_semantic_token_hash_mismatches = 0
    question_absolute_span_changes = 0
    option_absolute_span_changes = 0

    fixture_reports: dict[str, Any] = {}
    for fixture_id in fixtures:
        canonical = actual[(fixture_id, "packed-canonical")]
        fixture_report = {
            "canonical_response_sha256": canonical["response_sha256"],
            "conditions": {},
            "head_only_counterfactuals": {},
        }

        for variant_id in variants:
            evidence = actual[(fixture_id, variant_id)]
            hash_match = (
                evidence["response_sha256"]
                == phase2a_hashes[(fixture_id, variant_id)]
            )
            phase2a_response_hash_matches += int(hash_match)

            condition_report: dict[str, Any] = {
                "response_sha256": evidence["response_sha256"],
                "phase2a_repeat1_response_sha256_match": hash_match,
            }
            if variant_id != "packed-canonical":
                delta = evidence["deltas_vs_canonical"]
                probability = _probability_delta(
                    canonical["logits"],
                    evidence["logits"],
                )
                actual_probability_deltas.append(
                    probability["max_absolute_probability_delta"]
                )
                condition_report["actual_probability_delta"] = probability
                condition_report["stage_deltas_vs_canonical"] = delta

                state_token_hash_mismatches += int(
                    not delta["state_token_sha256_match"]
                )
                state_span_mismatches += int(not delta["state_span_match"])
                state_raw_max.append(
                    float(delta["state_backbone_raw"]["max_absolute_delta"])
                )
                state_normalized_max.append(
                    float(
                        delta["state_backbone_normalized"][
                            "max_absolute_delta"
                        ]
                    )
                )
                global_raw_max.append(
                    float(delta["global_backbone_raw"]["max_absolute_delta"])
                )
                global_normalized_max.append(
                    float(
                        delta["global_backbone_normalized"][
                            "max_absolute_delta"
                        ]
                    )
                )

                for question in delta["questions"].values():
                    instruction_token_hash_mismatches += int(
                        not question["instruction_token_sha256_match"]
                    )
                    question_absolute_span_changes += int(
                        not question["absolute_span_match"]
                    )
                    question_raw_max.append(
                        float(
                            question["backbone_question_raw"][
                                "max_absolute_delta"
                            ]
                        )
                    )
                    question_normalized_max.append(
                        float(
                            question["backbone_question_normalized"][
                                "max_absolute_delta"
                            ]
                        )
                    )
                    for option in question["options"].values():
                        option_semantic_token_hash_mismatches += int(
                            not option["semantic_token_sha256_match"]
                        )
                        option_absolute_span_changes += int(
                            not option["absolute_span_match"]
                        )
                        option_raw_max.append(
                            float(
                                option["backbone_context_raw"][
                                    "max_absolute_delta"
                                ]
                            )
                        )
                        option_normalized_max.append(
                            float(
                                option["backbone_context_normalized"][
                                    "max_absolute_delta"
                                ]
                            )
                        )
                        lexical_max.append(
                            float(
                                option["lexical_output_embedding"][
                                    "max_absolute_delta"
                                ]
                            )
                        )

                counter = head_only[(fixture_id, variant_id)]
                counter_probability = _probability_delta(
                    canonical["logits"],
                    counter["logits"],
                )
                head_only_probability_deltas.append(
                    counter_probability["max_absolute_probability_delta"]
                )
                fixture_report["head_only_counterfactuals"][variant_id] = {
                    "response_sha256": counter["response_sha256"],
                    "probability_delta_vs_canonical": counter_probability,
                }

            fixture_report["conditions"][variant_id] = condition_report
        fixture_reports[fixture_id] = fixture_report

    return {
        "schema_version": "0.1",
        "experiment": manifest["experiment"],
        "runtime": run["runtime"],
        "hf_revision": run["hf_revision"],
        "canary": {
            "stage": canary["stage"],
            "response_sha256": canary["response_sha256"],
        },
        "coverage": {
            "actual_conditions": len(actual),
            "head_only_counterfactuals": len(head_only),
            "phase2a_repeat1_response_hash_matches": phase2a_response_hash_matches,
            "phase2a_repeat1_response_hash_comparisons": len(actual),
        },
        "encoding_invariants": {
            "state_token_hash_mismatches": state_token_hash_mismatches,
            "state_span_mismatches": state_span_mismatches,
            "question_instruction_token_hash_mismatches": (
                instruction_token_hash_mismatches
            ),
            "option_semantic_token_hash_mismatches": (
                option_semantic_token_hash_mismatches
            ),
            "question_absolute_span_changes": question_absolute_span_changes,
            "option_absolute_span_changes": option_absolute_span_changes,
        },
        "backbone_stage_summary": {
            "state_raw_max_absolute_delta": _collect_numeric(state_raw_max),
            "state_normalized_max_absolute_delta": _collect_numeric(
                state_normalized_max
            ),
            "global_raw_max_absolute_delta": _collect_numeric(global_raw_max),
            "global_normalized_max_absolute_delta": _collect_numeric(
                global_normalized_max
            ),
            "question_raw_max_absolute_delta": _collect_numeric(
                question_raw_max
            ),
            "question_normalized_max_absolute_delta": _collect_numeric(
                question_normalized_max
            ),
            "option_context_raw_max_absolute_delta": _collect_numeric(
                option_raw_max
            ),
            "option_context_normalized_max_absolute_delta": _collect_numeric(
                option_normalized_max
            ),
            "lexical_option_max_absolute_delta": _collect_numeric(lexical_max),
        },
        "released_path_probability_delta": _collect_numeric(
            actual_probability_deltas
        ),
        "fixed_backbone_head_only_probability_delta": _collect_numeric(
            head_only_probability_deltas
        ),
        "fixtures": fixture_reports,
        "interpretation_boundary": [
            "No semantic, numerical-noise, or causality threshold was frozen before Phase 2B output.",
            "The fixed-backbone head-only control is synthetic and is not a provider request.",
            "A zero head-only delta weakens tuple-order-alone explanations but does not prove a specific backbone attention or positional mechanism.",
            "A non-zero head-only delta demonstrates head-order contribution under the frozen counterfactual but does not quantify its causal share in actual provider requests.",
            "Phase 2A repeat-1 response-hash comparison is descriptive and is never an execution gate, especially across different GPU conditions.",
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
        try:
            with Path(args.output).open("x", encoding="utf-8") as handle:
                handle.write(rendered)
        except FileExistsError as exc:
            raise SystemExit(
                f"refusing to overwrite analysis: {args.output}"
            ) from exc
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

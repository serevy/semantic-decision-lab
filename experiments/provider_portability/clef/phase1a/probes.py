from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from contract import validate_request
from run_workers_ai_smoke import canonical_json, wire_json


ROOT = Path(__file__).resolve().parent
DEFAULT_MATRIX = ROOT / "probe-matrix.v0.1.json"


def load_matrix(path: str | Path = DEFAULT_MATRIX) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def source_fixture_path(matrix: dict[str, Any]) -> Path:
    return (ROOT / matrix["source_fixture"]).resolve()


def load_source_fixture(matrix: dict[str, Any]) -> dict[str, Any]:
    path = source_fixture_path(matrix)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != matrix["source_fixture_sha256"]:
        raise ValueError(
            "source fixture hash mismatch: "
            f"expected={matrix['source_fixture_sha256']} actual={digest}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def build_request(
    variant: dict[str, Any],
    source_fixture: dict[str, Any],
) -> dict[str, Any]:
    source_request = source_fixture["request"]
    source_questions = source_request["questions"]

    request = {
        "model": source_request["model"],
        "state": copy.deepcopy(source_request["state"]),
        "questions": {},
    }

    for question_id in variant["question_order"]:
        if question_id not in source_questions:
            raise ValueError(f"unknown question id in variant: {question_id}")
        question = copy.deepcopy(source_questions[question_id])
        if question_id == "owner":
            order = variant.get("owner_choice_order")
            if not order:
                raise ValueError("owner question requires owner_choice_order")
            source_criteria = question["criteria"]
            if set(order) != set(source_criteria):
                raise ValueError(f"owner choice order mismatch in {variant['id']}")
            question["criteria"] = {key: source_criteria[key] for key in order}
        request["questions"][question_id] = question

    validate_request(request)
    return request


def materialize_fixture(
    variant: dict[str, Any],
    source_fixture: dict[str, Any],
) -> dict[str, Any]:
    request = build_request(variant, source_fixture)
    return {
        "schema_version": source_fixture["schema_version"],
        "purpose": (
            "Clef-Flash Phase 1A frozen ordering/packing probe; "
            f"variant={variant['id']}"
        ),
        "request": request,
        "contract_expectations": {
            "answer_ids": list(request["questions"]),
            "semantic_gold": None,
            "probability_tolerance_after_rounding": source_fixture[
                "contract_expectations"
            ]["probability_tolerance_after_rounding"],
        },
    }


def validate_matrix(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    if matrix.get("frozen_before_phase1a_output") is not True:
        raise ValueError("Phase 1A matrix must be explicitly frozen before output")

    source = load_source_fixture(matrix)
    source_questions = source["request"]["questions"]
    canonical_score_criteria = source_questions["severity"]["criteria"]

    variants = matrix.get("variants")
    if not isinstance(variants, list) or len(variants) != 14:
        raise ValueError("Phase 1A v0.1 must contain exactly 14 frozen variants")

    ids = [variant["id"] for variant in variants]
    if len(ids) != len(set(ids)):
        raise ValueError("variant ids must be unique")

    materialized = []
    for variant in variants:
        request = build_request(variant, source)
        if "severity" in request["questions"]:
            if request["questions"]["severity"]["criteria"] != canonical_score_criteria:
                raise ValueError("score criteria order must never change")

        canonical_hash = hashlib.sha256(canonical_json(request)).hexdigest()
        wire_hash = hashlib.sha256(wire_json(request)).hexdigest()
        if canonical_hash != variant["canonical_request_sha256"]:
            raise ValueError(f"canonical request hash mismatch for {variant['id']}")
        if wire_hash != variant["wire_request_sha256"]:
            raise ValueError(f"wire request hash mismatch for {variant['id']}")

        materialized.append(materialize_fixture(variant, source))

    return materialized

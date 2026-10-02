from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Mapping


QUESTION_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
MODEL_SELECTORS = {"clef", "clef-flash"}
QUESTION_TYPES = {"noul", "choice", "score"}


def load_fixture(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _probability(value: Any, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")
    value = float(value)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{field} must be within [0, 1]")
    return value


def _validate_distribution(
    probabilities: Mapping[str, Any],
    expected_keys: list[str],
    *,
    tolerance: float,
) -> None:
    if set(probabilities) != set(expected_keys):
        raise ValueError(
            f"probability keys mismatch: expected={sorted(expected_keys)} "
            f"actual={sorted(probabilities)}"
        )
    values = [_probability(probabilities[key], f"probabilities.{key}") for key in expected_keys]
    if abs(sum(values) - 1.0) > tolerance:
        raise ValueError(
            f"probabilities must sum to 1 within tolerance {tolerance}; got {sum(values)}"
        )


def validate_request(request: Mapping[str, Any]) -> None:
    if not isinstance(request, Mapping):
        raise ValueError("request must be an object")

    model = request.get("model")
    if model not in MODEL_SELECTORS:
        raise ValueError(f"model must be one of {sorted(MODEL_SELECTORS)}")
    if "state" not in request:
        raise ValueError("state is required")

    questions = request.get("questions")
    if not isinstance(questions, Mapping) or not 1 <= len(questions) <= 64:
        raise ValueError("questions must contain 1..64 entries")

    for question_id, question in questions.items():
        if not isinstance(question_id, str) or not QUESTION_ID_RE.fullmatch(question_id):
            raise ValueError(f"invalid question id: {question_id!r}")
        if not isinstance(question, Mapping):
            raise ValueError(f"{question_id} must be an object")

        question_type = question.get("type")
        if question_type not in QUESTION_TYPES:
            raise ValueError(f"{question_id}.type must be noul, choice, or score")

        instructions = question.get("instructions")
        if instructions is not None and not isinstance(instructions, str):
            raise ValueError(f"{question_id}.instructions must be a string when present")

        criteria = question.get("criteria")
        if question_type == "choice":
            if not isinstance(criteria, Mapping) or not criteria:
                raise ValueError(f"{question_id}.criteria must be a non-empty mapping")
            if any(not isinstance(key, str) or not key for key in criteria):
                raise ValueError(f"{question_id}.criteria option ids must be non-empty strings")
        elif question_type == "score":
            if (
                not isinstance(criteria, list)
                or not criteria
                or any(not isinstance(item, str) for item in criteria)
            ):
                raise ValueError(f"{question_id}.criteria must be a non-empty list of strings")
        elif criteria is not None:
            if not isinstance(criteria, Mapping):
                raise ValueError(f"{question_id}.criteria must be an object when present")


def unwrap_cloudflare_rest(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("response payload must be a JSON object")
    if "success" not in payload:
        return payload
    if payload.get("success") is not True:
        raise ValueError(
            f"Cloudflare REST request was not successful: errors={payload.get('errors')!r}"
        )
    result = payload.get("result")
    if not isinstance(result, Mapping):
        raise ValueError("Cloudflare REST envelope must contain an object result")
    return result


def validate_response(
    payload: Mapping[str, Any],
    request: Mapping[str, Any],
    *,
    probability_tolerance: float = 0.002,
) -> Mapping[str, Any]:
    validate_request(request)
    response = unwrap_cloudflare_rest(payload)

    if not isinstance(response.get("model"), str):
        raise ValueError("response.model must be a string")
    answers = response.get("answers")
    if not isinstance(answers, Mapping):
        raise ValueError("response.answers must be an object")
    questions = request["questions"]
    if set(answers) != set(questions):
        raise ValueError(
            f"answer ids mismatch: expected={sorted(questions)} actual={sorted(answers)}"
        )
    if not isinstance(response.get("usage"), Mapping):
        raise ValueError("response.usage must be an object")

    for question_id, question in questions.items():
        answer = answers[question_id]
        if not isinstance(answer, Mapping):
            raise ValueError(f"answer {question_id} must be an object")
        question_type = question["type"]
        if answer.get("type") != question_type:
            raise ValueError(
                f"answer {question_id}.type mismatch: "
                f"expected={question_type!r} actual={answer.get('type')!r}"
            )

        if question_type == "noul":
            _probability(answer.get("noul"), f"{question_id}.noul")
            continue

        if question_type == "choice":
            options = [str(key) for key in question["criteria"]]
            chosen = answer.get("choice")
            if chosen not in options:
                raise ValueError(f"{question_id}.choice is not an allowed option")
            confidence = _probability(answer.get("confidence"), f"{question_id}.confidence")
            probabilities = answer.get("probabilities")
            if not isinstance(probabilities, Mapping):
                raise ValueError(f"{question_id}.probabilities must be an object")
            _validate_distribution(
                probabilities,
                options,
                tolerance=probability_tolerance,
            )
            if abs(confidence - float(probabilities[chosen])) > probability_tolerance:
                raise ValueError(f"{question_id}.confidence must match chosen probability")
            continue

        levels = [str(i) for i in range(len(question["criteria"]))]
        probabilities = answer.get("probabilities")
        if not isinstance(probabilities, Mapping):
            raise ValueError(f"{question_id}.probabilities must be an object")
        _validate_distribution(
            probabilities,
            levels,
            tolerance=probability_tolerance,
        )
        score = answer.get("score")
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            raise ValueError(f"{question_id}.score must be numeric")
        if not 0.0 <= float(score) <= len(levels) - 1:
            raise ValueError(f"{question_id}.score is outside the expected range")
        _probability(answer.get("confidence"), f"{question_id}.confidence")

        legend = answer.get("legend")
        if not isinstance(legend, Mapping):
            raise ValueError(f"{question_id}.legend must be an object")
        expected_legend = dict(zip(levels, question["criteria"]))
        if dict(legend) != expected_legend:
            raise ValueError(f"{question_id}.legend does not match score criteria")

    return response

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib import error as urllib_error
from urllib import request as urllib_request

from semantic_provider import CandidateDecision, SemanticDecisionResult


CRITERIA = {
    "required": (
        "The current task could be materially wrong or unsafe if this record is omitted."
    ),
    "useful": (
        "The record adds relevant context, but the task can still be completed correctly "
        "without it."
    ),
    "irrelevant": "The record does not materially help with the current task.",
}

BUNDLE_ID = "jevbert-poc-nli-ja-en-0.2.0"

Transport = Callable[[str, str, Mapping[str, Any]], Mapping[str, Any]]


def build_jevbert_question(*, task: str, pddr_id: str) -> dict[str, Any]:
    return {
        "type": "choice",
        "instructions": (
            f"Current task: {task}\n\n"
            f"Classify the relevance of historical decision record {pddr_id} "
            "in the state to the current task. Treat the PDDR as decision "
            "history/evidence, not automatically executable policy."
        ),
        "criteria": CRITERIA,
    }


def _default_transport(
    endpoint: str,
    api_key: str,
    payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
    req = urllib_request.Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=300) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"provider HTTP {exc.code} from {endpoint}: {detail}"
        ) from exc


@dataclass
class TypedDecisionBertHttpProvider:
    api_key: str
    endpoint: str = "http://127.0.0.1:8765/v1/systemone"
    transport: Transport = _default_transport

    @property
    def name(self) -> str:
        return "typed-decision-bert-v0.1"

    def classify(
        self,
        *,
        task: str,
        records: Mapping[str, str],
    ) -> SemanticDecisionResult:
        decisions: list[CandidateDecision] = []
        total_input_tokens = 0
        total_http_seconds = 0.0

        for pddr_id in sorted(records):
            payload = {
                "model": BUNDLE_ID,
                "state": records[pddr_id],
                "questions": {
                    "relevance": build_jevbert_question(
                        task=task,
                        pddr_id=pddr_id,
                    )
                },
            }
            started = time.perf_counter()
            raw = self.transport(self.endpoint, self.api_key, payload)
            elapsed = time.perf_counter() - started
            total_http_seconds += elapsed

            if raw.get("model") != BUNDLE_ID:
                raise ValueError(
                    f"unexpected bundle id for {pddr_id}: {raw.get('model')}"
                )

            answers = raw.get("answers")
            if not isinstance(answers, Mapping):
                raise ValueError(f"provider response has no answers for {pddr_id}")
            answer = answers.get("relevance")
            if not isinstance(answer, Mapping):
                raise ValueError(f"provider response missing relevance for {pddr_id}")

            probs = answer.get("probabilities")
            if not isinstance(probs, Mapping):
                raise ValueError(f"provider response for {pddr_id} has no probabilities")
            missing = set(CRITERIA) - set(probs)
            if missing:
                raise ValueError(
                    f"provider response for {pddr_id} missing labels: {sorted(missing)}"
                )

            values = [
                float(probs[label])
                for label in ("required", "useful", "irrelevant")
            ]
            total = sum(values)
            if total <= 0:
                raise ValueError(
                    f"provider response for {pddr_id} has zero probability mass"
                )
            required, useful, irrelevant = [value / total for value in values]

            usage = raw.get("usage")
            input_tokens = (
                int(usage.get("input_tokens", 0))
                if isinstance(usage, Mapping)
                else 0
            )
            total_input_tokens += input_tokens

            decisions.append(
                CandidateDecision(
                    pddr_id=pddr_id,
                    required_probability=required,
                    useful_probability=useful,
                    irrelevant_probability=irrelevant,
                    metadata={
                        "backend_choice": answer.get("choice"),
                        "backend_confidence": answer.get("confidence"),
                        "input_tokens": input_tokens,
                        "http_seconds": elapsed,
                    },
                )
            )

        return SemanticDecisionResult(
            provider=self.name,
            decisions=decisions,
            metadata={
                "backend_calls": len(records),
                "packing_version": "jevbert-a0-one-record-v0.1",
                "total_input_tokens": total_input_tokens,
                "total_http_seconds": total_http_seconds,
            },
        )

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib import request as urllib_request

from semantic_provider import CandidateDecision, SemanticDecisionResult


Transport = Callable[[str, Mapping[str, Any]], Mapping[str, Any]]


def _default_transport(endpoint: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


@dataclass
class OpenJevHttpProvider:
    """Adapter for intikhab49/open-jev-typed-decision-engine's /decide API."""

    endpoint: str = "http://127.0.0.1:8000/decide"
    calibrated: bool = True
    transport: Transport = _default_transport

    @property
    def name(self) -> str:
        return "open-jev-typed-decision-engine"

    def classify(
        self,
        *,
        task: str,
        records: Mapping[str, str],
    ) -> SemanticDecisionResult:
        state = {
            "task": task,
            "pddr_records": records,
            "instruction": (
                "Classify each named PDDR record only by its relevance to the current task. "
                "Do not treat historical PDDR as executable policy."
            ),
        }
        criteria = {
            "required": (
                "The current task could be materially wrong or unsafe if this record is omitted."
            ),
            "useful": (
                "The record adds relevant context, but the task can still be completed correctly "
                "without it."
            ),
            "irrelevant": (
                "The record does not materially help with the current task."
            ),
        }
        questions = {
            pddr_id: {
                "type": "choice",
                "instructions": (
                    f"For the current task, classify the relevance of {pddr_id}. "
                    "Use the record with that exact ID from pddr_records."
                ),
                "criteria": criteria,
            }
            for pddr_id in sorted(records)
        }

        raw = self.transport(
            self.endpoint,
            {
                "state": state,
                "questions": questions,
                "calibrated": self.calibrated,
            },
        )

        decisions = []
        for pddr_id in sorted(records):
            if pddr_id not in raw:
                raise ValueError(f"provider response missing {pddr_id}")
            answer = raw[pddr_id]
            probs = answer.get("probabilities")
            if not isinstance(probs, Mapping):
                raise ValueError(f"provider response for {pddr_id} has no probabilities")
            missing = {"required", "useful", "irrelevant"} - set(probs)
            if missing:
                raise ValueError(
                    f"provider response for {pddr_id} missing labels: {sorted(missing)}"
                )
            values = [float(probs[label]) for label in ("required", "useful", "irrelevant")]
            total = sum(values)
            if total <= 0:
                raise ValueError(f"provider response for {pddr_id} has zero probability mass")
            required, useful, irrelevant = [value / total for value in values]
            decisions.append(
                CandidateDecision(
                    pddr_id=pddr_id,
                    required_probability=required,
                    useful_probability=useful,
                    irrelevant_probability=irrelevant,
                    metadata={
                        "backend_label": answer.get("label"),
                        "backend_confidence": answer.get("confidence"),
                    },
                )
            )

        return SemanticDecisionResult(
            provider=self.name,
            decisions=decisions,
            metadata={
                "endpoint_kind": "open-jev-/decide",
                "calibrated": self.calibrated,
            },
        )

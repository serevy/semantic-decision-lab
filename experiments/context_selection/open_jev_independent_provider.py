from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from open_jev_http_provider import OpenJevHttpProvider
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


def build_independent_request(
    *,
    task: str,
    pddr_id: str,
    record: str,
    calibrated: bool,
) -> dict[str, Any]:
    return {
        "state": record,
        "questions": {
            "relevance": {
                "type": "choice",
                "instructions": (
                    f"Current task: {task}\n\n"
                    f"Classify the relevance of historical decision record {pddr_id} "
                    "in the state to the current task. Treat the PDDR as decision "
                    "history/evidence, not automatically executable policy."
                ),
                "criteria": CRITERIA,
            }
        },
        "calibrated": calibrated,
    }


@dataclass
class OpenJevIndependentHttpProvider(OpenJevHttpProvider):
    """Open Jev v0.2: one PDDR record per backend request."""

    @property
    def name(self) -> str:
        return "open-jev-typed-decision-engine-v0.2-independent"

    def classify(
        self,
        *,
        task: str,
        records: Mapping[str, str],
    ) -> SemanticDecisionResult:
        decisions: list[CandidateDecision] = []

        for pddr_id in sorted(records):
            payload = build_independent_request(
                task=task,
                pddr_id=pddr_id,
                record=records[pddr_id],
                calibrated=self.calibrated,
            )
            raw = self.transport(self.endpoint, payload)
            answer = raw.get("relevance")
            if not isinstance(answer, Mapping):
                raise ValueError(f"provider response missing relevance answer for {pddr_id}")

            probs = answer.get("probabilities")
            if not isinstance(probs, Mapping):
                raise ValueError(f"provider response for {pddr_id} has no probabilities")

            missing = set(CRITERIA) - set(probs)
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
                "packing_version": "v0.2-independent-record",
                "backend_calls": len(records),
            },
        )

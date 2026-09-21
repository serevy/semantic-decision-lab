from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

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


class LayaAgent(Protocol):
    def predict(
        self,
        state: str,
        questions: Mapping[str, Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        ...


def build_laya_question(*, task: str, pddr_id: str) -> dict[str, Any]:
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


@dataclass
class LayaMultilingualProvider:
    """Adapter for the pinned Laya multilingual checkpoint."""

    agent: LayaAgent

    @property
    def name(self) -> str:
        return "laya-multilingual-v0.1"

    def classify(
        self,
        *,
        task: str,
        records: Mapping[str, str],
    ) -> SemanticDecisionResult:
        decisions: list[CandidateDecision] = []
        total_input_tokens = 0

        for pddr_id in sorted(records):
            question = build_laya_question(task=task, pddr_id=pddr_id)
            raw = self.agent.predict(
                records[pddr_id],
                {"relevance": question},
            )
            answers = raw.get("answers")
            if not isinstance(answers, Mapping):
                raise ValueError(f"Laya response has no answers for {pddr_id}")
            answer = answers.get("relevance")
            if not isinstance(answer, Mapping):
                raise ValueError(f"Laya response missing relevance answer for {pddr_id}")

            probs = answer.get("probabilities")
            if not isinstance(probs, Mapping):
                raise ValueError(f"Laya response for {pddr_id} has no probabilities")
            missing = set(CRITERIA) - set(probs)
            if missing:
                raise ValueError(
                    f"Laya response for {pddr_id} missing labels: {sorted(missing)}"
                )

            values = [
                float(probs[label])
                for label in ("required", "useful", "irrelevant")
            ]
            total = sum(values)
            if total <= 0:
                raise ValueError(f"Laya response for {pddr_id} has zero probability mass")
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
                    },
                )
            )

        return SemanticDecisionResult(
            provider=self.name,
            decisions=decisions,
            metadata={
                "backend_calls": len(records),
                "packing_version": "laya-independent-record-v0.1",
                "total_input_tokens": total_input_tokens,
            },
        )

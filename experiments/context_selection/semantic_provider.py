from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence


_LABELS = ("required", "useful", "irrelevant")


@dataclass(frozen=True)
class CandidateDecision:
    """Provider-neutral typed classification for one PDDR candidate."""

    pddr_id: str
    required_probability: float
    useful_probability: float
    irrelevant_probability: float
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        probabilities = (
            self.required_probability,
            self.useful_probability,
            self.irrelevant_probability,
        )
        if any(p < 0.0 or p > 1.0 for p in probabilities):
            raise ValueError("probabilities must be between 0 and 1")
        if abs(sum(probabilities) - 1.0) > 1e-6:
            raise ValueError("required/useful/irrelevant probabilities must sum to 1")

    @property
    def label(self) -> str:
        values = {
            "required": self.required_probability,
            "useful": self.useful_probability,
            "irrelevant": self.irrelevant_probability,
        }
        return max(_LABELS, key=lambda label: (values[label], -_LABELS.index(label)))

    @property
    def confidence(self) -> float:
        return max(
            self.required_probability,
            self.useful_probability,
            self.irrelevant_probability,
        )


@dataclass(frozen=True)
class SemanticDecisionResult:
    provider: str
    decisions: Sequence[CandidateDecision]
    abstained: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


class SemanticDecisionProvider(Protocol):
    """Backend boundary. Adapters may batch, loop, call APIs, or run locally."""

    @property
    def name(self) -> str:
        ...

    def classify(
        self,
        *,
        task: str,
        records: Mapping[str, str],
    ) -> SemanticDecisionResult:
        """Classify every candidate as required/useful/irrelevant probabilities."""
        ...


def validate_result(
    result: SemanticDecisionResult,
    expected_ids: Sequence[str],
) -> None:
    expected = set(expected_ids)
    actual = [decision.pddr_id for decision in result.decisions]
    if len(actual) != len(set(actual)):
        raise ValueError("provider returned duplicate PDDR IDs")
    if set(actual) != expected:
        missing = sorted(expected - set(actual))
        unknown = sorted(set(actual) - expected)
        raise ValueError(f"provider candidate mismatch: missing={missing}, unknown={unknown}")


def select_top_k(
    result: SemanticDecisionResult,
    *,
    top_k: int,
) -> list[str]:
    """Apply one provider-independent ranking/cutoff policy.

    Required-context probability is primary because missing required context is
    the experiment's highest-severity error. Useful probability is the fixed
    secondary key; PDDR ID is the deterministic final tie-break.
    """
    if top_k < 0:
        raise ValueError("top_k must be non-negative")
    if result.abstained:
        return []
    ranked = sorted(
        result.decisions,
        key=lambda d: (
            -d.required_probability,
            -d.useful_probability,
            d.pddr_id,
        ),
    )
    return [decision.pddr_id for decision in ranked[:top_k]]

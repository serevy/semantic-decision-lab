from __future__ import annotations

import json
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


Transport = Callable[[str, Mapping[str, Any]], Mapping[str, Any]]


def build_zefan_question(*, task: str, pddr_id: str) -> dict[str, Any]:
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


def _default_transport(endpoint: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
    body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
    req = urllib_request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
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
class ZefanOpenJev2BHttpProvider:
    endpoint: str = "http://127.0.0.1:8791/v1/systemone"
    transport: Transport = _default_transport

    @property
    def name(self) -> str:
        return "zefan-open-jev-2b-v0.1"

    def classify(
        self,
        *,
        task: str,
        records: Mapping[str, str],
    ) -> SemanticDecisionResult:
        decisions: list[CandidateDecision] = []
        total_input_tokens = 0
        total_inference_seconds = 0.0
        identity: dict[str, Any] | None = None

        for pddr_id in sorted(records):
            payload = {
                "model": "open-jev",
                "state": records[pddr_id],
                "questions": {
                    "relevance": build_zefan_question(
                        task=task,
                        pddr_id=pddr_id,
                    )
                },
            }
            raw = self.transport(self.endpoint, payload)
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
                raise ValueError(f"provider response for {pddr_id} has zero probability mass")
            required, useful, irrelevant = [value / total for value in values]

            usage = raw.get("usage")
            input_tokens = (
                int(usage.get("input_tokens", 0))
                if isinstance(usage, Mapping)
                else 0
            )
            total_input_tokens += input_tokens

            metadata = raw.get("metadata")
            if not isinstance(metadata, Mapping):
                raise ValueError(f"provider response for {pddr_id} has no metadata")
            inference_seconds = float(metadata.get("inference_seconds", 0.0))
            total_inference_seconds += inference_seconds

            prefix_cache = metadata.get("prefix_cache")
            observed_identity = {
                "model": raw.get("model"),
                "method": metadata.get("method"),
                "temperature": metadata.get("temperature"),
                "checkpoint_sha256": metadata.get("checkpoint_sha256"),
                "base_revision": metadata.get("base_revision"),
                "max_length": metadata.get("max_length"),
                "code_commit": metadata.get("code_commit"),
                "prefix_cache_enabled": (
                    prefix_cache.get("enabled")
                    if isinstance(prefix_cache, Mapping)
                    else None
                ),
                "prefix_cache_mode": (
                    prefix_cache.get("mode")
                    if isinstance(prefix_cache, Mapping)
                    else None
                ),
            }
            if identity is None:
                identity = observed_identity
            elif observed_identity != identity:
                raise ValueError(
                    "provider runtime identity changed between candidate calls"
                )

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
                        "inference_seconds": inference_seconds,
                    },
                )
            )

        return SemanticDecisionResult(
            provider=self.name,
            decisions=decisions,
            metadata={
                "backend_calls": len(records),
                "packing_version": "zefan-independent-record-v0.1",
                "total_input_tokens": total_input_tokens,
                "total_inference_seconds": total_inference_seconds,
                "identity": identity or {},
            },
        )

import unittest

from semantic_provider import select_top_k, validate_result
from typed_decision_bert_provider import (
    TypedDecisionBertHttpProvider,
    build_jevbert_question,
)


class TypedDecisionBertProviderTest(unittest.TestCase):
    def test_question_matches_shared_three_labels(self):
        q = build_jevbert_question(task="upgrade safely", pddr_id="PDDR-0007")
        self.assertEqual(q["type"], "choice")
        self.assertIn("upgrade safely", q["instructions"])
        self.assertIn("PDDR-0007", q["instructions"])
        self.assertEqual(
            list(q["criteria"]),
            ["required", "useful", "irrelevant"],
        )

    def test_one_http_call_per_record(self):
        calls = []

        def fake_transport(endpoint, api_key, payload):
            calls.append((endpoint, api_key, payload))
            instructions = payload["questions"]["relevance"]["instructions"]
            strong = "PDDR-0002" in instructions
            probs = (
                {"required": 0.8, "useful": 0.15, "irrelevant": 0.05}
                if strong
                else {"required": 0.2, "useful": 0.7, "irrelevant": 0.1}
            )
            return {
                "model": "jevbert-poc-nli-ja-en-0.2.0",
                "answers": {
                    "relevance": {
                        "type": "choice",
                        "choice": max(probs, key=probs.get),
                        "probabilities": probs,
                        "confidence": 0.5,
                    }
                },
                "usage": {"input_tokens": 321, "output_tokens": 0},
            }

        provider = TypedDecisionBertHttpProvider(
            api_key="x" * 32,
            transport=fake_transport,
        )
        result = provider.classify(
            task="test task",
            records={"PDDR-0001": "one", "PDDR-0002": "two"},
        )

        self.assertEqual(len(calls), 2)
        validate_result(result, ["PDDR-0001", "PDDR-0002"])
        self.assertEqual(select_top_k(result, top_k=1), ["PDDR-0002"])
        self.assertEqual(result.metadata["total_input_tokens"], 642)


if __name__ == "__main__":
    unittest.main()

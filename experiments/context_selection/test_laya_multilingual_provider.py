import unittest

from laya_multilingual_provider import (
    LayaMultilingualProvider,
    build_laya_question,
)
from semantic_provider import select_top_k, validate_result


class FakeAgent:
    def __init__(self):
        self.calls = []

    def predict(self, state, questions):
        self.calls.append((state, questions))
        instructions = questions["relevance"]["instructions"]
        if "PDDR-0002" in instructions:
            probs = {"required": 0.8, "useful": 0.15, "irrelevant": 0.05}
        else:
            probs = {"required": 0.2, "useful": 0.7, "irrelevant": 0.1}
        return {
            "answers": {
                "relevance": {
                    "type": "choice",
                    "choice": max(probs, key=probs.get),
                    "probabilities": probs,
                    "confidence": 0.5,
                }
            },
            "usage": {"input_tokens": 123, "output_tokens": 0},
        }


class LayaMultilingualProviderTest(unittest.TestCase):
    def test_question_matches_shared_three_labels(self):
        q = build_laya_question(task="upgrade safely", pddr_id="PDDR-0007")
        self.assertEqual(q["type"], "choice")
        self.assertIn("upgrade safely", q["instructions"])
        self.assertIn("PDDR-0007", q["instructions"])
        self.assertEqual(
            list(q["criteria"]),
            ["required", "useful", "irrelevant"],
        )

    def test_one_agent_call_per_record_and_shared_ranking(self):
        agent = FakeAgent()
        provider = LayaMultilingualProvider(agent)
        result = provider.classify(
            task="test task",
            records={"PDDR-0001": "one", "PDDR-0002": "two"},
        )

        self.assertEqual(len(agent.calls), 2)
        validate_result(result, ["PDDR-0001", "PDDR-0002"])
        self.assertEqual(select_top_k(result, top_k=1), ["PDDR-0002"])
        self.assertEqual(result.metadata["backend_calls"], 2)
        self.assertEqual(result.metadata["total_input_tokens"], 246)


if __name__ == "__main__":
    unittest.main()

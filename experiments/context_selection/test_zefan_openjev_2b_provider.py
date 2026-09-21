import unittest

from semantic_provider import select_top_k, validate_result
from zefan_openjev_2b_provider import (
    ZefanOpenJev2BHttpProvider,
    build_zefan_question,
)


class ZefanOpenJev2BProviderTest(unittest.TestCase):
    def test_question_matches_shared_three_labels(self):
        q = build_zefan_question(task="upgrade safely", pddr_id="PDDR-0007")
        self.assertEqual(q["type"], "choice")
        self.assertIn("upgrade safely", q["instructions"])
        self.assertIn("PDDR-0007", q["instructions"])
        self.assertEqual(
            list(q["criteria"]),
            ["required", "useful", "irrelevant"],
        )

    def test_one_http_call_per_record_and_identity_capture(self):
        calls = []

        def fake_transport(endpoint, payload):
            calls.append((endpoint, payload))
            instructions = payload["questions"]["relevance"]["instructions"]
            strong = "PDDR-0002" in instructions
            probs = (
                {"required": 0.8, "useful": 0.15, "irrelevant": 0.05}
                if strong
                else {"required": 0.2, "useful": 0.7, "irrelevant": 0.1}
            )
            return {
                "model": "Qwen/Qwen3.5-2B",
                "answers": {
                    "relevance": {
                        "type": "choice",
                        "choice": max(probs, key=probs.get),
                        "probabilities": probs,
                        "confidence": 0.5,
                    }
                },
                "usage": {"input_tokens": 321, "output_tokens": 0},
                "metadata": {
                    "method": "lora_decision_head",
                    "temperature": 1.5,
                    "candidate_sequences": 3,
                    "inference_seconds": 0.25,
                    "checkpoint_sha256": "checkpoint",
                    "base_revision": "base",
                    "max_length": 4096,
                    "code_commit": "code",
                    "prefix_cache": {
                        "enabled": False,
                        "mode": "independent_candidates",
                    },
                },
            }

        provider = ZefanOpenJev2BHttpProvider(transport=fake_transport)
        result = provider.classify(
            task="test task",
            records={"PDDR-0001": "one", "PDDR-0002": "two"},
        )

        self.assertEqual(len(calls), 2)
        validate_result(result, ["PDDR-0001", "PDDR-0002"])
        self.assertEqual(select_top_k(result, top_k=1), ["PDDR-0002"])
        self.assertEqual(result.metadata["total_input_tokens"], 642)
        self.assertAlmostEqual(result.metadata["total_inference_seconds"], 0.5)
        self.assertFalse(result.metadata["identity"]["prefix_cache_enabled"])


if __name__ == "__main__":
    unittest.main()

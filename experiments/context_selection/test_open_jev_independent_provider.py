import unittest

from open_jev_independent_provider import (
    OpenJevIndependentHttpProvider,
    build_independent_request,
)
from semantic_provider import select_top_k, validate_result


class OpenJevIndependentProviderTest(unittest.TestCase):
    def test_task_is_in_question_and_state_is_one_record(self):
        payload = build_independent_request(
            task="upgrade safely",
            pddr_id="PDDR-0007",
            record="record body",
            calibrated=True,
        )
        self.assertEqual(payload["state"], "record body")
        self.assertIn("upgrade safely", payload["questions"]["relevance"]["instructions"])
        self.assertIn("PDDR-0007", payload["questions"]["relevance"]["instructions"])
        self.assertEqual(
            set(payload["questions"]["relevance"]["criteria"]),
            {"required", "useful", "irrelevant"},
        )

    def test_one_transport_call_per_record(self):
        payloads = []

        def fake_transport(endpoint, payload):
            payloads.append(payload)
            pddr_id = (
                "PDDR-0002"
                if "PDDR-0002" in payload["questions"]["relevance"]["instructions"]
                else "PDDR-0001"
            )
            required = 0.8 if pddr_id == "PDDR-0002" else 0.2
            return {
                "relevance": {
                    "label": "required" if required > 0.5 else "useful",
                    "confidence": required,
                    "probabilities": {
                        "required": required,
                        "useful": 0.15 if required > 0.5 else 0.7,
                        "irrelevant": 0.05 if required > 0.5 else 0.1,
                    },
                }
            }

        provider = OpenJevIndependentHttpProvider(transport=fake_transport)
        result = provider.classify(
            task="test task",
            records={"PDDR-0001": "one", "PDDR-0002": "two"},
        )

        self.assertEqual(len(payloads), 2)
        validate_result(result, ["PDDR-0001", "PDDR-0002"])
        self.assertEqual(select_top_k(result, top_k=1), ["PDDR-0002"])
        self.assertEqual(result.metadata["packing_version"], "v0.2-independent-record")


if __name__ == "__main__":
    unittest.main()

import unittest

from open_jev_http_provider import OpenJevHttpProvider
from semantic_provider import select_top_k, validate_result


class OpenJevHttpProviderTest(unittest.TestCase):
    def test_maps_backend_probabilities_to_contract(self):
        captured = {}

        def fake_transport(endpoint, payload):
            captured["endpoint"] = endpoint
            captured["payload"] = payload
            return {
                "PDDR-0001": {
                    "label": "useful",
                    "confidence": 0.6,
                    "probabilities": {
                        "irrelevant": 0.1,
                        "required": 0.3,
                        "useful": 0.6,
                    },
                },
                "PDDR-0002": {
                    "label": "required",
                    "confidence": 0.8,
                    "probabilities": {
                        "required": 0.8,
                        "useful": 0.15,
                        "irrelevant": 0.05,
                    },
                },
            }

        provider = OpenJevHttpProvider(
            endpoint="http://example.test/decide",
            transport=fake_transport,
        )
        result = provider.classify(
            task="current task",
            records={"PDDR-0001": "one", "PDDR-0002": "two"},
        )

        validate_result(result, ["PDDR-0001", "PDDR-0002"])
        self.assertEqual(select_top_k(result, top_k=1), ["PDDR-0002"])
        self.assertTrue(captured["payload"]["calibrated"])
        self.assertEqual(
            captured["payload"]["questions"]["PDDR-0001"]["type"],
            "choice",
        )
        self.assertEqual(
            set(captured["payload"]["questions"]["PDDR-0001"]["criteria"]),
            {"required", "useful", "irrelevant"},
        )

    def test_normalizes_probability_mass(self):
        def fake_transport(endpoint, payload):
            return {
                "PDDR-0001": {
                    "probabilities": {
                        "required": 2.0,
                        "useful": 1.0,
                        "irrelevant": 1.0,
                    }
                }
            }

        result = OpenJevHttpProvider(transport=fake_transport).classify(
            task="x",
            records={"PDDR-0001": "one"},
        )
        decision = result.decisions[0]
        self.assertAlmostEqual(decision.required_probability, 0.5)
        self.assertAlmostEqual(decision.useful_probability, 0.25)
        self.assertAlmostEqual(decision.irrelevant_probability, 0.25)

    def test_missing_candidate_is_rejected(self):
        def fake_transport(endpoint, payload):
            return {}

        with self.assertRaises(ValueError):
            OpenJevHttpProvider(transport=fake_transport).classify(
                task="x",
                records={"PDDR-0001": "one"},
            )


if __name__ == "__main__":
    unittest.main()

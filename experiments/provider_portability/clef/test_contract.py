import json
import unittest
from pathlib import Path

from contract import unwrap_cloudflare_rest, validate_request, validate_response


ROOT = Path(__file__).resolve().parent
FIXTURE = json.loads((ROOT / "systemone-contract.v0.1.json").read_text(encoding="utf-8"))
REQUEST = FIXTURE["request"]


def valid_response():
    return {
        "model": "clef-flash",
        "answers": {
            "outage": {"type": "noul", "noul": 0.99},
            "owner": {
                "type": "choice",
                "choice": "payments",
                "confidence": 0.8,
                "probabilities": {
                    "payments": 0.8,
                    "storefront": 0.1,
                    "support": 0.1,
                },
            },
            "severity": {
                "type": "score",
                "score": 2.7,
                "confidence": 0.75,
                "legend": {
                    "0": "No impact",
                    "1": "Minor",
                    "2": "Major",
                    "3": "Critical",
                },
                "probabilities": {
                    "0": 0.0,
                    "1": 0.05,
                    "2": 0.2,
                    "3": 0.75,
                },
            },
        },
        "usage": {"input_tokens": 123},
    }


class ClefContractTest(unittest.TestCase):
    def test_frozen_request_is_valid(self):
        validate_request(REQUEST)

    def test_direct_systemone_response_is_valid(self):
        validate_response(valid_response(), REQUEST)

    def test_cloudflare_rest_envelope_is_unwrapped(self):
        response = valid_response()
        wrapped = {"result": response, "success": True, "errors": [], "messages": []}
        self.assertIs(unwrap_cloudflare_rest(wrapped), response)
        validate_response(wrapped, REQUEST)

    def test_missing_answer_is_rejected(self):
        response = valid_response()
        del response["answers"]["owner"]
        with self.assertRaises(ValueError):
            validate_response(response, REQUEST)

    def test_unknown_choice_is_rejected(self):
        response = valid_response()
        response["answers"]["owner"]["choice"] = "security"
        with self.assertRaises(ValueError):
            validate_response(response, REQUEST)

    def test_bad_probability_sum_is_rejected(self):
        response = valid_response()
        response["answers"]["owner"]["probabilities"]["payments"] = 0.6
        with self.assertRaises(ValueError):
            validate_response(response, REQUEST)

    def test_score_outside_legend_range_is_rejected(self):
        response = valid_response()
        response["answers"]["severity"]["score"] = 4.0
        with self.assertRaises(ValueError):
            validate_response(response, REQUEST)

    def test_more_than_64_questions_is_rejected(self):
        request = json.loads(json.dumps(REQUEST))
        prototype = request["questions"]["outage"]
        request["questions"] = {
            f"q{i}": prototype for i in range(65)
        }
        with self.assertRaises(ValueError):
            validate_request(request)


if __name__ == "__main__":
    unittest.main()

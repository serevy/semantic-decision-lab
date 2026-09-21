import unittest

from fastapi.testclient import TestClient

from serve_open_jev_v02 import build_app


class OpenJevV02ServerSchemaTest(unittest.TestCase):
    def test_decide_accepts_json_body(self):
        observed = {}

        def fake_decide(state, questions, calibrated):
            observed["state"] = state
            observed["questions"] = questions
            observed["calibrated"] = calibrated
            return {
                "relevance": {
                    "label": "useful",
                    "confidence": 0.7,
                    "probabilities": {
                        "required": 0.2,
                        "useful": 0.7,
                        "irrelevant": 0.1,
                    },
                }
            }

        client = TestClient(build_app(fake_decide))
        payload = {
            "state": "PDDR body",
            "questions": {
                "relevance": {
                    "type": "choice",
                    "instructions": "Current task: test",
                    "criteria": {
                        "required": "required",
                        "useful": "useful",
                        "irrelevant": "irrelevant",
                    },
                }
            },
            "calibrated": True,
        }

        response = client.post("/decide", json=payload)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(observed["state"], payload["state"])
        self.assertEqual(observed["questions"], payload["questions"])
        self.assertTrue(observed["calibrated"])
        self.assertEqual(response.json()["relevance"]["label"], "useful")


if __name__ == "__main__":
    unittest.main()

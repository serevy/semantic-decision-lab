import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

from phase1a.analyze import compare_answer
from phase1a.probes import build_request, load_matrix, load_source_fixture, validate_matrix
from run_workers_ai_smoke import canonical_json, wire_json


ROOT = Path(__file__).resolve().parent


class Phase1AFreezeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = load_matrix()
        cls.source = load_source_fixture(cls.matrix)
        cls.materialized = validate_matrix(cls.matrix)
        cls.variants = {variant["id"]: variant for variant in cls.matrix["variants"]}

    def test_exactly_fourteen_variants_are_frozen(self):
        self.assertEqual(len(self.matrix["variants"]), 14)
        self.assertEqual(len(self.materialized), 14)

    def test_question_order_changes_wire_bytes_not_canonical_content(self):
        baseline = build_request(self.variants["packed-canonical"], self.source)
        reordered = build_request(
            self.variants["packed-qorder-owner-severity-outage"],
            self.source,
        )
        self.assertEqual(canonical_json(baseline), canonical_json(reordered))
        self.assertNotEqual(wire_json(baseline), wire_json(reordered))

    def test_choice_order_changes_wire_bytes_not_canonical_content(self):
        baseline = build_request(self.variants["packed-canonical"], self.source)
        reordered = build_request(
            self.variants["packed-choice-support-storefront-payments"],
            self.source,
        )
        self.assertEqual(canonical_json(baseline), canonical_json(reordered))
        self.assertNotEqual(wire_json(baseline), wire_json(reordered))

    def test_top_level_and_state_mapping_order_are_fixed_across_variants(self):
        baseline = build_request(self.variants["packed-canonical"], self.source)
        expected_top_level = list(baseline)
        expected_state_order = list(baseline["state"])
        for variant in self.matrix["variants"]:
            request = build_request(variant, self.source)
            self.assertEqual(list(request), expected_top_level)
            self.assertEqual(list(request["state"]), expected_state_order)
            self.assertEqual(request["state"], baseline["state"])

    def test_score_criteria_order_never_changes(self):
        expected = self.source["request"]["questions"]["severity"]["criteria"]
        for variant in self.matrix["variants"]:
            request = build_request(variant, self.source)
            if "severity" in request["questions"]:
                self.assertEqual(request["questions"]["severity"]["criteria"], expected)


class Phase1AMetricTest(unittest.TestCase):
    def test_choice_metrics_detect_order_sensitive_output(self):
        baseline = {
            "type": "choice",
            "choice": "a",
            "confidence": 0.8,
            "probabilities": {"a": 0.8, "b": 0.2},
        }
        variant = {
            "type": "choice",
            "choice": "b",
            "confidence": 0.6,
            "probabilities": {"a": 0.4, "b": 0.6},
        }
        metrics = compare_answer(baseline, variant)
        self.assertTrue(metrics["top_choice_flip"])
        self.assertAlmostEqual(metrics["per_option_max_absolute_delta"], 0.4)
        self.assertGreater(metrics["jensen_shannon_divergence_base2"], 0.0)

    def test_score_expected_value_delta_is_separate_from_reported_score(self):
        baseline = {
            "type": "score",
            "score": 1.0,
            "confidence": 0.7,
            "probabilities": {"0": 0.0, "1": 1.0, "2": 0.0},
        }
        variant = {
            "type": "score",
            "score": 1.2,
            "confidence": 0.6,
            "probabilities": {"0": 0.0, "1": 0.5, "2": 0.5},
        }
        metrics = compare_answer(baseline, variant)
        self.assertAlmostEqual(metrics["reported_score_absolute_delta"], 0.2)
        self.assertAlmostEqual(metrics["expected_score_absolute_delta"], 0.5)


if __name__ == "__main__":
    unittest.main()

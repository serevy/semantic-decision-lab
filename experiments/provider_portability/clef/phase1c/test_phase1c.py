import unittest

from phase1c.probes import load_manifest, validate_manifest


class Phase1CFreezeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_manifest()
        cls.cases = validate_manifest(cls.manifest)

    def test_exact_schedule_and_call_count_are_frozen(self):
        self.assertEqual(self.manifest["condition_count"], 18)
        self.assertEqual(self.manifest["repeats_per_condition"], 3)
        self.assertEqual(self.manifest["expected_provider_calls"], 54)
        self.assertEqual(len(self.cases), 54)

    def test_each_condition_occurs_once_per_round(self):
        repeats = {}
        for case in self.cases:
            key = (case["fixture_id"], case["variant"]["id"])
            repeats.setdefault(key, set()).add(case["repeat_index"])
        self.assertEqual(len(repeats), 18)
        self.assertTrue(all(value == {1, 2, 3} for value in repeats.values()))

    def test_same_condition_has_same_wire_hash_across_repeats(self):
        hashes = {}
        for case in self.cases:
            key = (case["fixture_id"], case["variant"]["id"])
            hashes.setdefault(key, set()).add(case["wire_request_sha256"])
        self.assertTrue(all(len(value) == 1 for value in hashes.values()))

    def test_no_choice_order_or_single_question_conditions_are_included(self):
        ids = self.manifest["question_order_variants"]
        self.assertEqual(len(ids), 6)
        self.assertFalse(any("choice-" in value for value in ids))
        self.assertFalse(any(value.startswith("single-") for value in ids))

    def test_no_causality_or_semantic_threshold_is_frozen(self):
        rendered = str(self.manifest)
        self.assertNotIn("pass_threshold", rendered)
        self.assertNotIn("causality_threshold", rendered)


if __name__ == "__main__":
    unittest.main()

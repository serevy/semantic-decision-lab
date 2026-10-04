import unittest

from phase1b.probes import load_manifest, validate_manifest


class Phase1BFreezeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_manifest()
        cls.cases = validate_manifest(cls.manifest)

    def test_exact_call_count_is_frozen(self):
        self.assertEqual(self.manifest["expected_provider_calls"], 42)
        self.assertEqual(len(self.cases), 42)

    def test_three_replication_fixtures_are_frozen(self):
        self.assertEqual(
            [entry["id"] for entry in self.manifest["fixtures"]],
            ["payments-partial", "storefront-hard", "support-info"],
        )

    def test_each_fixture_has_exactly_fourteen_wire_distinct_variants(self):
        by_fixture = {}
        for case in self.cases:
            by_fixture.setdefault(case["fixture_id"], []).append(case)
        for fixture_id, cases in by_fixture.items():
            with self.subTest(fixture=fixture_id):
                self.assertEqual(len(cases), 14)
                self.assertEqual(
                    len({case["wire_request_sha256"] for case in cases}),
                    14,
                )
                self.assertEqual(
                    len({case["canonical_request_sha256"] for case in cases}),
                    4,
                )

    def test_no_semantic_threshold_is_frozen(self):
        rendered = str(self.manifest)
        self.assertNotIn("pass_threshold", rendered)
        self.assertNotIn("fail_threshold", rendered)


if __name__ == "__main__":
    unittest.main()

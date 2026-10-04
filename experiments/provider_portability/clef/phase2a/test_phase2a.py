import unittest

from phase2a.probes import load_manifest, validate_manifest
from phase2a.run_local import dry_run


class Phase2AFreezeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_manifest()
        cls.plan = validate_manifest(cls.manifest)
        cls.cases = cls.plan["cases"]

    def test_full_hf_revision_is_frozen(self):
        revision = self.manifest["model"]["hf_revision"]
        self.assertEqual(
            revision,
            "17f0b0ad64efb65d273590632833508766b2aae6",
        )
        self.assertEqual(len(revision), 40)
        self.assertTrue(revision.startswith("17f0b0a"))

    def test_phase1c_schedule_is_inherited_exactly(self):
        phase1c = self.plan["phase1c_manifest"]
        self.assertEqual(len(self.cases), 54)
        self.assertEqual(
            [
                (
                    case["round"],
                    case["fixture_id"],
                    case["variant"]["id"],
                    case["repeat_index"],
                )
                for case in self.cases
            ],
            [
                (
                    item["round"],
                    item["fixture_id"],
                    item["variant_id"],
                    item["repeat_index"],
                )
                for item in phase1c["schedule"]
            ],
        )

    def test_execution_count_and_canary_are_frozen(self):
        execution = self.manifest["execution"]
        self.assertEqual(execution["canary_calls"], 1)
        self.assertEqual(execution["phase1c_schedule_calls"], 54)
        self.assertEqual(execution["total_model_calls"], 55)
        self.assertIsNone(execution["semantic_canary_threshold"])

    def test_runtime_boundary_is_explicit(self):
        runtime = self.manifest["runtime_contract"]
        self.assertEqual(runtime["device"], "cuda")
        self.assertEqual(runtime["requested_dtype"], "bfloat16")
        self.assertEqual(runtime["torch_version_prefix"], "2.11")
        self.assertEqual(runtime["transformers_version"], "5.10.2")
        self.assertTrue(runtime["no_quantization"])
        self.assertTrue(runtime["no_cpu_offload"])

    def test_hosted_reference_is_repository_pinned(self):
        pins = self.manifest["frozen_pins"]
        self.assertEqual(
            pins["hosted_phase1c_bundle_blob_sha"],
            "cbcd772fe00664aeb8b51747707286bd2776033d",
        )
        self.assertEqual(
            pins["hosted_phase1c_analysis_blob_sha"],
            "8e5c3864f73e06961e320e4f12ce92aa3d19ffc7",
        )

    def test_dry_run_materializes_without_model_output(self):
        report = dry_run(self.manifest, self.plan)
        self.assertEqual(report["mode"], "dry-run-no-model-output")
        self.assertEqual(report["condition_count"], 18)
        self.assertEqual(report["scheduled_calls"], 54)
        self.assertEqual(report["total_model_calls_if_executed"], 55)
        self.assertEqual(len(report["schedule"]), 54)

    def test_no_semantic_or_causality_threshold_is_frozen(self):
        rendered = str(self.manifest)
        self.assertNotIn("pass_threshold", rendered)
        self.assertNotIn("causality_threshold", rendered)
        self.assertNotIn("acceptable_delta", rendered)


if __name__ == "__main__":
    unittest.main()

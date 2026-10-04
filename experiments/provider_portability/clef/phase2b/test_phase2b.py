import unittest

from phase2b.probes import load_manifest, validate_manifest


class Phase2BFreezeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_manifest()
        cls.plan = validate_manifest(cls.manifest)

    def test_revision_and_runtime_match_phase2a_family(self):
        self.assertEqual(
            self.manifest["model"]["hf_revision"],
            "17f0b0ad64efb65d273590632833508766b2aae6",
        )
        runtime = self.manifest["runtime_contract"]
        self.assertEqual(runtime["device"], "cuda")
        self.assertEqual(runtime["requested_dtype"], "bfloat16")
        self.assertEqual(runtime["torch_version_prefix"], "2.11")
        self.assertEqual(runtime["transformers_version"], "5.10.2")
        self.assertTrue(runtime["no_quantization"])
        self.assertTrue(runtime["no_cpu_offload"])

    def test_condition_family_is_exactly_3_by_6(self):
        self.assertEqual(len(self.plan["fixtures"]), 3)
        self.assertEqual(len(self.plan["variants"]), 6)
        self.assertEqual(self.plan["variants"][0], "packed-canonical")
        self.assertEqual(len(self.plan["conditions"]), 18)
        self.assertEqual(
            {
                (case["fixture_id"], case["variant"]["id"])
                for case in self.plan["conditions"]
            },
            {
                (fixture_id, variant_id)
                for fixture_id in self.plan["fixtures"]
                for variant_id in self.plan["variants"]
            },
        )

    def test_execution_budget_is_frozen(self):
        execution = self.manifest["execution"]
        self.assertEqual(execution["canary_calls"], 1)
        self.assertEqual(execution["traced_actual_conditions"], 18)
        self.assertEqual(execution["actual_backbone_forwards"], 18)
        self.assertEqual(execution["total_backbone_forwards_including_canary"], 19)
        self.assertEqual(execution["head_only_counterfactuals"], 15)
        self.assertTrue(execution["one_observation_per_condition"])

    def test_head_only_intervention_is_narrow(self):
        control = self.manifest["head_only_counterfactual"]
        self.assertEqual(control["backbone_hidden_states"], "canonical fixed")
        self.assertEqual(control["input_ids"], "canonical fixed")
        self.assertEqual(control["attention_mask"], "canonical fixed")
        self.assertIn("EncodedRecord.questions", control["only_intervention"])
        self.assertIn("question_id", control["alignment"])

    def test_no_post_output_threshold_is_frozen(self):
        execution = self.manifest["execution"]
        self.assertIsNone(execution["semantic_threshold"])
        self.assertIsNone(execution["stage_delta_threshold"])


if __name__ == "__main__":
    unittest.main()

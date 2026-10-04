import unittest

from phase2b.probes import load_manifest, validate_manifest


class Phase2BFreezeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_manifest()
        cls.plan = validate_manifest(cls.manifest)

    def test_v0_2_retry_freeze_is_default(self):
        self.assertEqual(self.manifest["protocol_version"], "0.2")
        self.assertEqual(self.plan["protocol_version"], "0.2")
        self.assertTrue(
            self.manifest["frozen_before_phase2b_v0_2_retry_output"]
        )
        self.assertEqual(
            self.manifest["execution"]["run_identity"],
            "clef-phase2b-local-v0.2",
        )

    def test_v0_1_failure_is_preserved_before_retry(self):
        attempts = self.manifest["prior_failed_attempts"]
        self.assertEqual(len(attempts), 1)
        prior = attempts[0]
        self.assertEqual(prior["run_identity"], "clef-phase2b-local-v0.1")
        self.assertEqual(
            prior["freeze_commit"],
            "08c16640320805aeaad7942079dfbe87ea8f8d7a",
        )
        self.assertEqual(prior["first_actual_stage"], "trace-error")
        self.assertEqual(
            prior["failure_kind"],
            "runner-inference-tensor-trace-context",
        )
        self.assertTrue(prior["first_actual_response_preserved"])
        self.assertEqual(prior["successful_trace_outputs"], 0)
        self.assertEqual(prior["head_only_counterfactuals_completed"], 0)

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

    def test_trace_bridge_preserves_released_inference_path(self):
        trace_fix = self.manifest["trace_runtime_fix"]
        self.assertEqual(
            trace_fix["actual_inference_context"],
            "torch.inference_mode",
        )
        self.assertIn("clone", trace_fix["trace_bridge"].lower())
        self.assertEqual(trace_fix["trace_context"], "torch.no_grad")

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

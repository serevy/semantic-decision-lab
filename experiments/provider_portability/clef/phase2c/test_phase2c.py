import unittest

from phase2c.probes import load_manifest, validate_manifest
from phase2c.run_local import dry_run


class Phase2CFreezeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = load_manifest()
        cls.plan = validate_manifest(cls.manifest)

    def test_freeze_precedes_any_phase2c_output(self):
        self.assertEqual(self.manifest["protocol_version"], "0.1")
        self.assertTrue(self.manifest["frozen_before_phase2c_output"])
        self.assertEqual(self.manifest["phase2c_model_outputs_observed_before_freeze"], 0)

    def test_phase2b_v0_2_is_the_pinned_parent(self):
        self.assertEqual(self.plan["phase2b_plan"]["protocol_version"], "0.2")
        self.assertEqual(
            self.manifest["source_commits"]["phase2b_evidence_merge"],
            "04b1fa1997071c447953023f92f5b6b247365eec",
        )

    def test_revision_and_runtime_remain_fixed(self):
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

    def test_inherited_condition_family_is_exact(self):
        self.assertEqual(len(self.plan["fixtures"]), 3)
        self.assertEqual(len(self.plan["variants"]), 6)
        self.assertEqual(self.plan["variants"][0], "packed-canonical")
        self.assertEqual(len(self.plan["conditions"]), 18)
        self.assertEqual(len(self.plan["canonical_conditions"]), 3)

    def test_intervention_budget_is_frozen(self):
        execution = self.manifest["execution"]
        self.assertEqual(execution["standard_conditions"], 18)
        self.assertEqual(execution["zero_position_conditions"], 18)
        self.assertEqual(execution["suffix_shift_conditions"], 6)
        self.assertEqual(execution["experimental_backbone_forwards"], 42)
        self.assertEqual(execution["suffix_shift_offsets"], [32, 128])
        self.assertTrue(execution["one_observation_per_condition"])
        self.assertTrue(execution["reuse_single_loaded_model"])
        self.assertTrue(execution["no_retries_inside_run"])

    def test_controls_are_narrow(self):
        controls = self.manifest["controls"]
        self.assertEqual(controls["zero_position"]["position_ids"], "all zero")
        suffix = controls["canonical_suffix_shift"]
        self.assertEqual(suffix["source_variant"], "packed-canonical")
        self.assertEqual(suffix["offsets"], [32, 128])
        self.assertEqual(suffix["input_ids"], "canonical fixed")
        self.assertEqual(suffix["attention_mask"], "canonical fixed")
        self.assertEqual(suffix["causal_token_order"], "canonical fixed")

    def test_no_post_output_thresholds_exist(self):
        execution = self.manifest["execution"]
        for key in (
            "semantic_threshold",
            "numerical_noise_threshold",
            "sufficiency_threshold",
            "necessity_threshold",
            "causality_threshold",
        ):
            self.assertIsNone(execution[key])

    def test_dry_run_freezes_exact_schedule(self):
        result = dry_run(self.manifest, self.plan)
        self.assertEqual(result["standard_conditions"], 18)
        self.assertEqual(result["zero_position_conditions"], 18)
        self.assertEqual(result["suffix_shift_conditions"], 6)
        self.assertEqual(result["experimental_backbone_forwards"], 42)
        modes = [row["mode"] for row in result["schedule"]]
        self.assertEqual(modes.count("standard"), 18)
        self.assertEqual(modes.count("zero-position"), 18)
        self.assertEqual(modes.count("suffix-shift"), 6)


if __name__ == "__main__":
    unittest.main()

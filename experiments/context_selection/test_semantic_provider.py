import unittest

from semantic_provider import (
    CandidateDecision,
    SemanticDecisionResult,
    select_top_k,
    validate_result,
)


class SemanticProviderContractTest(unittest.TestCase):
    def test_candidate_probabilities_must_sum_to_one(self):
        with self.assertRaises(ValueError):
            CandidateDecision("PDDR-0001", 0.8, 0.3, 0.1)

    def test_top_k_prioritizes_required_probability(self):
        result = SemanticDecisionResult(
            provider="fixture",
            decisions=[
                CandidateDecision("PDDR-0001", 0.10, 0.85, 0.05),
                CandidateDecision("PDDR-0002", 0.60, 0.20, 0.20),
                CandidateDecision("PDDR-0003", 0.40, 0.50, 0.10),
            ],
        )
        self.assertEqual(select_top_k(result, top_k=2), ["PDDR-0002", "PDDR-0003"])

    def test_useful_probability_is_secondary_tie_break(self):
        result = SemanticDecisionResult(
            provider="fixture",
            decisions=[
                CandidateDecision("PDDR-0001", 0.40, 0.20, 0.40),
                CandidateDecision("PDDR-0002", 0.40, 0.50, 0.10),
            ],
        )
        self.assertEqual(select_top_k(result, top_k=1), ["PDDR-0002"])

    def test_abstention_selects_nothing(self):
        result = SemanticDecisionResult(
            provider="fixture",
            decisions=[CandidateDecision("PDDR-0001", 0.9, 0.05, 0.05)],
            abstained=True,
        )
        self.assertEqual(select_top_k(result, top_k=2), [])

    def test_validate_requires_exact_candidate_set(self):
        result = SemanticDecisionResult(
            provider="fixture",
            decisions=[CandidateDecision("PDDR-0001", 0.9, 0.05, 0.05)],
        )
        with self.assertRaises(ValueError):
            validate_result(result, ["PDDR-0001", "PDDR-0002"])


if __name__ == "__main__":
    unittest.main()

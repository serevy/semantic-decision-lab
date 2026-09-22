import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import run_topk_frontier_v0_2 as frontier


class TopKFrontierV02Tests(unittest.TestCase):
    def test_embedding_required_rank_evidence_matches_gold(self):
        cases = json.loads(frontier.CASES.read_text())
        ranks = json.loads(frontier.EMBEDDING_REQUIRED_RANKS.read_text())

        self.assertEqual(set(ranks["cases"]), {case["case_id"] for case in cases})
        for case in cases:
            row = ranks["cases"][case["case_id"]]
            self.assertEqual(row["required"], case["gold"]["required"][0])
            self.assertGreaterEqual(row["rank"], 1)
            self.assertLessEqual(row["rank"], len(case["corpus"]))

    def test_frozen_top2_is_reproduced(self):
        cases = json.loads(frontier.CASES.read_text())
        registry = json.loads(frontier.REGISTRY.read_text())
        baseline = json.loads(frontier.BASELINE_EVIDENCE.read_text())
        ranks = json.loads(frontier.EMBEDDING_REQUIRED_RANKS.read_text())
        snapshots = frontier.load_snapshot_docs(registry)

        keyword = frontier.summarize_keyword(cases, snapshots, 2)
        embedding = frontier.summarize_embedding(cases, ranks, 2)

        self.assertEqual(keyword["required_hits"], 11)
        self.assertEqual(
            frontier.normalized_selection_sets(keyword["selections"]),
            frontier.normalized_selection_sets(baseline["arms"]["keyword_top2"]["selections"]),
        )
        self.assertEqual(embedding["required_hits"], 10)
        self.assertEqual(sorted(embedding["required_misses"]), ["ctx-002", "ctx-003"])


if __name__ == "__main__":
    unittest.main()

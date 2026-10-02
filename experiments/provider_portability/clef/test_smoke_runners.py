import json
import tempfile
import unittest
from pathlib import Path

from evidence_io import reserve_evidence, update_evidence
from run_local_clef_flash_smoke import validate_approved_revision


class EvidenceIoTest(unittest.TestCase):
    def test_reservation_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            reserve_evidence(path, {"stage": "first"})
            with self.assertRaises(FileExistsError):
                reserve_evidence(path, {"stage": "second"})

    def test_update_replaces_complete_json_after_reservation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            reserve_evidence(path, {"stage": "reserved"})
            update_evidence(path, {"stage": "raw-response", "status": 200})
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"stage": "raw-response", "status": 200},
            )


class ClefRevisionGateTest(unittest.TestCase):
    def test_full_approved_revision_is_accepted(self):
        validate_approved_revision("17f0b0a" + "0" * 33)

    def test_short_revision_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_approved_revision("17f0b0a")

    def test_different_revision_prefix_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_approved_revision("abcdef0" + "0" * 33)


if __name__ == "__main__":
    unittest.main()

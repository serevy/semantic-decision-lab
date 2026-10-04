import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from evidence_io import reserve_evidence, update_evidence
from run_local_clef_flash_smoke import (
    FROZEN_MAX_LENGTH,
    inspect_state_encoding,
    validate_approved_revision,
)
from run_workers_ai_smoke import canonical_json, raw_body_evidence, wire_json


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
            predictable_old_temp = path.with_name(f".{path.name}.tmp")
            predictable_old_temp.write_text("must survive", encoding="utf-8")
            update_evidence(path, {"stage": "raw-response", "status": 200})
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"stage": "raw-response", "status": 200},
            )
            self.assertEqual(
                predictable_old_temp.read_text(encoding="utf-8"),
                "must survive",
            )


class ClefFrozenConditionTest(unittest.TestCase):
    def test_first_smoke_max_length_is_frozen(self):
        self.assertEqual(FROZEN_MAX_LENGTH, 16384)


class ClefRevisionGateTest(unittest.TestCase):
    def test_full_approved_revision_is_accepted(self):
        validate_approved_revision("17f0b0a" + "0" * 33)

    def test_short_revision_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_approved_revision("17f0b0a")

    def test_different_revision_prefix_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_approved_revision("abcdef0" + "0" * 33)


class FakeTokenizer:
    def __call__(self, text, add_special_tokens=False):
        del add_special_tokens
        return SimpleNamespace(input_ids=list(range(len(text))))


class FakeProcessor:
    tokenizer = FakeTokenizer()


class FakeJointSchemaModule:
    @staticmethod
    def render(value):
        return str(value)

    @staticmethod
    def encode_record(tokenizer, record, max_length, processor):
        del processor
        fixed = 10
        state = tokenizer(
            FakeJointSchemaModule.render(record["state"]),
            add_special_tokens=False,
        ).input_ids
        retained = state[: max_length - fixed]
        return SimpleNamespace(input_ids=tuple([0] * fixed + retained))


class EncodingPreflightTest(unittest.TestCase):
    def test_complete_state_is_reported_without_truncation(self):
        diagnostics = inspect_state_encoding(
            FakeJointSchemaModule,
            FakeProcessor(),
            {"state": "abc", "questions": {}},
            max_length=20,
        )
        self.assertFalse(diagnostics["state_truncated"])
        self.assertEqual(diagnostics["state_tokens_original"], 3)
        self.assertEqual(diagnostics["state_tokens_retained"], 3)

    def test_truncated_state_is_detected(self):
        diagnostics = inspect_state_encoding(
            FakeJointSchemaModule,
            FakeProcessor(),
            {"state": "abcdefghijklmno", "questions": {}},
            max_length=20,
        )
        self.assertTrue(diagnostics["state_truncated"])
        self.assertEqual(diagnostics["state_tokens_original"], 15)
        self.assertEqual(diagnostics["state_tokens_retained"], 10)


class HostedWireSerializationTest(unittest.TestCase):
    def test_canonical_hash_ignores_mapping_order_but_wire_bytes_preserve_it(self):
        first = {"questions": {"a": {"type": "noul"}, "b": {"type": "noul"}}}
        second = {"questions": {"b": {"type": "noul"}, "a": {"type": "noul"}}}
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertNotEqual(wire_json(first), wire_json(second))
        self.assertLess(wire_json(first).find(b'"a"'), wire_json(first).find(b'"b"'))
        self.assertLess(wire_json(second).find(b'"b"'), wire_json(second).find(b'"a"'))


class HostedRawEvidenceTest(unittest.TestCase):
    def test_raw_bytes_are_preserved_exactly(self):
        raw = b'{"x":"\xff"}'
        fields = raw_body_evidence(raw)
        self.assertEqual(fields["raw_response_base64"], "eyJ4Ijoi/yJ9")
        self.assertEqual(
            fields["raw_response_sha256"],
            "36781faac995a68b69aab7d540747e0c70efed427e66a608cdf64fc4feaaff12",
        )


if __name__ == "__main__":
    unittest.main()

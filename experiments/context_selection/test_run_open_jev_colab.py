import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run_open_jev_colab as target


class ColabRunnerTest(unittest.TestCase):
    def test_constants_match_frozen_provider_revision(self):
        self.assertEqual(
            target.UPSTREAM_REVISION,
            "78d3b3a171f24d8d9a8dea18e027f9d3373fda45",
        )

    def test_wait_for_server_times_out_with_log_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "server.log"
            log.write_text("model failed\n")
            with mock.patch.object(
                target.urllib.request,
                "urlopen",
                side_effect=OSError("offline"),
            ), mock.patch.object(target.time, "sleep", return_value=None), mock.patch.object(
                target.time,
                "time",
                side_effect=[0, 0, 2],
            ):
                with self.assertRaises(SystemExit) as raised:
                    target.wait_for_server("http://127.0.0.1:8000/docs", log, timeout_s=1)
            self.assertIn("model failed", str(raised.exception))


if __name__ == "__main__":
    unittest.main()

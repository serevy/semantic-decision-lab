import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run_zefan_openjev_2b_colab as runner


class FakeExitedServer:
    def poll(self):
        return 1


class ZefanColabRunnerTest(unittest.TestCase):
    def test_removes_incompatible_optional_torchao(self):
        with (
            mock.patch.object(
                runner.importlib.metadata,
                "version",
                return_value="0.10.0",
            ),
            mock.patch.object(runner, "run") as run,
        ):
            runner.remove_incompatible_torchao()

        run.assert_called_once_with(
            [
                runner.sys.executable,
                "-m",
                "pip",
                "uninstall",
                "-y",
                "torchao",
            ]
        )

    def test_keeps_newer_torchao(self):
        with (
            mock.patch.object(
                runner.importlib.metadata,
                "version",
                return_value="0.17.0",
            ),
            mock.patch.object(runner, "run") as run,
        ):
            runner.remove_incompatible_torchao()

        run.assert_not_called()

    def test_server_exit_fails_fast_and_includes_log_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "server.log"
            log.write_text("adapter load failed\n")

            with self.assertRaises(SystemExit) as raised:
                runner.wait_for_server(
                    "http://127.0.0.1:8791/health",
                    log,
                    FakeExitedServer(),
                )

        message = str(raised.exception)
        self.assertIn("exited before becoming ready", message)
        self.assertIn("adapter load failed", message)


if __name__ == "__main__":
    unittest.main()

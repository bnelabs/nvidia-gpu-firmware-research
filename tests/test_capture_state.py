"""All collector tests use injected CPU-only responses. Never run nvidia-smi."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import runpy
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import capture_state as capture

UUID = "GPU-00000000-0000-0000-0000-000000000001"


def response(uuid=UUID, rc=0):
    values = [uuid, "Synthetic fixture only", "0000:01:00.0", "test", "test", "P8",
              "31", "N/A", "370.00", "210", "405", "0", "0", "0", "1", "16"]
    return subprocess.CompletedProcess([], rc, ", ".join(values) + "\n", "")


class CollectorTests(unittest.TestCase):
    def test_cooldown_and_concurrent_attempts_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "monitor.lock"
            with capture.monitoring_slot(path, clock=lambda: 100):
                with self.assertRaises(ValueError):
                    with capture.monitoring_slot(path, clock=lambda: 100):
                        self.fail("concurrent collection allowed")
            with self.assertRaises(ValueError):
                with capture.monitoring_slot(path, clock=lambda: 105):
                    self.fail("rapid collection allowed")
            with capture.monitoring_slot(path, clock=lambda: 110):
                pass
            path.write_text("malformed")
            with self.assertRaises(ValueError):
                with capture.monitoring_slot(path, clock=lambda: 120):
                    self.fail("bad state bypassed")

    def test_legacy_dry_run_does_not_load_or_sample_nvml(self):
        wrapper = Path(__file__).resolve().parents[1] / "10-monitor/collector/collector.py"
        with patch.object(sys, "argv", [str(wrapper), "--dry-run"]), patch.object(capture, "collect", side_effect=AssertionError("hardware forbidden")), contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as result:
            runpy.run_path(str(wrapper), run_name="__main__")
        self.assertEqual(result.exception.code, 0)
        with patch.object(sys, "argv", [str(wrapper), "--dry-run", "--live"]), self.assertRaises(SystemExit) as result:
            runpy.run_path(str(wrapper), run_name="__main__")
        self.assertIn("cannot be combined", str(result.exception))

    def run_fixture(self, runner):
        return capture.collect(UUID, runner=runner, euid=lambda: 1000,
                               executable="/usr/bin/nvidia-smi")

    def test_default_plan_cannot_collect(self):
        out = io.StringIO()
        with patch.object(capture, "collect", side_effect=AssertionError("hardware forbidden")), contextlib.redirect_stdout(out):
            self.assertEqual(capture.main([]), 0)
        self.assertFalse(json.loads(out.getvalue())["hardware_access"])

    def test_missing_identity_and_arbitrary_flags_rejected_before_collection(self):
        with patch.object(capture, "collect", side_effect=AssertionError("hardware forbidden")):
            for args in (["--live"], ["--fields", "foo"], ["--live", "--reset"]):
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    capture.main(args)
        for value in ("0", UUID + ";reset", "/dev/nvidia0", "--gpu-reset"):
            with self.assertRaises(ValueError):
                capture.command(value)

    def test_root_refused_before_any_query(self):
        runner = Mock(side_effect=AssertionError("hardware forbidden"))
        with self.assertRaisesRegex(ValueError, "refuses root"):
            capture.collect(UUID, runner=runner, euid=lambda: 0)
        runner.assert_not_called()

    def test_one_fixed_query_preserves_unsupported_values(self):
        runner = Mock(return_value=response())
        record = self.run_fixture(runner)
        self.assertEqual(record["status"], "observed")
        self.assertEqual(record["values"]["power.draw"], "N/A")
        self.assertEqual(record["values"]["pstate"], "P8")
        runner.assert_called_once()
        args, opts = runner.call_args
        self.assertEqual(args[0], capture.command(UUID))
        self.assertEqual(set(opts["env"]), {"PATH", "LANG", "LC_ALL"})
        self.assertEqual(opts["timeout"], 8)
        self.assertFalse(opts["check"])

    def test_timeout_stops_without_retry(self):
        runner = Mock(side_effect=subprocess.TimeoutExpired("fixture", 8))
        record = self.run_fixture(runner)
        self.assertEqual(record["status"], "error")
        self.assertNotIn("values", record)
        runner.assert_called_once()

    def test_failures_and_identity_mismatch_are_not_measurements(self):
        cases = [response(rc=3), response(UUID[:-1] + "2"),
                 subprocess.CompletedProcess([], 0, "malformed\n", "")]
        for result in cases:
            runner = Mock(return_value=result)
            record = self.run_fixture(runner)
            self.assertEqual(record["status"], "error")
            self.assertNotIn("values", record)
            runner.assert_called_once()


if __name__ == "__main__":
    unittest.main()

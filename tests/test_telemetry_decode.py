#!/usr/bin/env python3
"""Bounded-milestone test: fixture decodes to NVML-consistent values, offline."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from decode_telemetry import decode_pstate, decode_gsp_features  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[1] / "tests/fixtures/telemetry-615.71.09-idle.json"


class TestTelemetryDecode(unittest.TestCase):
    def test_pstate_onehot_enum(self):
        self.assertEqual(decode_pstate(1), "P0")
        self.assertEqual(decode_pstate(4), "P2")
        self.assertEqual(decode_pstate(256), "P8")
        self.assertEqual(decode_pstate(0x8000), "P15")

    def test_pstate_nononehot_stays_raw(self):
        self.assertEqual(decode_pstate(3), "raw(0x3)")
        self.assertEqual(decode_pstate(0), "raw(0x0)")

    def test_gsp_features(self):
        self.assertEqual(decode_gsp_features(1), ["UVM_ENABLED"])
        self.assertEqual(decode_gsp_features(3), ["UVM_ENABLED"])
        self.assertEqual(decode_gsp_features(0), [])

    def test_fixture_end_to_end(self):
        fixture = json.loads(FIXTURE.read_text())
        from decode_telemetry import decode
        out = decode(fixture)
        self.assertEqual(out["decoded"]["pstate"], "P8")
        self.assertEqual(out["decoded"]["gpc_clk_mhz"], 210.0)
        self.assertTrue(out["decoded"]["gsp_rm_default"])
        self.assertEqual(out["device"]["vbios"], "94.02.42.00.F4")


if __name__ == "__main__":
    unittest.main(verbosity=2)

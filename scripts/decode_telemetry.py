#!/usr/bin/env python3
"""decode_telemetry.py - source-pinned GA102 telemetry decoder (bounded milestone).

Decodes fixture JSON (tests/fixtures/telemetry-*.json) into human values with the
semantic contract per field. Unknown fields stay raw (RESEARCH-DIRECTION.md).
"""
import json
import sys
from offline_io import read_artifact

PSTATE_ONEHOT = {1 << n: f"P{n}" for n in range(16)}   # ctrl2080perf.h @ca2d03e
GSP_FEATURE_BITS = {0: "UVM_ENABLED"}                  # ctrl2080gsp.h 0:0


def decode_pstate(raw: int) -> str:
    return PSTATE_ONEHOT.get(raw, f"raw(0x{raw:x})")


def decode_gsp_features(mask: int) -> list:
    # Known bits get names; unknown bits are PRESERVED as raw entries
    # (RESEARCH-DIRECTION.md: unknown fields stay raw).
    known_bits = set()
    out = []
    for bit, name in GSP_FEATURE_BITS.items():
        if mask & (1 << bit):
            out.append(name)
            known_bits.add(bit)
    for bit in range(mask.bit_length()):
        if mask & (1 << bit) and bit not in known_bits:
            out.append(f"unknown_bit{bit}")
    return out


def decode(fixture: dict) -> dict:
    p = fixture["probes"]
    samples = p["clk_pmumon_domains_get_samples"]["raw"]
    count = samples["numSamples"]
    clock = samples["last_activeGpcClkFreqKHz"]
    if not isinstance(count, int) or isinstance(count, bool) or not 0 <= count <= 250:
        raise ValueError("PMUMON sample count outside the versioned capacity")
    if not isinstance(clock, int) or isinstance(clock, bool) or not 0 <= clock <= 0xffffffff:
        raise ValueError("clock sample must be a u32")
    clock_status = "no-samples" if count == 0 else "invalid-sentinel" if clock == 0xffffffff else "source-decoded"
    return {
        "device": fixture["device"],
        "driver": fixture["driver"],
        "decoded": {
            "pstate": decode_pstate(p["perf_get_current_pstate"]["raw"]["currPstate"]),
            "gpc_clk_mhz": clock / 1000.0 if clock_status == "source-decoded" else None,
            "gpc_clk_status": clock_status,
            "gsp_features": decode_gsp_features(p["gsp_get_features"]["raw"]["gspFeatures"]),
            "gsp_rm_default": bool(p["gsp_get_features"]["raw"]["bDefaultGspRmGpu"]),
        },
        "contract": {
            "pstate": "one-hot enum, ctrl2080perf.h @ca2d03e",
            "gpc_clk": "KHz u32 -> MHz, ctrl2080clk.h",
            "gsp_features": "bitmask, ctrl2080gsp.h 0:0 UVM_ENABLED",
        },
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    print(json.dumps(decode(json.loads(read_artifact(sys.argv[1]))), indent=1))

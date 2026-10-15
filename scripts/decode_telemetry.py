#!/usr/bin/env python3
"""decode_telemetry.py - source-pinned GA102 telemetry decoder (bounded milestone).

Decodes fixture JSON (tests/fixtures/telemetry-*.json) into human values with the
semantic contract per field. Unknown fields stay raw (RESEARCH-DIRECTION.md).
"""
import json
import sys

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
    return {
        "device": fixture["device"],
        "driver": fixture["driver"],
        "decoded": {
            "pstate": decode_pstate(p["perf_get_current_pstate"]["raw"]["currPstate"]),
            "gpc_clk_mhz": p["clk_pmumon_domains_get_samples"]["raw"]["last_activeGpcClkFreqKHz"] / 1000.0,
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
    print(json.dumps(decode(json.load(open(sys.argv[1]))), indent=1))

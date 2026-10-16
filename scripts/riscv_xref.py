#!/usr/bin/env python3
"""riscv_xref.py — find RV64 lui/addi references to a data address in a flat binary.

RISC-V references constants via paired instructions:
    lui  rd, %hi(addr)   -> 0x37 | rd<<7 | (hi & 0xFFFFF) << 12
    addi rd, rd, %lo(addr)
This resolver enumerates lui encodings for the target page across all rd values,
verifies with the matching addi (immediate = lo, rd equal), and reports file offsets.

Usage: riscv_xref.py <file> <vaddr-hex> [--text-only]
Assumes the whole file is scanned; the caller constrains to code regions if needed.
"""
import struct
import sys


def lui_addi_addrs(blob: bytes, target: int):
    hi20 = (target + 0x800) >> 12
    lo12 = target - (hi20 << 12)
    lo12 &= 0xFFF
    if lo12 >= 0x800:
        lo12 -= 0x1000
    hits = []
    for off in range(0, len(blob) - 8, 4):
        w1, = struct.unpack_from("<I", blob, off)
        if (w1 & 0x7F) != 0x37:  # LUI opcode
            continue
        imm20 = (w1 >> 12) & 0xFFFFF
        if imm20 != hi20:
            continue
        rd = (w1 >> 7) & 0x1F
        if rd == 0:
            continue
        # scan the next few slots for the paired ADDI with same rd
        for k in (4, 8):
            if off + k + 4 > len(blob):
                continue
            w2, = struct.unpack_from("<I", blob, off + k)
            if (w2 & 0x7F) != 0x13:
                continue
            rd2 = (w2 >> 7) & 0x1F
            f3 = (w2 >> 12) & 0x7
            if rd2 != rd or f3 != 0:
                continue
            imm = (w2 >> 20) & 0xFFF
            if imm >= 0x800:
                imm -= 0x1000
            resolved = (hi20 << 12) + imm
            if resolved == target:
                hits.append((off, rd, k // 4))
    return hits


def main():
    path, va_hex = sys.argv[1], sys.argv[2]
    target = int(va_hex, 16)
    blob = open(path, "rb").read()
    hits = lui_addi_addrs(blob, target)
    print(f"{path}: target 0x{target:x} -> {len(hits)} lui/addi reference(s)")
    for off, rd, gap in hits:
        print(f"  file 0x{off:x} (rd=x{rd}, gap={gap})")


if __name__ == "__main__":
    main()

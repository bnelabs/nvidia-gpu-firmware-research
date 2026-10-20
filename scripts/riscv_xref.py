#!/usr/bin/env python3
"""riscv_xref.py — find RV64 lui/addi references to a data address in a flat binary.

RISC-V references constants via paired instructions:
    lui  rd, %hi(addr)   -> 0x37 | rd<<7 | (hi & 0xFFFFF) << 12
    addi rd, rd, %lo(addr)
This resolver enumerates lui encodings for the target page across all rd values,
verifies with the matching addi (immediate = lo, rd equal), and reports file offsets.

Usage: riscv_xref.py <file> <vaddr-hex>
Finds adjacent, uncompressed LUI/ADDI pairs at 2-byte boundaries (RVC alignment).
These are instruction-pattern candidates, not proven executable-code references.
AUIPC, separated instructions and arbitrary dataflow are not resolved here.
"""
import struct
import sys
from offline_io import read_artifact


def lui_addi_addrs(blob: bytes, target: int):
    target &= (1 << 64) - 1
    hits = []
    for off in range(0, len(blob) - 7, 2):
        w1, = struct.unpack_from("<I", blob, off)
        if (w1 & 0x7F) != 0x37:  # LUI opcode
            continue
        imm20 = (w1 >> 12) & 0xFFFFF
        rd = (w1 >> 7) & 0x1F
        if rd == 0:
            continue
        # Only an adjacent ADDI with matching source and destination is resolved.
        for k in (4,):
            if off + k + 4 > len(blob):
                continue
            w2, = struct.unpack_from("<I", blob, off + k)
            if (w2 & 0x7F) != 0x13:
                continue
            rd2 = (w2 >> 7) & 0x1F
            f3 = (w2 >> 12) & 0x7
            rs1 = (w2 >> 15) & 0x1F
            if rd2 != rd or rs1 != rd or f3 != 0:
                continue
            imm = (w2 >> 20) & 0xFFF
            if imm >= 0x800:
                imm -= 0x1000
            upper = imm20 << 12
            if upper & 0x80000000:
                upper -= 1 << 32  # RV64 LUI sign-extends its 32-bit result
            resolved = (upper + imm) & ((1 << 64) - 1)
            if resolved == target:
                hits.append((off, rd, k // 4))
    return hits


def main():
    path, va_hex = sys.argv[1], sys.argv[2]
    target = int(va_hex, 16)
    blob = read_artifact(path)
    hits = lui_addi_addrs(blob, target)
    print(f"{path}: target 0x{target:x} -> {len(hits)} lui/addi reference(s)")
    for off, rd, gap in hits:
        print(f"  file 0x{off:x} (rd=x{rd}, gap={gap})")


if __name__ == "__main__":
    main()

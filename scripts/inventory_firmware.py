#!/usr/bin/env python3
"""inventory_firmware.py — packet C: offline, reproducible firmware inventory.

For each artifact: SHA-256, size, section table (outer ELF containers), embedded
ELF candidates (bounds-checked headers), and loader-source provenance parsed from
symtab `_binary_*_firmware_bin_start` marker symbols (Perforce build paths).

Validation per candidate: ELF magic, class/endian/machine, program headers within
file bounds, entry-point mapping. Everything reported as status strings, never
inferred. No network, no GPU.

Usage: inventory_firmware.py <file...> > inventory.json
"""
import hashlib
import json
import struct
import sys
from offline_io import read_artifact

ELF_MAGIC = b"\x7fELF"
MACHINES = {0xF3: "RISC-V", 0x3E: "x86-64", 0xB7: "AArch64"}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_sections(data: bytes):
    """ELF section table for 64-bit LE ELF. Returns list (with error markers)."""
    if len(data) < 64 or data[:4] != ELF_MAGIC or data[4] != 2 or data[5] != 1:
        return []
    try:
        e_shoff, = struct.unpack_from("<Q", data, 0x28)
        e_shentsize, e_shnum = struct.unpack_from("<HH", data, 0x3A)
        if e_shnum and (e_shentsize < 64 or e_shoff + e_shentsize * e_shnum > len(data)):
            return [{"error": "section table outside artifact or invalid stride"}]
        secs = []
        for i in range(e_shnum):
            off = e_shoff + i * e_shentsize
            if off + 64 > len(data):
                secs.append({"index": i, "error": "section header out of bounds"})
                break
            name_off, s_type, flags, addr, offset, size = struct.unpack_from(
                "<IIQQQQ", data, off)
            in_bounds = s_type == 8 or offset + size <= len(data)  # SHT_NOBITS has no file payload
            secs.append({
                "index": i, "type": s_type, "offset": offset, "size": size,
                "in_bounds": in_bounds,
                "preview": data[offset:offset + min(size, 16)].hex() if in_bounds and s_type != 8 else None,
            })
        return secs
    except struct.error as e:
        return [{"error": f"struct: {e}"}]


def scan_embedded_elfs(data: bytes):
    """Bounds-checked embedded ELF candidates (magic scan, dedup by offset)."""
    out = []
    pos = 0
    while True:
        pos = data.find(ELF_MAGIC, pos)
        if pos < 0:
            break
        pos += 4
        cand = {"file_offset": pos - 4}
        ok = False
        d = data[pos - 4:]
        if len(d) >= 20:
            ei_class, ei_data = d[4], d[5]
            e_machine, = struct.unpack_from("<H", d, 18)
            cand["class"] = {1: "ELF32", 2: "ELF64"}.get(ei_class, f"unknown({ei_class})")
            cand["endian"] = {1: "LE", 2: "BE"}.get(ei_data, "unknown")
            cand["machine"] = MACHINES.get(e_machine, f"0x{e_machine:x}")
            if ei_class == 2 and ei_data == 1 and len(d) >= 64:
                e_type, = struct.unpack_from("<H", d, 16)
                e_entry, = struct.unpack_from("<Q", d, 24)
                cand["type"] = {1: "REL", 2: "EXEC", 3: "DYN", 4: "CORE"}.get(
                    e_type, e_type)
                cand["entry"] = e_entry
                try:
                    # ELF64: e_phoff@32 (8B), e_phentsize@54, e_phnum@56
                    e_phoff, = struct.unpack_from("<Q", d, 32)
                    e_phentsize, e_phnum = struct.unpack_from("<HH", d, 54)
                    if e_phentsize < 56 or not e_phnum or e_phnum > 4096:
                        cand["ph_error"] = f"implausible e_phentsize={e_phentsize}"
                    else:
                        phs, bounds_ok, entry_mapped = [], True, False
                        if e_phoff + e_phnum * e_phentsize > len(d):
                            bounds_ok = False
                        for i in range(e_phnum) if bounds_ok else ():
                            ph = e_phoff + i * e_phentsize
                            if ph + 56 > len(d):
                                bounds_ok = False
                                break
                            p_type, p_flags, p_off, p_va, _, p_filesz, p_memsz = \
                                struct.unpack_from("<IIQQQQQ", d, ph)
                            valid_segment = p_off + p_filesz <= len(d)
                            if p_type == 1:
                                valid_segment = valid_segment and p_filesz <= p_memsz and p_va + p_memsz <= 1 << 64
                                if p_flags & 1 and p_va <= e_entry < p_va + p_memsz:
                                    entry_mapped = True
                            bounds_ok = bounds_ok and valid_segment
                            phs.append({"type": p_type, "va": p_va,
                                        "offset": p_off, "filesz": p_filesz, "memsz": p_memsz,
                                        "in_bounds": valid_segment})
                        cand["program_headers"] = phs
                        cand["ph_in_bounds"] = bounds_ok
                        cand["entry_in_executable_load"] = entry_mapped
                        ok = bounds_ok and entry_mapped and e_machine in MACHINES
                except struct.error:
                    cand["ph_error"] = True
        cand["status"] = "structurally-plausible" if ok else "header-only"
        cand["limit"] = "bounds checked against remaining artifact, not a proven archive-member boundary or architecture mapping"
        out.append(cand)
    return out


def loader_provenance(data: bytes):
    """Find symtab marker symbols (Perforce build paths) in outer containers."""
    marker = b"_binary__dvs_p4"
    pos = data.find(marker)
    if pos < 0:
        pos = data.find(b"_binary_")
    if pos < 0:
        return None
    end = data.find(b"\x00", pos)
    sym = data[pos:min(end, pos + 300)].decode("ascii", "replace")
    return {"symbol": sym, "note": "build-path marker from .symtab; raw string"}


def inventory(path: str) -> dict:
    data = read_artifact(path)
    rec = {
        "path": path,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
        "first_bytes": data[:4].hex(),
    }
    if data[:4] == ELF_MAGIC:
        rec["sections"] = parse_sections(data)
        rec["loader_provenance"] = loader_provenance(data)
    rec["embedded_elf_candidates"] = scan_embedded_elfs(data)
    return rec


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    json.dump([inventory(p) for p in sys.argv[1:]], sys.stdout, indent=1)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

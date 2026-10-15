#!/usr/bin/env python3
"""parse_vbios_bit.py — parse NVIDIA vBIOS BIT (BIOS Information Table) directory.

Self-calibrating: locates "BIT\\0", tries header sizes / location endianness, and picks the
interpretation whose token IDs match the official token set ('B' BIOSDATA, 'I' NVINIT,
'P' PERF, 'M' MEMORY, 'p' falcon, 'u' UEFI, 'x' MXM, ...). Token format (NVIDIA
BIOS-Information-Table spec): {u8 id; u16 location; u16 size; u8 version}.

Usage: parse_vbios_bit.py <file.rom>
Handles raw option ROMs and NVGI/EVGA-wrapped images (auto-locates inner 0x55AA image).
"""
import struct
import sys

KNOWN_IDS = set(b"BIpPMuxTSDFHKCNeEnwc")


def find_inner_rom(data: bytes):
    """Return offset of the first 0x55AA option ROM image (0 if already raw)."""
    if data[:2] == b"\x55\xaa":
        return 0
    pos = data.find(b"\x55\xaa")
    if pos >= 0 and b"PCIR" in data[pos : pos + 0x200]:
        return pos
    return 0


def parse_pcir(data, rom_off):
    pcir_off = data.find(b"PCIR", rom_off, rom_off + 0x400)
    if pcir_off < 0:
        return None
    vendor, device = struct.unpack_from("<HH", data, pcir_off + 4)
    img_len_units = struct.unpack_from("<H", data, pcir_off + 0x10)[0]
    code_type = data[pcir_off + 0x14]
    size = img_len_units * 512 if img_len_units else None
    return {
        "pcir_off": hex(pcir_off), "vendor": hex(vendor), "device": hex(device),
        "image_size": size, "code_type": hex(code_type),
    }


def parse_bit(data, rom_off, bit_off):
    """Try interpretations; return (header_info, tokens) for the first consistent match."""
    hdr = data[bit_off : bit_off + 16]
    for hdr_size in (10, 11, 12, 13, 14, 15, 16, 17, 18):
        for loc_be in (True, False):
            tokens = []
            ok = True
            pos = bit_off + hdr_size
            for _ in range(32):
                if pos + 6 > len(data):
                    ok = False
                    break
                tid = data[pos]
                (loc,) = struct.unpack_from(">H" if loc_be else "<H", data, pos + 1)
                (size,) = struct.unpack_from(">H" if loc_be else "<H", data, pos + 3)
                ver = data[pos + 5]
                if tid == 0:
                    break
                if tid not in KNOWN_IDS:
                    break  # end of token stream (next table follows) — success
                if loc > len(data) or (size and loc + size > len(data)):
                    ok = False
                    break
                tokens.append((chr(tid), loc, size, ver))
                pos += 6
            if ok and len(tokens) >= 3:
                return {"hdr_size": hdr_size, "loc_endian": "BE" if loc_be else "LE",
                        "raw_header": hdr.hex()}, tokens
    return None, None


def main():
    path = sys.argv[1]
    data = open(path, "rb").read()
    print(f"file: {path} ({len(data)} bytes)")
    print(f"first 4 bytes: {data[:4]!r}")

    rom_off = find_inner_rom(data)
    if rom_off:
        print(f"wrapped image: inner option ROM located at 0x{rom_off:x}")
    print(f"PCIR: {parse_pcir(data, rom_off)}")

    bit_off = data.find(b"BIT\x00", rom_off)
    if bit_off < 0:
        print("no BIT table found")
        return
    print(f"BIT header at file 0x{bit_off:x} (ROM-relative 0x{bit_off - rom_off:x})")
    info, tokens = parse_bit(data, rom_off, bit_off)
    if not tokens:
        print("BIT found but no token interpretation matched")
        return
    print(f"interpretation: header_size={info['hdr_size']} location_endian={info['loc_endian']}")
    print(f"raw header: {info['raw_header']}")
    names = {"B": "BIOSDATA", "I": "NVINIT", "P": "PERF", "M": "MEMORY",
             "p": "FALCON/PMU", "u": "UEFI", "x": "MXM", "S": "S?", "T": "THERMAL?"}
    print("\n id  token       location     size  version   target(file abs)   first bytes")
    for tid, loc, size, ver in tokens:
        tgt = rom_off + loc
        preview = data[tgt : tgt + 12].hex() if size else "-"
        print(f"  {tid}  {names.get(tid, '?'):10s}  0x{loc:06x}  0x{size:05x}   {ver}"
              f"      0x{tgt:06x}      {preview}")


if __name__ == "__main__":
    main()

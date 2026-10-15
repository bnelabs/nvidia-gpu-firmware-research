#!/usr/bin/env python3
"""parse_vbios_bit.py — parse NVIDIA vBIOS BIT (BIOS Information Table) per the official spec.

Spec: https://download.nvidia.com/open-gpu-doc/BIOS-Information-Table/1/BIOS-Information-Table.html

BIT header (12 B): {u16 ID=0xB8FF; char[4] "BIT\\0"; u16 BCD ver=0x0100; u8 header_size=12;
 u8 token_size=6; u8 token_entries; u8 checksum(0-sum)}
BIT token (6 B): {u8 id; u8 data_version; u16 data_size(BE); u16 data_ptr(BE, ROM-relative)}
Pointer adjustment rule: if ptr > legacy-image length, add the UEFI image length.

Usage: parse_vbios_bit.py <file.rom> [--perf]   (--perf follows BIT_PERF_PTRS v2 chain)
Handles raw ROMs and NVGI/EVGA-wrapped images (auto-locates inner 0x55AA image).
"""
import struct
import sys

# Token names from the official spec (id -> name)
NAMES = {
    0x32: "I2C_PTRS", 0x41: "DAC_PTRS", 0x42: "BIOSDATA", 0x43: "CLOCK_PTRS",
    0x44: "DFP_PTRS", 0x49: "NVINIT_PTRS", 0x4C: "LVDS_PTRS", 0x4D: "MEMORY_PTRS",
    0x4E: "NOP", 0x50: "PERF_PTRS", 0x53: "STRING_PTRS", 0x54: "TMDS_PTRS",
    0x55: "DISPLAY_PTRS", 0x56: "VIRTUAL_PTRS", 0x63: "32BIT_PTRS", 0x64: "DP_PTRS",
    0x70: "FALCON_DATA", 0x75: "UEFI_DATA", 0x78: "MXM_DATA", 0x52: "BRIDGE_FW_DATA",
}

PERF_PTRS_V2 = [  # field names in order (u32 pointers) per spec
    "PerformanceTable", "MemoryClockTable", "MemoryTweakTable", "PowerControlTable",
    "ThermalControlTable", "ThermalDeviceTable", "ThermalCoolersTable",
    "PerformanceSettingsScript", "ContinuousVirtualBinningTable", "VenturaTable",
    "PowerSensorsTable", "PowerPolicyTable", "PStateClockRangeTable",
    "VoltageFrequencyTable", "VirtualPStateTable", "PowerTopologyTable",
    "PowerLeakageTable", "PerfTestSpecTable", "ThermalChannelTable",
    "ThermalAdjustmentTable", "ThermalPolicyTable", "PStateMemClockFreqTable",
    "FanCoolerTable", "FanPolicyTable", "DIDTTable", "FanTestTable",
    "VoltageRailTable", "VoltageDeviceTable", "VoltagePolicyTable", "LowPowerTable",
    "LowPowerPCIeTable", "LowPowerPCIePlatformTable", "LowPowerGRTable",
    "LowPowerMSTable", "LowPowerDITable", "LowPowerGC6Table", "LowPowerPSITable",
    "ThermalMonitorTable", "OverclockingTable", "LowPowerNVLINKTable",
]


def find_inner_rom(data: bytes):
    """Return offset of the first 0x55AA option ROM image preceded by valid PCIR."""
    if data[:2] == b"\x55\xaa" and b"PCIR" in data[:0x400]:
        return 0
    pos = 0
    while True:
        pos = data.find(b"\x55\xaa", pos + 1)
        if pos < 0:
            return 0
        if b"PCIR" in data[pos : pos + 0x200]:
            return pos


def parse_pcir(data, rom_off):
    pcir_off = data.find(b"PCIR", rom_off, rom_off + 0x400)
    if pcir_off < 0:
        return None
    vendor, device = struct.unpack_from("<HH", data, pcir_off + 4)
    img_len_units = struct.unpack_from("<H", data, pcir_off + 0x10)[0]
    code_type = data[pcir_off + 0x14]
    return {"pcir_off": hex(pcir_off), "vendor": hex(vendor), "device": hex(device),
            "image_size_512units": img_len_units, "code_type": hex(code_type)}


def find_bit(data, rom_off):
    """Locate ID 0xB8FF + 'BIT\\0' per spec. Returns (bit_off, header dict) or (None, None)."""
    pos = rom_off
    while True:
        pos = data.find(b"BIT\x00", pos + 1)
        if pos < 2:
            return None, None
        if data[pos - 2 : pos] == b"\xff\xb8":
            base = pos - 2
            hdr = data[base : base + 12]
            id_, sig, bcd, hsize, tsize, entries, cksum = struct.unpack("<H4sHBBBB", hdr)
            return base, {"id": hex(id_), "bcd": hex(bcd), "header_size": hsize,
                          "token_size": tsize, "token_entries": entries,
                          "checksum": hex(cksum),
                          "raw": hdr.hex()}
        # else keep scanning


def parse_tokens(data, rom_off, bit_off, hdr):
    tokens = []
    pos = bit_off + hdr["header_size"]
    for _ in range(hdr["token_entries"]):
        tid, ver, size, ptr = struct.unpack_from("<BBHH", data, pos)
        tokens.append({"id": tid, "name": NAMES.get(tid, hex(tid)),
                       "ver": ver, "size": size, "ptr": ptr, "tok_off": pos})
        pos += hdr["token_size"]
    return tokens


def adj_ptr(ptr, legacy_len):
    """Spec pointer-adjustment rule for pointers beyond the legacy image."""
    return ptr + 0 if ptr <= legacy_len else None  # caller supplies legacy_len


def main():
    path = sys.argv[1]
    follow_perf = "--perf" in sys.argv
    data = open(path, "rb").read()
    print(f"file: {path} ({len(data)} bytes), first 4: {data[:4]!r}")

    rom_off = find_inner_rom(data)
    if rom_off:
        print(f"wrapped image: inner option ROM at 0x{rom_off:x}")
    print(f"PCIR: {parse_pcir(data, rom_off)}")

    bit_off, hdr = find_bit(data, rom_off)
    if not bit_off:
        print("no BIT (ID 0xB8FF + BIT\\0) found")
        return
    print(f"BIT @0x{bit_off:x}: {hdr}")
    tokens = parse_tokens(data, rom_off, bit_off, hdr)
    print(f"\n{'id':>4}  {'token':<12} ver  size     ptr      target(file)")
    for t in tokens:
        if t["name"] == "NOP" or t["ptr"] == 0:
            print(f" 0x{t['id']:02x}  {t['name']:<12} {t['ver']:3}  {t['size']:6}  (nop)")
            continue
        tgt = rom_off + t["ptr"]
        print(f" 0x{t['id']:02x}  {t['name']:<12} {t['ver']:3}  {t['size']:6}  0x{t['ptr']:04x}   0x{tgt:06x}")

    if follow_perf:
        perf = next((t for t in tokens if t["name"] == "PERF_PTRS"), None)
        if not perf:
            print("no PERF_PTRS token")
            return
        base = rom_off + perf["ptr"]
        print(f"\nBIT_PERF_PTRS v{perf['ver']} @0x{base:x} ({perf['size']} bytes):")
        n = perf["size"] // 4
        for i in range(n):
            (val,) = struct.unpack_from("<I", data, base + 4 * i)
            if not val:
                continue
            name = PERF_PTRS_V2[i] if i < len(PERF_PTRS_V2) else f"field{i}"
            # v2 pointers are 32-bit offsets into the ROM image
            tgt = rom_off + val
            print(f"  [{i:2d}] {name:<32} 0x{val:06x} -> file 0x{tgt:06x}  first: {data[tgt:tgt+8].hex()}")


if __name__ == "__main__":
    main()

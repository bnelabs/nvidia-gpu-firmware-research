#!/usr/bin/env python3
"""parse_vbios_bit.py — parse NVIDIA vBIOS BIT (BIOS Information Table) per the official spec.

Spec: https://download.nvidia.com/open-gpu-doc/BIOS-Information-Table/1/BIOS-Information-Table.html

BIT header (12 B): {u16 ID=0xB8FF; char[4] "BIT\\0"; u16 BCD ver=0x0100; u8 header_size=12;
 u8 token_size=6; u8 token_entries; u8 checksum(0-sum)}
BIT token (6 B): {u8 id; u8 data_version; u16 data_size(LE); u16 data_ptr(LE, ROM-relative)}
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


def require(data, offset, size, label):
    if offset < 0 or size < 0 or offset + size > len(data):
        raise ValueError(f"{label}: out of bounds at 0x{offset:x} ({size} bytes)")


def parse_pcir(data, rom_off):
    require(data, rom_off, 0x1a, "ROM header")
    if data[rom_off:rom_off + 2] != b"\x55\xaa":
        raise ValueError("missing option ROM signature")
    pcir_off = rom_off + struct.unpack_from("<H", data, rom_off + 0x18)[0]
    require(data, pcir_off, 0x18, "PCIR")
    if data[pcir_off:pcir_off + 4] != b"PCIR":
        raise ValueError("invalid PCIR pointer/signature")
    vendor, device = struct.unpack_from("<HH", data, pcir_off + 4)
    units = struct.unpack_from("<H", data, pcir_off + 0x10)[0]
    if not units:
        raise ValueError("zero-length option ROM image")
    require(data, rom_off, units * 512, "option ROM image")
    if pcir_off + 0x18 > rom_off + units * 512:
        raise ValueError("PCIR outside option ROM image")
    return {"pcir_off": hex(pcir_off), "vendor": hex(vendor), "device": hex(device),
            "image_size_512units": units, "code_type": data[pcir_off + 0x14],
            "last_image": bool(data[pcir_off + 0x15] & 0x80)}


def find_inner_rom(data):
    """Validate the header's PCIR pointer at each 512-byte boundary."""
    for pos in range(0, len(data), 512):
        if data[pos:pos + 2] == b"\x55\xaa":
            try:
                parse_pcir(data, pos)
                return pos
            except ValueError:
                continue
    raise ValueError("no valid PCI option ROM found")


def image_lengths(data, rom_off):
    """Walk the PCI image chain; adjustment applies to a following UEFI image."""
    first = parse_pcir(data, rom_off)
    if first["code_type"] != 0:
        raise ValueError("expected legacy image before BIT pointer resolution")
    legacy_len = first["image_size_512units"] * 512
    uefi_len = 0
    pos, current = rom_off, first
    while not current["last_image"]:
        pos += current["image_size_512units"] * 512
        current = parse_pcir(data, pos)
        if pos == rom_off + legacy_len and current["code_type"] == 3:
            uefi_len = current["image_size_512units"] * 512
    return legacy_len, uefi_len


def find_bit(data, rom_off):
    legacy_len, _ = image_lengths(data, rom_off)
    base = data.find(b"\xff\xb8BIT\x00", rom_off, rom_off + legacy_len)
    if base < 0:
        return None, None
    require(data, base, 12, "BIT header")
    id_, sig, bcd, hsize, tsize, entries, cksum = struct.unpack_from("<H4sHBBBB", data, base)
    if bcd != 0x100 or hsize < 12 or tsize < 6:
        raise ValueError("unsupported BIT version/header/token size")
    require(data, base, hsize + tsize * entries, "BIT directory")
    if base + hsize + tsize * entries > rom_off + legacy_len:
        raise ValueError("BIT directory exceeds legacy image")
    if sum(data[base:base + hsize]) & 0xff:
        raise ValueError("invalid BIT header checksum")
    return base, {"id": hex(id_), "bcd": hex(bcd), "header_size": hsize,
                  "token_size": tsize, "token_entries": entries,
                  "checksum": hex(cksum), "raw": data[base:base + hsize].hex()}


def adj_ptr(ptr, legacy_len, uefi_len=0):
    return ptr + (uefi_len if ptr > legacy_len else 0)


def parse_tokens(data, rom_off, bit_off, hdr):
    legacy_len, uefi_len = image_lengths(data, rom_off)
    tokens = []
    pos = bit_off + hdr["header_size"]
    for _ in range(hdr["token_entries"]):
        require(data, pos, hdr["token_size"], "BIT token")
        tid, ver, size, ptr = struct.unpack_from("<BBHH", data, pos)
        target = rom_off + adj_ptr(ptr, legacy_len, uefi_len) if ptr else None
        if target is not None and tid != 0x4e:
            require(data, target, size, "BIT token payload")
        tokens.append({"id": tid, "name": NAMES.get(tid, hex(tid)),
                       "ver": ver, "size": size, "ptr": ptr, "tok_off": pos,
                       "target": target})
        pos += hdr["token_size"]
    return tokens


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom")
    parser.add_argument("--perf", action="store_true")
    args = parser.parse_args()
    path, follow_perf = args.rom, args.perf
    with open(path, "rb") as stream:
        data = stream.read()
    print(f"file: {path} ({len(data)} bytes), first 4: {data[:4]!r}")

    rom_off = find_inner_rom(data)
    if rom_off:
        print(f"wrapped image: inner option ROM at 0x{rom_off:x}")
    print(f"PCIR: {parse_pcir(data, rom_off)}")

    bit_off, hdr = find_bit(data, rom_off)
    if bit_off is None:
        print("no BIT (ID 0xB8FF + BIT\\0) found")
        raise ValueError("BIT directory missing")
    print(f"BIT @0x{bit_off:x}: {hdr}")
    tokens = parse_tokens(data, rom_off, bit_off, hdr)
    print(f"\n{'id':>4}  {'token':<12} ver  size     ptr      target(file)")
    for t in tokens:
        if t["name"] == "NOP" or t["ptr"] == 0:
            print(f" 0x{t['id']:02x}  {t['name']:<12} {t['ver']:3}  {t['size']:6}  (nop)")
            continue
        tgt = t["target"]
        print(f" 0x{t['id']:02x}  {t['name']:<12} {t['ver']:3}  {t['size']:6}  0x{t['ptr']:04x}   0x{tgt:06x}")

    if follow_perf:
        perf = next((t for t in tokens if t["name"] == "PERF_PTRS"), None)
        if not perf:
            print("no PERF_PTRS token")
            return
        if perf["ver"] != 2:
            raise ValueError("PERF field names only supported for version 2")
        if perf["target"] is None:
            raise ValueError("PERF token has no data")
        if perf["size"] % 4:
            raise ValueError("PERF pointer array size is not a multiple of four")
        base = perf["target"]
        legacy_len, uefi_len = image_lengths(data, rom_off)
        print(f"\nBIT_PERF_PTRS v{perf['ver']} @0x{base:x} ({perf['size']} bytes):")
        n = perf["size"] // 4
        for i in range(n):
            (val,) = struct.unpack_from("<I", data, base + 4 * i)
            if not val:
                continue
            name = PERF_PTRS_V2[i] if i < len(PERF_PTRS_V2) else f"field{i}"
            # v2 pointers are 32-bit offsets into the ROM image
            tgt = rom_off + adj_ptr(val, legacy_len, uefi_len)
            require(data, tgt, 1, "PERF target")
            print(f"  [{i:2d}] {name:<32} 0x{val:06x} -> file 0x{tgt:06x}  first: {data[tgt:tgt+8].hex()}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        sys.exit(f"error: {exc}")

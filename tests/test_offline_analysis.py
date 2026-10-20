import importlib.util
from pathlib import Path
import struct
import unittest
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from offline_io import read_artifact
def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m
inventory = module("inventory_firmware")
xref = module("riscv_xref")

def elf():
    b = bytearray(256)
    b[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<HHIQQ", b, 16, 2, 0xf3, 1, 0x1000, 64)
    struct.pack_into("<HHH", b, 52, 64, 56, 1)
    struct.pack_into("<IIQQQQQ", b, 64, 1, 5, 128, 0x1000, 0, 16, 16)
    return b

class OfflineAnalysisTests(unittest.TestCase):
    def test_artifact_reader_rejects_pseudo_files_and_symlink_aliases(self):
        for path in ("/dev/null", "/dev/../dev/null"):
            with self.assertRaises(ValueError):
                read_artifact(path)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "alias"
            p.symlink_to("/dev/null")
            with self.assertRaises(ValueError):
                read_artifact(p)
            p.unlink()
            p.write_bytes(b"copied artifact")
            self.assertEqual(read_artifact(p), b"copied artifact")

    def test_short_elf_is_not_a_validated_container(self):
        for b in (b"\x7fELF", b"\x7fELF\x02"):
            self.assertEqual(inventory.parse_sections(b), [])
    def test_segments_and_entry_point_must_be_in_bounds(self):
        self.assertEqual(inventory.scan_embedded_elfs(elf())[0]["status"], "structurally-plausible")
        for offset, value in ((72, 10000), (96, 10000), (24, 0x9999)):
            b = elf()
            struct.pack_into("<Q", b, offset, value)
            self.assertEqual(inventory.scan_embedded_elfs(b)[0]["status"], "header-only")
    def test_xref_checks_source_register_and_last_pair(self):
        lui = (0x12345 << 12) | (5 << 7) | 0x37
        addi = (0x678 << 20) | (5 << 15) | (5 << 7) | 0x13
        pair = struct.pack("<II", lui, addi)
        self.assertEqual(xref.lui_addi_addrs(pair, 0x12345678), [(0, 5, 1)])
        self.assertEqual(xref.lui_addi_addrs(b"\x01\x00" + pair, 0x12345678), [(2, 5, 1)])
        wrong = struct.pack("<II", lui, addi ^ (1 << 15))
        self.assertEqual(xref.lui_addi_addrs(wrong, 0x12345678), [])
    def test_rv64_lui_sign_extension(self):
        pair = struct.pack("<II", 0x800002b7, 0x00028293)
        self.assertEqual(xref.lui_addi_addrs(pair, 0xffffffff80000000), [(0, 5, 1)])
        self.assertEqual(xref.lui_addi_addrs(pair, 0x80000000), [])

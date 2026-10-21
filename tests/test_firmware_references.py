"""Independent instruction encodings check signed PC-relative target arithmetic."""
import importlib.util
from pathlib import Path
import struct
import unittest
import capstone

spec = importlib.util.spec_from_file_location('firmware_ranges', Path(__file__).resolve().parents[1] / 'research/2026-10-21-pstate-writers/export_ranges.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class FirmwareReferenceTests(unittest.TestCase):
    def decode(self, upper, low, consumer_register=1, gap=False):
        first = (upper & 0xfffff000) | (1 << 7) | 0x17
        second = ((low & 0xfff) << 20) | (consumer_register << 15) | (1 << 7) | 0x67
        raw = struct.pack('<I',first) + (b'\x01\x00' if gap else b'') + struct.pack('<I',second)
        md=capstone.Cs(capstone.CS_ARCH_RISCV,capstone.CS_MODE_RISCV64|capstone.CS_MODE_RISCVC)
        return module.references(list(md.disasm(raw,0x16be9a0)))

    def test_negative_upper_real_target(self):
        r=self.decode(-0x41000,0x4a0)
        self.assertEqual(r[0]['target_firmware_elf_va'],'0x167de40')
        self.assertEqual(r[0]['signed_upper'],-0x41000)

    def test_negative_low_and_jalr_low_bit(self):
        r=self.decode(0x1000,-1)
        self.assertEqual(int(r[0]['target_firmware_elf_va'],16), (0x16be9a0+0x1000-1)&~1)
        self.assertEqual(r[0]['signed_low'],-1)

    def test_mismatched_or_nonadjacent_not_resolved(self):
        self.assertEqual(self.decode(0x1000,0x100,consumer_register=2),[])
        self.assertEqual(self.decode(0x1000,0x100,gap=True),[])

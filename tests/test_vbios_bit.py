"""Synthetic ROMs: no GPU access and no redistributed firmware required."""
import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location('bit', Path(__file__).resolve().parents[1] / 'scripts/parse_vbios_bit.py')
bit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bit)


def fixture(wrapped=False):
    data = bytearray(2048)
    for offset, code, last in [(0, 0, 0), (512, 3, 0x80)]:
        data[offset:offset + 2] = b'\x55\xaa'
        struct.pack_into('<H', data, offset + 0x18, 0x40)
        p = offset + 0x40
        data[p:p + 4] = b'PCIR'
        struct.pack_into('<HH', data, p + 4, 0x10de, 0x2204)
        struct.pack_into('<H', data, p + 0x10, 1)
        data[p + 0x14:p + 0x16] = bytes([code, last])
    header = bytearray(struct.pack('<H4sHBBBB', 0xb8ff, b'BIT\0', 0x100, 12, 6, 1, 0))
    header[-1] = (-sum(header)) & 0xff
    data[0x80:0x8c] = header
    struct.pack_into('<BBHH', data, 0x8c, ord('P'), 2, 4, 0xa0)
    struct.pack_into('<I', data, 0xa0, 0x300)
    data[0x500:0x508] = b'REALDATA'
    return bytes(512) + data if wrapped else data


class ParserTests(unittest.TestCase):
    def test_raw_and_wrapped_adjustment(self):
        for wrapped in (False, True):
            data = fixture(wrapped)
            off = bit.find_inner_rom(data)
            self.assertEqual(off, 512 if wrapped else 0)
            base, header = bit.find_bit(data, off)
            token = bit.parse_tokens(data, off, base, header)[0]
            self.assertEqual(token['size'], 4)
            self.assertEqual(token['ptr'], 0xa0)
            ptr, = struct.unpack_from('<I', data, token['target'])
            target = off + bit.adj_ptr(ptr, *bit.image_lengths(data, off))
            self.assertEqual(data[target:target + 8], b'REALDATA')

    def test_adjustment_boundary(self):
        self.assertEqual(bit.adj_ptr(512, 512, 512), 512)
        self.assertEqual(bit.adj_ptr(513, 512, 512), 1025)
        self.assertEqual(bit.adj_ptr(513, 512), 513)

    def test_invalid_checksum(self):
        data = fixture()
        data[0x8b] ^= 1
        with self.assertRaisesRegex(ValueError, 'checksum'):
            bit.find_bit(data, 0)

    def test_invalid_pcir_pointer(self):
        data = fixture()
        struct.pack_into('<H', data, 0x18, 0x60)
        with self.assertRaisesRegex(ValueError, 'PCIR'):
            bit.parse_pcir(data, 0)

    def test_truncated_image(self):
        with self.assertRaises(ValueError):
            bit.image_lengths(fixture()[:800], 0)

    def test_token_payload_out_of_bounds(self):
        data = fixture()
        struct.pack_into('<H', data, 0x90, 0xffff)
        base, header = bit.find_bit(data, 0)
        with self.assertRaisesRegex(ValueError, 'payload'):
            bit.parse_tokens(data, 0, base, header)

    def test_token_stride_rejected(self):
        data = fixture()
        data[0x89] = 5
        with self.assertRaisesRegex(ValueError, 'size'):
            bit.find_bit(data, 0)


if __name__ == '__main__':
    unittest.main()

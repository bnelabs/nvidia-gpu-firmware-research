from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from extract_nvoc_exports import parse


def fixture():
    b = bytearray(1024)
    b[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<H', b, 18, 243)
    struct.pack_into('<Q', b, 32, 64)
    struct.pack_into('<HH', b, 54, 56, 1)
    struct.pack_into('<II6Q', b, 64, 1, 5, 0, 0x1000000, 0, len(b), len(b), 4096)
    struct.pack_into('<II4Q', b, 0x100, 0x530, 0x4b01b3, 0, 0, 0, 0x1000180)
    struct.pack_into('<IIQ', b, 0x180, 2, 0, 0x1000200)
    struct.pack_into('<QIIIIQ', b, 0x200, 0x1000300, 0xc0, 0, 0x20800aff, 16, 0x1000100)
    struct.pack_into('<QIIIIQ', b, 0x220, 0, 0x50048, 0, 0x20802068, 4, 0x1000100)
    return b


class NvocExportsTests(unittest.TestCase):
    def test_preserves_file_va_null_pointer_and_raw_fields(self):
        r = parse(fixture(), 0x1000100)
        self.assertEqual(r['class_definition']['class_id'], '0x4b01b3')
        self.assertEqual(r['export_info']['count'], 2)
        self.assertEqual(r['methods'][0]['entry_file_offset'], '0x200')
        self.assertEqual(r['methods'][0]['function_file_offset'], '0x300')
        self.assertEqual(r['methods'][0]['params_bytes'], 16)
        self.assertIsNone(r['methods'][1]['function_file_offset'])

    def test_bounds_and_unsorted_entries_are_rejected(self):
        for offset, fmt, value in ((0x180, '<I', 65537), (0x188, '<Q', 0x10003f0),
                                   (0x100 + 32, '<Q', 0x9999999),
                                   (0x220 + 16, '<I', 0x20800000),
                                   (0x200, '<Q', 0x9999999)):
            with self.subTest(offset=offset):
                b = fixture()
                struct.pack_into(fmt, b, offset, value)
                with self.assertRaises(ValueError):
                    parse(b, 0x1000100)

    def test_incomplete_load_is_rejected(self):
        b = fixture()
        struct.pack_into('<Q', b, 64 + 32, len(b) + 1)
        with self.assertRaises(ValueError):
            parse(b, 0x1000100)

import gzip
from pathlib import Path
import sys
import unittest
import struct
import zlib
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from compare_ga102_boot import analyze, extract


def source(payload, *, bad_padding=False, bad_crc=False, bad_size=False):
    packed = bytearray(gzip.compress(payload, mtime=0)[10:])
    if bad_crc:
        packed[-8] ^= 1
    n = len(packed)
    packed.extend(b'\x00' * ((-n) % 8))
    if bad_padding:
        if len(packed) == n:
            raise AssertionError('fixture needs padding')
        packed[-1] = 1
    words = ', '.join('0x%016xULL' % x[0] for x in struct.iter_unpack('<Q', packed))
    return '''// FUNCTION: kgspGetBinArchiveGspRmBoot_GA102("BINDATA_LABEL_UCODE_DESC_PROD")
// COMPRESSION: YES
// DATA SIZE (bytes): %d
// COMPRESSED SIZE (bytes): %d
static BINDATA_CONST NV_DECLARE_ALIGNED(NvU64, 8) kgspBinArchiveGspRmBoot_GA102_BINDATA_LABEL_UCODE_DESC_PROD_data[] = {%s};
''' % (len(payload) + int(bad_size), n, words)


class BindataBootTests(unittest.TestCase):
    def test_storage_padding_is_not_descriptor_data(self):
        data, meta = extract(source(bytes(range(84))), 'DESC_PROD')
        self.assertEqual(data, bytes(range(84)))
        self.assertEqual(meta['decoded_bytes'], 84)
        self.assertLess(meta['compressed_bytes'], meta['storage_bytes'])

    def test_padding_crc_and_declared_size_are_checked(self):
        for options in ({'bad_padding': True}, {'bad_crc': True}, {'bad_size': True}):
            with self.subTest(options=options), self.assertRaises((ValueError, zlib.error)):
                extract(source(bytes(range(84)), **options), 'DESC_PROD')

    def test_truncated_initializer_and_wrong_component_are_rejected(self):
        valid = source(bytes(range(84)))
        for damaged in (valid[:valid.rfind(',')]+ '};', valid.replace('GA102', 'GH100')):
            with self.assertRaises(ValueError):
                extract(damaged, 'DESC_PROD')

    def test_expansion_size_is_bounded_before_decompression(self):
        valid = source(bytes(range(84)))
        with self.assertRaises(ValueError):
            extract(valid.replace('bytes): 84\n', 'bytes): 4294967295\n'), 'DESC_PROD')

    def test_descriptor_regions_and_version_fail_closed(self):
        image = bytes(range(256))
        for version, offset, size in ((5, 256, 1), (5, 250, 7), (99, 0, 0)):
            desc = bytearray(84)
            struct.pack_into('<3I', desc, 0, version, offset, size)
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'copied-source.c'
                path.write_text(source(image).replace('DESC_PROD', 'IMAGE_PROD') + source(desc))
                with self.assertRaises(ValueError):
                    analyze(path)

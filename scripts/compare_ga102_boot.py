#!/usr/bin/env python3
"""Compare copied GA102 PROD boot bindata, without importing vendor code.

Supports the NvU64 little-endian storage representation used by the two pinned
r615 releases. Gzip framing follows NVIDIA's nouveau extractor; storage padding
is excluded using the declared compressed length. CRC and ISIZE are checked.
This parses files only. It neither loads firmware nor verifies boot signatures.
"""
import argparse
import hashlib
import json
import re
import struct

from offline_io import read_artifact

FIELDS = (
    "version bootloaderOffset bootloaderSize bootloaderParamOffset "
    "bootloaderParamSize riscvElfOffset riscvElfSize appVersion manifestOffset "
    "manifestSize monitorDataOffset monitorDataSize monitorCodeOffset "
    "monitorCodeSize bIsMonitorEnabled swbromCodeOffset swbromCodeSize "
    "swbromDataOffset swbromDataSize fbReservedSize bSignedAsCode"
).split()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def extract(source, label):
    pattern = (
        r'// FUNCTION: [^\n]+\("BINDATA_LABEL_UCODE_' + re.escape(label)
        + r'"\)(.*?)\[\]\s*=\s*\{(.*?)\};'
    )
    matches = list(re.finditer(pattern, source, re.S))
    if len(matches) != 1:
        raise ValueError("expected exactly one GA102 bindata record: " + label)
    match = matches[0]
    metadata, body = match.groups()
    if "NV_DECLARE_ALIGNED(NvU64, 8) kgspBinArchiveGspRmBoot_GA102_" not in metadata:
        raise ValueError("unsupported bindata element type or component")
    if "// COMPRESSION: YES" not in metadata:
        raise ValueError("expected compressed record")
    size = int(re.search(r'// DATA SIZE \(bytes\): (\d+)', metadata)[1])
    compressed_size = int(re.search(r'// COMPRESSED SIZE \(bytes\): (\d+)', metadata)[1])
    if not 0 < size <= 1024 * 1024 or not 8 <= compressed_size <= 1024 * 1024:
        raise ValueError("unreasonable record size")
    words = re.findall(r'0x([0-9a-fA-F]{1,16})ULL', body)
    remainder = re.sub(r'0x[0-9a-fA-F]{1,16}ULL|[\s,]', '', body)
    if remainder:
        raise ValueError("unsupported bindata initializer")
    storage = b''.join(struct.pack('<Q', int(word, 16)) for word in words)
    if len(storage) != (compressed_size + 7) // 8 * 8:
        raise ValueError("storage extent does not match declared length")
    if any(storage[compressed_size:]):
        raise ValueError("nonzero storage padding")
    packed = storage[:compressed_size]
    # 10-byte gzip header; payload already contains the CRC32/ISIZE trailer.
    # Precheck ISIZE and use a bounded decompressor to reject expansion bombs.
    if struct.unpack('<I', packed[-4:])[0] != size:
        raise ValueError("gzip ISIZE disagrees with bindata")
    import zlib
    decoder = zlib.decompressobj(31)
    data = decoder.decompress(bytes.fromhex('1f8b0800000000000003') + packed, size + 1)
    if len(data) != size or not decoder.eof or decoder.unused_data:
        raise ValueError("decompressed length or gzip framing mismatch")
    return data, {
        "label": label, "source_line": source[:match.start()].count('\n') + 1,
        "storage_bytes": len(storage), "compressed_bytes": compressed_size,
        "decoded_bytes": len(data), "padding_hex": storage[compressed_size:].hex(),
        "storage_sha256": digest(storage), "compressed_sha256": digest(packed),
        "decoded_sha256": digest(data), "gzip_crc32_isize_hex": packed[-8:].hex(),
    }


def analyze(path):
    original = read_artifact(path)
    source = original.decode('utf-8')
    image, image_record = extract(source, 'IMAGE_PROD')
    desc, desc_record = extract(source, 'DESC_PROD')
    if len(desc) != 84:
        raise ValueError("only the observed 84-byte descriptor prefix is supported")
    fields = dict(zip(FIELDS, struct.unpack('<21I', desc)))
    if fields['version'] != 5:
        raise ValueError("unsupported descriptor version")
    regions = {}
    for prefix in ('bootloader', 'bootloaderParam', 'riscvElf', 'manifest',
                   'monitorData', 'monitorCode', 'swbromCode', 'swbromData'):
        offset, size = fields[prefix + 'Offset'], fields[prefix + 'Size']
        if offset > len(image) or size > len(image) - offset:
            raise ValueError("image region out of bounds: " + prefix)
        region = image[offset:offset + size]
        regions[prefix] = {"offset": offset, "size": size, "sha256": digest(region),
                           "first_32_bytes_hex": region[:32].hex()}
    return image, desc, {
        "path": str(path), "source_bytes": len(original), "source_sha256": digest(original),
        "address_domain": "decompressed component file offset; no hardware load address inferred",
        "image": image_record, "descriptor": desc_record, "descriptor_hex": desc.hex(),
        "descriptor_fields": fields, "regions": regions,
        "absent_descriptor_tail": ["bIsSmp", "bIsPlicEnabled"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('older')
    parser.add_argument('newer')
    args = parser.parse_args()
    a, ad, ar = analyze(args.older)
    b, bd, br = analyze(args.newer)
    print(json.dumps({"status": "source-decoded", "component": "GA102 GspRmBoot PROD",
                      "artifacts": [ar, br], "image_byte_identical": a == b,
                      "descriptor_byte_identical": ad == bd,
                      "limits": "Packaging equality does not prove runtime selection, hardware support, signature validity, or all firmware equality."}, indent=2))


if __name__ == '__main__':
    main()

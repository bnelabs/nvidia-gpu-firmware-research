#!/usr/bin/env python3
"""Raw RV64 SD encoding candidates at an explicit object displacement.

Halfword-aligned patterns in executable LOAD bytes are leads, not a proven CFG.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from export_ranges import PATH, EXPECTED, signed
from extract_nvoc_exports import mapping
from offline_io import read_artifact

displacement = int(sys.argv[1], 0)
data = read_artifact(PATH)
assert hashlib.sha256(data).hexdigest() == EXPECTED
rows = []
for off, base, size, flags in mapping(data):
    if not flags & 1:
        continue
    for relative in range(0, size-3, 2):
        word = struct.unpack_from('<I', data, off+relative)[0]
        if word & 0x707f != 0x3023:
            continue
        immediate = signed(((word >> 25) << 5) | ((word >> 7) & 31), 12)
        if immediate == displacement:
            rows.append({'firmware_elf_va': hex(base+relative), 'file_offset': hex(off+relative),
                         'raw_hex': data[off+relative:off+relative+4].hex(),
                         'base_x_register': (word >> 15) & 31, 'value_x_register': (word >> 20) & 31})
print(json.dumps({'artifact_sha256': EXPECTED, 'displacement': displacement, 'encoding_candidates': rows,
                  'limits': 'Raw halfword scan of executable LOAD only; includes possible data/overlapping decodes and unrelated object types. Candidate presence is not a reference or writer proof.'}, indent=2))

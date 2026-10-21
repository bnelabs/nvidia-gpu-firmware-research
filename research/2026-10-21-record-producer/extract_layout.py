#!/usr/bin/env python3
"""Retain the exact selector jump table; no guessed format names."""
import hashlib,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'2026-10-21-pstate-writers'))
from offline_io import read_artifact
from extract_nvoc_exports import mapping,region
from export_ranges import PATH,EXPECTED
data=read_artifact(PATH);assert hashlib.sha256(data).hexdigest()==EXPECTED
base=0x1e13bb4
raw,offset,flags=region(data,mapping(data),base,28)
rows=[{'format_byte':i,'relative_i32':struct.unpack_from('<i',raw,4*i)[0],
       'target_firmware_elf_va':hex(base+struct.unpack_from('<i',raw,4*i)[0])} for i in range(7)]
assert rows[0]['target_firmware_elf_va']=='0x1768232'
assert rows[1]['target_firmware_elf_va']=='0x1767c28'
print(json.dumps({'artifact_sha256':EXPECTED,'address_domain':'firmware ELF VA with file offsets',
    'jump_table':{'firmware_elf_va':hex(base),'file_offset':hex(offset),'bytes':len(raw),
        'raw_hex':raw.hex(),'sha256':hashlib.sha256(raw).hexdigest(),'load_flags_raw':flags,'cases':rows},
    'interpretation':'Format byte 1 selects the copied 12-byte internal mask construction branch; format 0 selects an error branch. These are artifact-specific selectors, not public wire-format names.',
    'limits':'Raw table plus demonstrated dispatch consumer at 0x1767a2c; no real source table bytes or runtime format observed.'},indent=2))

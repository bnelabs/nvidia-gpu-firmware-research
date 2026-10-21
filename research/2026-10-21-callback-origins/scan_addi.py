#!/usr/bin/env python3
"""Literal ADDI displacement candidates in executable LOAD; no CFG claims."""
import hashlib,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'2026-10-21-pstate-writers'))
from export_ranges import PATH,EXPECTED,signed
from extract_nvoc_exports import mapping
from offline_io import read_artifact
data=read_artifact(PATH)
assert hashlib.sha256(data).hexdigest()==EXPECTED
value=int(sys.argv[1],0)
rows=[]
for off,base,size,flags in mapping(data):
    if not flags&1:continue
    for k in range(0,size-3,2):
        w=struct.unpack_from('<I',data,off+k)[0]
        if w&0x707f==0x13 and signed(w>>20,12)==value:
            rows.append({'firmware_elf_va':hex(base+k),'file_offset':hex(off+k),
                         'raw_hex':data[off+k:off+k+4].hex(),'rd':(w>>7)&31,'rs1':(w>>15)&31})
print(json.dumps({'artifact_sha256':EXPECTED,'immediate':value,'encoding_candidates':rows,
    'limits':'Raw halfword-aligned instruction patterns only, not proven references, object identities or CFG paths.'},indent=2))

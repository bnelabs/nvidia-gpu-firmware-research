#!/usr/bin/env python3
"""Explicit NVOC records and exact-target call leads in a retained firmware ELF."""
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'2026-10-21-pstate-writers'))
from offline_io import read_artifact
from extract_nvoc_exports import mapping, region
from export_ranges import PATH, EXPECTED, signed

data=read_artifact(PATH)
assert hashlib.sha256(data).hexdigest()==EXPECTED
segments=mapping(data)
root=Path('vendor/open-gpu-kernel-modules-615.71.09')
commit='61dcc93722ecb418bb5f2e00923f05b4b8051dd1'
assert read_artifact(root/'.git/HEAD').decode().strip()==commit

def raw(va,size):
    b,off,flags=region(data,segments,va,size)
    return {'firmware_elf_va':hex(va),'file_offset':hex(off),'bytes':size,
            'load_flags_raw':flags,'raw_hex':b.hex(),'sha256':hashlib.sha256(b).hexdigest()}

classes=[]
for name,va,ident,source in [
    ('OBJGPU',0x1e19c58,0x7ef3cb,'src/nvidia/generated/g_gpu_nvoc.h'),
    ('Perf',0x1cb0978,0xed0b65,'src/nvidia/generated/g_eng_desc_nvoc.h'),
    ('KernelPerf',0x1cb0950,0xc53a57,'src/nvidia/generated/g_eng_desc_nvoc.h'),
]:
    source_bytes=read_artifact(root/source)
    text=source_bytes.decode()
    match=re.search(r'^#define __nvoc_class_id_'+name+r'\s+(0x[0-9a-f]+)u',text,re.M)
    assert match and int(match[1],16)==ident
    record=raw(va,40)
    size,identifier,provider,creator,casts,exports=struct.unpack('<II4Q',bytes.fromhex(record['raw_hex']))
    assert identifier & 0xffffff == ident
    count=struct.unpack('<I',region(data,segments,casts,4)[0])[0]
    assert 0<count<64
    cast_raw=raw(casts,8+count*8)
    relatives=[]
    for ptr in struct.unpack_from('<'+'Q'*count,bytes.fromhex(cast_raw['raw_hex']),8):
        rtti=raw(ptr,24)
        class_va,dtor,offset=struct.unpack('<QQI4x',bytes.fromhex(rtti['raw_hex']))
        definition=raw(class_va,40)
        relatives.append({'rtti':rtti,'class_definition':definition,'dtor_firmware_elf_va':hex(dtor),
                          'subobject_offset_raw':offset,'class_id_raw':hex(struct.unpack_from('<I',bytes.fromhex(definition['raw_hex']),4)[0]&0xffffff)})
    classes.append({'source_identity':name,'source_path':source,'source_commit':commit,
                    'source_sha256':hashlib.sha256(source_bytes).hexdigest(),'source_line':text[:match.start()].count('\n')+1,
                    'class_definition':record,'object_bytes':size,'class_id_raw':hex(ident),
                    'provider_pointer_raw':hex(provider),'create_firmware_elf_va':hex(creator),
                    'cast_info':cast_raw,'relatives':relatives,'export_info':raw(exports,16)})

# New discriminator: exact direct-call target obtained from the typed Perf path.
# Raw pairs are still candidates until checked against the retained caller block.
calls=[]
for off,base,size,flags in segments:
    if not flags&1: continue
    for rel in range(0,size-7,2):
        a,b=struct.unpack_from('<II',data,off+rel)
        if a&127!=0x17 or b&0x707f!=0x67 or not (a>>7)&31 or (b>>15)&31!=(a>>7)&31:
            continue
        target=(base+rel+signed(a&0xfffff000,32)+signed(b>>20,12))&((1<<64)-1)&~1
        if target==0x1be9250:
            calls.append({'raw_pair':raw(base+rel,8),'target_firmware_elf_va':hex(target)})
assert [c['raw_pair']['firmware_elf_va'] for c in calls]==['0x1668540']
print(json.dumps({'artifact_path':PATH,'artifact_bytes':len(data),'artifact_sha256':EXPECTED,
    'class_records':classes,'selected_metadata_bytes':[raw(0x1caa550,0x180),raw(0x1ecb278,24)],
    'exact_target_call_candidates':calls,
    'limits':'Source class IDs identify retained metadata, not matching public/private object layouts or current instances. Metadata slots are raw offsets unless their consumer is demonstrated. Exact-target raw instruction pairs require caller/dataflow validation; runtime overrides and availability remain unknown.'},indent=2))

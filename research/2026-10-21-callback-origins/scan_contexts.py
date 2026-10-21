#!/usr/bin/env python3
"""Retain raw contexts for SD displacement leads, without promoting dataflow."""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'2026-10-21-pstate-writers'))
from export_ranges import PATH, EXPECTED, references
from offline_io import read_artifact
from extract_nvoc_exports import mapping,region
import capstone

data=read_artifact(PATH)
assert hashlib.sha256(data).hexdigest()==EXPECTED
candidates=json.loads(read_artifact(sys.argv[1]))['encoding_candidates']
md=capstone.Cs(capstone.CS_ARCH_RISCV,capstone.CS_MODE_RISCV64|capstone.CS_MODE_RISCVC)
rows=[]
for candidate in candidates:
    address=int(candidate['firmware_elf_va'],16)
    raw,offset,_=region(data,mapping(data),address-128,132)
    instructions=list(md.disasm(raw,address-128))
    if not instructions or instructions[-1].address!=address:
        # Alternative halfword start may avoid an initial overlapping decode.
        instructions=list(md.disasm(raw[2:],address-126))
    refs=references(instructions)
    leads=[r for r in refs if r['kind']=='pc-relative-address' and
           (int.from_bytes(bytes.fromhex(r['raw_hex'])[:4],'little')>>7)&31==candidate['value_x_register']]
    rows.append({**candidate,'context_file_offset':hex(offset),'context_raw_hex':raw.hex(),
                 'last_decoded_va':hex(instructions[-1].address) if instructions else None,
                 'address_generation_leads':leads,
                 'instructions':[{'va':hex(i.address),'mnemonic':i.mnemonic,'operands':i.op_str,'raw_hex':i.bytes.hex()} for i in instructions]})
print(json.dumps({'artifact_sha256':EXPECTED,'contexts':rows,
    'limits':'Arbitrary halfword context starts, no function/CFG boundary proof or liveness validation; same-register address generation remains a candidate only.'},indent=2))

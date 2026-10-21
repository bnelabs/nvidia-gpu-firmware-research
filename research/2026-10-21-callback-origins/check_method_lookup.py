#!/usr/bin/env python3
"""Copied method binary search against every retained Subdevice export record."""
import hashlib,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'2026-10-21-pstate-writers'))
from export_ranges import PATH,EXPECTED
from offline_io import read_artifact
from extract_nvoc_exports import parse,mapping,region
from unicorn import Uc,UC_ARCH_RISCV,UC_MODE_RISCV64,UC_PROT_READ,UC_PROT_WRITE,UC_PROT_EXEC,UC_HOOK_CODE
from unicorn.riscv_const import UC_RISCV_REG_A0,UC_RISCV_REG_A1,UC_RISCV_REG_SP,UC_RISCV_REG_RA,UC_RISCV_REG_PC
import unicorn
data=read_artifact(PATH)
assert hashlib.sha256(data).hexdigest()==EXPECTED
metadata=parse(data,0x1c64e70)
uc=Uc(UC_ARCH_RISCV,UC_MODE_RISCV64)
for off,base,size,flags in mapping(data):
    uc.mem_map(base,size,UC_PROT_READ)
    uc.mem_write(base,data[off:off+size])
uc.mem_protect(0x18eb000,4096,UC_PROT_READ|UC_PROT_EXEC)
stack,sentinel=0x70000000,0x7fff0000
uc.mem_map(stack,4096,UC_PROT_READ|UC_PROT_WRITE)
uc.mem_map(sentinel,4096,UC_PROT_READ|UC_PROT_EXEC)

def guard(engine,address,size,_):
    if not 0x18eb54c<=address<0x18eb59e:
        raise ValueError('escaped copied method search '+hex(address))

uc.hook_add(UC_HOOK_CODE,guard)
lookup={int(m['command'],16):int(m['entry_firmware_elf_va'],16) for m in metadata['methods']}
misses=[0,0xffffffff]
commands=sorted(lookup)
misses += [a+1 for a,b in zip(commands,commands[1:]) if b>a+1][:16]
rows=[]
for command in commands+misses:
    for reg,value in ((UC_RISCV_REG_A0,0x1c62e38),(UC_RISCV_REG_A1,command),
                      (UC_RISCV_REG_SP,stack+0x800),(UC_RISCV_REG_RA,sentinel)):
        uc.reg_write(reg,value)
    uc.emu_start(0x18eb54c,sentinel,count=1024)
    assert uc.reg_read(UC_RISCV_REG_PC)==sentinel
    returned=uc.reg_read(UC_RISCV_REG_A0)
    assert returned==lookup.get(command,0),(command,returned)
    rows.append({'command':hex(command),'entry_firmware_elf_va':hex(returned),'expected_present':command in lookup})
segments=mapping(data)
class_bytes,off,_=region(data,segments,0x1c64e70,40)
cast_va=struct.unpack_from('<Q',class_bytes,24)[0]
count_bytes,_,_=region(data,segments,cast_va,8)
count=struct.unpack_from('<I',count_bytes)[0]
assert 0<count<64
cast_bytes,cast_off,_=region(data,segments,cast_va,8+8*count)
relatives=[]
for i in range(count):
    ptr=struct.unpack_from('<Q',cast_bytes,8+8*i)[0]
    raw,rtti_off,_=region(data,segments,ptr,24)
    class_va=struct.unpack_from('<Q',raw)[0]
    definition,definition_off,_=region(data,segments,class_va,40)
    relatives.append({'rtti_firmware_elf_va':hex(ptr),'rtti_file_offset':hex(rtti_off),'rtti_raw_hex':raw.hex(),
        'class_definition_firmware_elf_va':hex(class_va),'class_definition_file_offset':hex(definition_off),
        'class_definition_raw_hex':definition.hex(),'export_info_firmware_elf_va':hex(struct.unpack_from('<Q',definition,32)[0])})
print(json.dumps({'artifact_sha256':EXPECTED,'engine':'Unicorn '+unicorn.__version__,
    'helper_firmware_elf_va':'0x18eb54c','hits':len(commands),'misses':len(misses),'results':rows,
    'class_definition':{'firmware_elf_va':'0x1c64e70','file_offset':hex(off),'raw_hex':class_bytes.hex()},
    'cast_info':{'firmware_elf_va':hex(cast_va),'file_offset':hex(cast_off),'raw_hex':cast_bytes.hex(),'relatives':relatives},
    'limits':'Copied method search and immutable metadata only; no control invoked, hardware access, instantiated class proof, permissions or runtime availability.'},indent=2))

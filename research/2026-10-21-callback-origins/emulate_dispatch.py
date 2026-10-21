#!/usr/bin/env python3
"""Execute copied initializer, RUSD callback and metadata dispatch to the getter.

Only TLS/context swap is an opaque synthetic service. The RM API dispatch is
the target assigned by copied instructions, not a substituted routing stub.
Stops BEFORE the still-unresolved table-entry getter.
"""
import hashlib,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'2026-10-21-pstate-writers'))
from export_ranges import PATH,EXPECTED
from offline_io import read_artifact
from extract_nvoc_exports import mapping
from unicorn import Uc,UC_ARCH_RISCV,UC_MODE_RISCV64,UC_PROT_READ,UC_PROT_WRITE,UC_PROT_EXEC,UC_HOOK_CODE
from unicorn.riscv_const import UC_RISCV_REG_A0,UC_RISCV_REG_A1,UC_RISCV_REG_A2,UC_RISCV_REG_A3,UC_RISCV_REG_A4,UC_RISCV_REG_SP,UC_RISCV_REG_RA,UC_RISCV_REG_PC,UC_RISCV_REG_S4
import unicorn

data=read_artifact(PATH)
assert hashlib.sha256(data).hexdigest()==EXPECTED
uc=Uc(UC_ARCH_RISCV,UC_MODE_RISCV64)
for off,base,size,flags in mapping(data):
    assert not base&4095 and not size&4095
    uc.mem_map(base,size,UC_PROT_READ)
    uc.mem_write(base,data[off:off+size])
ranges=[(0x1aea74e,0x1aea7ec),(0x1c25af8,0x1c25c72),(0x143bde0,0x143be9a),
        (0x14078cc,0x1407c9e),(0x18eb54c,0x18eb59e),(0x16be978,0x16be9c6),(0x167de40,0x167de9e)]
for base in {start&~4095 for start,end in ranges}:
    uc.mem_protect(base,4096,UC_PROT_READ|UC_PROT_EXEC)
# Context swap is an explicit stopped service boundary, never executed.
uc.mem_protect(0x18e5000,4096,UC_PROT_READ|UC_PROT_EXEC)
gpu,timer,shared,subdev,parent,perf,table,stack,client,rtti,resource=[0x70000000+i*0x10000 for i in range(11)]
for base in (gpu,timer,shared,subdev,parent,perf,table,stack,client,rtti,resource):
    uc.mem_map(base,0x10000,UC_PROT_READ|UC_PROT_WRITE)
getter=0x7ffd0000
uc.mem_map(getter,4096,UC_PROT_READ|UC_PROT_EXEC)
uc.mem_write(getter,b'\x13\x00\x00\x00'*1024)
uc.reg_write(UC_RISCV_REG_S4,gpu)
uc.reg_write(UC_RISCV_REG_SP,stack+0x8000)
initialization_pcs,route_pcs,context_boundaries=[],[],[]
phase='initialization'

def guard(engine,address,size,_):
    if address in (getter,0x18e57ec):
        engine.emu_stop()
        return
    if not any(a<=address<b for a,b in ranges):
        raise ValueError('escaped copied code: '+hex(address))
    (initialization_pcs if phase=='initialization' else route_pcs).append(hex(address))

uc.hook_add(UC_HOOK_CODE,guard)
template=bytes(uc.mem_read(0x4193d10,240))
assert template==bytes(240)
uc.emu_start(0x1aea74e,0x1aea7ec,count=10000)
assert uc.reg_read(UC_RISCV_REG_PC)==0x1aea7ec
control=struct.unpack('<Q',bytes(uc.mem_read(gpu+0x41c0,8)))[0]
private_context=struct.unpack('<Q',bytes(uc.mem_read(gpu+0x4270,8)))[0]
assert control==0x14078cc and private_context==gpu
security_words=struct.unpack('<II',bytes(uc.mem_read(gpu+0x4240,8)))
assert security_words==(2,1)
initializer_result={'receiver_offset':'0x4188','assigned_control_target_firmware_elf_va':hex(control),
                    'synthetic_private_context_matches_gpu':True,'default_security_words_raw':list(security_words),
                    'retained_template':{'firmware_elf_va':'0x4193d10','file_offset':'0x1065d10',
                        'bytes':len(template),'raw_hex':template.hex(),'sha256':hashlib.sha256(template).hexdigest()},
                    'executed_firmware_elf_vas':initialization_pcs}
# Synthetic live-object substitutes. RTTI class definitions, casts, export tables
# and method records are copied firmware bytes; instance references are fixtures.
for address,value in ((gpu+0x4178,subdev),(gpu+0x4180,client),(subdev,rtti),
                       (rtti,0x1c64e70),(subdev+0x148,resource),(subdev+0x160,parent),
                       (parent+0xe8,gpu),(gpu+0x2000,perf),(perf+0x320,table),(table+0x38,getter)):
    uc.mem_write(address,struct.pack('<Q',value))
uc.mem_write(gpu+0x4154,struct.pack('<I',0x1234))
uc.mem_write(gpu+0x415c,struct.pack('<I',0x5678))
uc.mem_write(table+0x180,b'\xff\x00\x00\x07')
uc.mem_write(table+0x190,struct.pack('<II',3,2))
for reg,value in ((UC_RISCV_REG_A0,gpu),(UC_RISCV_REG_A1,timer),(UC_RISCV_REG_A2,shared+0x8e8),
                  (UC_RISCV_REG_A3,1),(UC_RISCV_REG_A4,2),(UC_RISCV_REG_SP,stack+0x8000),
                  (UC_RISCV_REG_RA,0x7ffe0000)):
    uc.reg_write(reg,value)
phase='dispatch'
start=0x143bde0
for _ in range(4):
    uc.emu_start(start,0,count=10000)
    pc=uc.reg_read(UC_RISCV_REG_PC)
    if pc==getter:
        break
    if pc!=0x18e57ec:
        raise ValueError('unresolved/budget boundary '+hex(pc))
    output=uc.reg_read(UC_RISCV_REG_A0)
    context_boundaries.append({'firmware_elf_va':hex(pc),'synthetic_old_context_output':hex(output),
                               'synthetic_new_context_pointer':hex(uc.reg_read(UC_RISCV_REG_A1)),
                               'action':'write synthetic old-context zero and return success; implementation not executed'})
    uc.mem_write(output,struct.pack('<Q',0))
    uc.reg_write(UC_RISCV_REG_A0,0)
    start=uc.reg_read(UC_RISCV_REG_RA)
else:
    raise ValueError('boundary budget exhausted')
assert uc.reg_read(UC_RISCV_REG_A0)==table and uc.reg_read(UC_RISCV_REG_A1)==7
for target in (0x14078cc,0x18eb54c,0x16be978,0x167de40):
    assert hex(target) in route_pcs
assert len(context_boundaries)==1
print(json.dumps({'artifact_sha256':EXPECTED,'engine':'Unicorn '+unicorn.__version__,
    'initializer_result':initializer_result,'request':{'control':'0x20802068','parameter_bytes':4,'poll_mask_fixture':2},
    'opaque_context_boundaries':context_boundaries,'executed_dispatch_firmware_elf_vas':route_pcs,
    'stopped_before_unresolved_entry_getter':{'fixture_pointer':hex(getter),'synthetic_receiver':hex(table),'remapped_index':7},
    'limits':'Copied initializer block entered with synthetic s4 GPU base. Real immutable metadata and assigned callback execute; object pointers/handles are synthetic. Context swap is stubbed. Stops before unknown entry getter: no payload origin, timestamp, actual scheduler, runtime pointer selection or hardware verified.'},indent=2))

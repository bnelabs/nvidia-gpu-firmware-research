#!/usr/bin/env python3
"""Copied schema setup and parsed-record construction; no data-transfer service.

The serialized table is a synthetic input at the stopped transfer boundary.
Only CPU heap allocation is substituted while executing the selected blocks.
"""
import hashlib,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'2026-10-21-pstate-writers'))
from export_ranges import PATH,EXPECTED
from offline_io import read_artifact
from extract_nvoc_exports import mapping
import unicorn
from unicorn import Uc,UC_ARCH_RISCV,UC_MODE_RISCV64,UC_PROT_READ,UC_PROT_WRITE,UC_PROT_EXEC,UC_HOOK_CODE
import unicorn.riscv_const as rv

data=read_artifact(PATH)
assert hashlib.sha256(data).hexdigest()==EXPECTED
ranges=[(0x1688876,0x168893a),(0x1767128,0x176723c),(0x17672d0,0x1767318),
        (0x1764294,0x1764350),(0x1688990,0x168899c),
        (0x1767a2c,0x1767a4c),(0x1767c28,0x1767d0a),
        (0x175fb8c,0x175fbb2),(0x175f270,0x175f2b2),(0x1ba12b4,0x1ba12fa),
        (0x1764048,0x176404e),(0x1764098,0x17640a8),(0x1760c24,0x1760c66),
        (0x17615d4,0x176162c),(0x17612a4,0x17612dc),
        (0x1768dd4,0x1768e10),(0x16870d4,0x1687120),(0x16871bc,0x168735a),
        (0x168780e,0x1687812),(0x17655b0,0x1765634),(0x1c25af8,0x1c25c72)]
uc=Uc(UC_ARCH_RISCV,UC_MODE_RISCV64)
for off,base,size,flags in mapping(data):
    uc.mem_map(base,size,UC_PROT_READ);uc.mem_write(base,data[off:off+size])
for page in {p for a,b in ranges for p in range(a&~4095,(b+4095)&~4095,4096)}|{0x18e2000}:
    uc.mem_protect(page,4096,UC_PROT_READ|UC_PROT_EXEC)
base=0x70000000
uc.mem_map(base,0x100000,UC_PROT_READ|UC_PROT_WRITE)
table,args,raw,mask,parsed,header1,header2,scratch,entry,stack=[base+i*0x10000 for i in range(10)]
interface=table+0x1e0
sentinel=0x7fff0000;uc.mem_map(sentinel,4096,UC_PROT_READ|UC_PROT_EXEC)
pcs=[];allocations=[];pending=[];stops=set()

def reg(name,value=None):
    key=getattr(rv,'UC_RISCV_REG_'+name.upper())
    if value is not None:uc.reg_write(key,value)
    return uc.reg_read(key)

def write(address,value,fmt='<Q'):uc.mem_write(address,struct.pack(fmt,value))
def read(address,fmt='<Q'):return struct.unpack(fmt,bytes(uc.mem_read(address,struct.calcsize(fmt))))[0]

def guard(engine,address,size,_):
    if address in stops or address==0x18e2c94:engine.emu_stop();return
    if not any(a<=address<b for a,b in ranges):raise ValueError('escaped copied code: '+hex(address))
    pcs.append(hex(address))
uc.hook_add(UC_HOOK_CODE,guard)

def run(start,stop=sentinel,**registers):
    global stops
    for k,v in dict(sp=stack+0x8000,ra=sentinel,**registers).items():reg(k,v)
    stops={stop};begin=len(pcs)
    for _ in range(6):
        uc.emu_start(start,stop,count=25000)
        if reg('pc')==stop:return {'start_va':hex(start),'stop_va':hex(stop),'executed_pcs':pcs[begin:]}
        assert reg('pc')==0x18e2c94,hex(reg('pc'))
        expected,output=pending.pop(0)
        assert reg('a1')==expected,(expected,reg('a1'))
        allocations.append({'opaque_allocator_va':'0x18e2c94','bytes':expected,'synthetic_result':hex(output)})
        reg('a0',output);start=reg('ra')
    raise ValueError('allocator boundary budget exhausted')

# Execute the copied constant setup and interface initializer through its schema
# stores. Other constructor fields are outside this bounded run.
write(args+0x28,args+0x1000);write(args+0x30,args+0x2000)
setup=run(0x1688876,0x1767318,s0=stack+0x9000,s3=args,a0=interface)
schema={'header_bytes':read(interface+0xc8,'<I'),'record_stride_bytes':read(interface+0xcc,'<I'),
        'source_selector':read(interface+0xd0,'<I'),'acquire_function_va':hex(read(interface+0x98)),
        'entry_wrapper_va':hex(read(interface+0xa8))}
assert schema=={'header_bytes':20,'record_stride_bytes':556,'source_selector':6,
                'acquire_function_va':'0x176b2a8','entry_wrapper_va':'0x1768dd4'}
assignment=run(0x1688990,0x168899c,s4=interface)
assert read(interface+0xf0)==0x16870d4

# The raw table is an explicit fixture AFTER the unexecuted transfer. Format
# byte 1 selects the copied 32-bit mask branch (raw jump-table case 1).
# Record indices 0 and 2 exist;
# index 1 is absent. Values deliberately remain raw.
size=schema['header_bytes']+3*schema['record_stride_bytes']
fixture=bytearray(size);fixture[0]=1;struct.pack_into('<I',fixture,8,0b101)
for index,value in ((0,4),(2,256)):
    offset=schema['header_bytes']+index*schema['record_stride_bytes']
    fixture[offset]=8;struct.pack_into('<I',fixture,offset+12,value)
uc.mem_write(raw,bytes(fixture))
pending[:]=[(12,mask),(64,parsed),(8,header1),(8,header2)]
parser=run(0x1767a2c,0x1767d08,s3=raw,s2=interface,s8=args+0x3000,s9=args+0x3008,s11=args+0x3010)
assert not pending and read(args+0x3000)==parsed
assert read(parsed+0x28)==0x17615d4 and read(parsed+8)==raw
assert read(parsed+0x38,'<I')==20 and read(parsed+0x3c,'<I')==556
assert read(parsed+0x30)==mask and read(parsed+0x10,'<H')==3
cases=[]
for index in (0,1,2):
    output=args+0x3100;write(output,0xa5a5a5a5)
    getter=run(0x17615d4,a0=parsed,a1=output,a2=index)
    ptr=read(output);expected=raw+20+556*index if index!=1 else 0
    assert reg('a0')==0 and ptr==expected
    result={'record_index':index,'returned_record_pointer':hex(ptr),'expected_pointer':hex(expected),'getter':getter}
    if ptr:
        pending[:]=[(0xa98,scratch),(0x10c0,entry)]
        constructor=run(0x1768dd4,0x1687358,a0=interface,a1=args+0x3200,a2=args,
                        a3=parsed,a4=header1,a5=output)
        assert not pending and reg('s11')==entry
        assert read(entry+0x34,'<I')==read(ptr+12,'<I')
        result.update({'record_tag':read(ptr,'<B'),'record_u32_at_0xc':read(ptr+12,'<I'),
                       'entry_u32_at_0x34':read(entry+0x34,'<I'),'constructor_prefix':constructor})
    cases.append(result)

print(json.dumps({'artifact_path':PATH,'artifact_bytes':len(data),'artifact_sha256':EXPECTED,
    'engine':'Unicorn '+unicorn.__version__,'address_domain':'firmware ELF VA; 0x700... pointers are synthetic',
    'schema':schema,'schema_initialization':setup,'entry_callback_assignment':assignment,
    'synthetic_serialized_table':{'bytes':len(fixture),'sha256':hashlib.sha256(fixture).hexdigest(),
                                  'raw_hex':fixture.hex(),'present_index_bits':5},
    'parsed_object_creation':parser,'parsed_getter_va':'0x17615d4','record_cases':cases,
    'allocator_substitutions':allocations,
    'limits':'The raw serialized table is a fixture supplied after transfer; 0x17776c4 and its memory-descriptor/transfer services are NOT executed or replaced with claimed hardware semantics. Copied schema setup, one mask-format parser branch, record pointer arithmetic and tag-8 constructor prefix execute. No real source bytes, source object identity, runtime selection, complete validation, physical read or vulnerability is established.'},indent=2))

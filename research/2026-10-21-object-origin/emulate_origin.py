#!/usr/bin/env python3
"""Bounded copied RV64 blocks for construction, entry copying and lookup.

All instance memory is synthetic. Only a CPU heap allocator is substituted.
Diagnostics and opaque factory/parser services are stopped before execution.
Run through scripts/run_cpu_only.sh; never load or execute firmware natively.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / '2026-10-21-pstate-writers'))
from export_ranges import PATH, EXPECTED
from extract_nvoc_exports import mapping
from offline_io import read_artifact
import unicorn
from unicorn import Uc, UC_ARCH_RISCV, UC_MODE_RISCV64, UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC, UC_HOOK_CODE
import unicorn.riscv_const as rv

DATA = read_artifact(PATH)
assert hashlib.sha256(DATA).hexdigest() == EXPECTED
RANGES = [
    (0x140dfd6, 0x140dfee), (0x1688714, 0x168893a),
    (0x1b0a460, 0x1b0a52c), (0x1b0a2c0, 0x1b0a38a),
    (0x175fb8c, 0x175fbb2), (0x167e4e0, 0x167e506),
    (0x1c25af8, 0x1c25c72), (0x1be970a, 0x1be9712),
    (0x16870d4, 0x168735a), (0x168780e, 0x1687812), (0x17655b0, 0x1765634),
    (0x1680c20, 0x1680ca8), (0x17610dc, 0x1761154),
    (0x1760fd0, 0x1761006), (0x16be978, 0x16be9c6),
    (0x167de40, 0x167de9e), (0x1757ea0, 0x1757efc + 2),
]
GPU, PERF, KPERF, ARGS, ENTRY, INPUT, TABLE, STACK, SUBDEV, PARENT, SCRATCH = [
    0x70000000 + i * 0x10000 for i in range(11)]
SENTINEL = 0x7fff0000


class Machine:
    def __init__(self):
        self.uc = Uc(UC_ARCH_RISCV, UC_MODE_RISCV64)
        for off, base, size, flags in mapping(DATA):
            self.uc.mem_map(base, size, UC_PROT_READ)
            self.uc.mem_write(base, DATA[off:off+size])
        for page in {p for a,b in RANGES for p in range(a & ~4095, (b+4095) & ~4095, 4096)} | {
                0x18e2000, 0x1407000, SENTINEL}:
            if page == SENTINEL:
                self.uc.mem_map(page, 4096, UC_PROT_READ | UC_PROT_EXEC)
            else:
                self.uc.mem_protect(page, 4096, UC_PROT_READ | UC_PROT_EXEC)
        for base in (GPU, PERF, KPERF, ARGS, ENTRY, INPUT, TABLE, STACK, SUBDEV, PARENT, SCRATCH):
            self.uc.mem_map(base, 0x10000, UC_PROT_READ | UC_PROT_WRITE)
        self.pcs, self.allocations, self.boundaries = [], [], set()
        self.uc.hook_add(UC_HOOK_CODE, self.guard)

    def reg(self, name, value=None):
        key = getattr(rv, 'UC_RISCV_REG_' + name.upper())
        if value is not None:
            self.uc.reg_write(key, value)
        return self.uc.reg_read(key)

    def write(self, address, value, fmt='<Q'):
        self.uc.mem_write(address, struct.pack(fmt, value))

    def read(self, address, fmt='<Q'):
        return struct.unpack(fmt, bytes(self.uc.mem_read(address, struct.calcsize(fmt))))[0]

    def guard(self, engine, address, size, _):
        if address in self.boundaries or address == 0x18e2c94:
            engine.emu_stop()
            return
        # Successful getter bytes only; never enter assertion/logging/MMIO paths.
        if 0x1757eb4 <= address < 0x1757ede:
            raise ValueError('unexpected diagnostic path: ' + hex(address))
        if not any(a <= address < b for a,b in RANGES):
            raise ValueError('escaped copied code: ' + hex(address))
        self.pcs.append(hex(address))

    def run(self, start, stop=SENTINEL, **registers):
        for name, value in dict(sp=STACK+0xf000, ra=SENTINEL, **registers).items():
            self.reg(name, value)
        self.boundaries = {stop}
        before = len(self.pcs)
        for _ in range(3):
            self.uc.emu_start(start, stop, count=20000)
            pc = self.reg('pc')
            if pc == stop:
                return {'start_firmware_elf_va': hex(start), 'stop_va': hex(stop),
                        'executed_pcs': self.pcs[before:]}
            if pc != 0x18e2c94:
                raise ValueError('instruction budget or unhandled stop: ' + hex(pc))
            size = self.reg('a1')
            allocation = {0x4c0: TABLE, 0xa98: SCRATCH, 0x10c0: ENTRY}.get(size)
            assert allocation is not None, hex(size)
            self.allocations.append({'opaque_allocator_firmware_elf_va': hex(pc),
                                     'requested_bytes': size, 'synthetic_return_pointer': hex(allocation)})
            self.reg('a0', allocation)
            start = self.reg('ra')
        raise ValueError('allocator boundary budget exceeded')


machine = Machine()
child = machine.run(0x140dfd6, 0x1407d4c, s1=GPU, s2=0x2000)
child['captured_arguments'] = {x: hex(machine.reg(x)) for x in ('a0','a1','a2','a3')}
assert [machine.reg(x) for x in ('a0','a1','a2','a3')] == [GPU, 0xed0b65, 0, GPU+0x2000]

# Select one explicitly synthetic feature branch. This does not identify a SKU.
machine.write(GPU+0x20b8, KPERF)
machine.write(KPERF+0x78b, 1, '<B')
for address,value in ((ARGS+8,GPU),(ARGS+0x10,PERF),(ARGS+0x18,INPUT),(ARGS+0x20,SCRATCH)):
    machine.write(address, value)
construction = machine.run(0x1688714, 0x1688932, a0=SCRATCH, a1=ARGS)
assert machine.read(TABLE+0x38) == 0x1757ea0
assert machine.read(TABLE+8) == TABLE+0x60
assert machine.read(TABLE+0x18, '<H') == 32
assert machine.read(TABLE+0x180, '<B') == 0x50
assert machine.reg('a0') == TABLE+0x1e0
construction.update({'getter_firmware_elf_va': hex(machine.read(TABLE+0x38)),
                     'pointer_array': hex(machine.read(TABLE+8)),
                     'array_capacity': machine.read(TABLE+0x18, '<H'),
                     'type_raw': machine.read(TABLE+0x180, '<B'),
                     'stopped_before_interface_constructor': hex(machine.reg('pc')),
                     'initial_table_bytes_hex': bytes(machine.uc.mem_read(TABLE,0x4c0)).hex()})

# Execute the exact install tail with the same table as an explicit factory result.
# The intervening full factory, parsing and scheduling are NOT emulated here.
machine.write(STACK+0xe000-0xf8, TABLE)
install = machine.run(0x1be970a, 0x1be9712, s0=STACK+0xe000, s1=PERF)
assert machine.read(PERF+0x320) == TABLE

# Common instance graph: the firmware consumer's pointers are fixtures.
for address,value in ((SUBDEV+0x160,PARENT),(PARENT+0xe8,GPU),(GPU+0x2000,PERF)):
    machine.write(address,value)
cases=[]
# Full interface initialization stopped above. Its descriptor pointer is an
# explicit fixture here, using the copied descriptor passed by that initializer.
machine.write(TABLE+0x1e0,0x1ecb278)
for raw in (1,4,256,3,0x80000000):
    m=machine
    m.write(INPUT,8,'<B')
    m.write(INPUT+0xc,raw,'<I')
    writer=m.run(0x16870d4,0x1687358,a0=TABLE+0x1e0,a1=ARGS+0x1000,a2=ARGS,a3=INPUT)
    assert m.read(SCRATCH+4,'<I')==raw
    assert m.reg('s11')==ENTRY
    assert m.read(ENTRY+0x34,'<I')==raw
    assert m.read(ENTRY+0x30,'<B')==raw.bit_length()-1
    # Reset insertion prerequisites for this independent synthetic entry.
    m.write(TABLE+0x18c,0,'<I')
    m.write(TABLE+0x1a,0xffff,'<H')
    m.write(TABLE+0x60+7*8,0)
    assert m.read(ENTRY+2,'<H')==0xffff
    insertion=m.run(0x1680c20,a0=TABLE,a1=ENTRY,a2=7)
    assert m.reg('a0')==0
    assert m.read(TABLE+0x60+7*8)==ENTRY
    assert m.read(TABLE+0x181,'<B')==7 and m.read(TABLE+0x190,'<I')==0
    assert m.read(ENTRY+2,'<H')==7
    # Current-index selection is outside this bounded experiment.
    m.write(TABLE+0x194,0,'<I')
    m.write(PERF+0x2d7,0,'<B')
    m.write(ARGS+0x800,0xa5a5a5a5,'<I')
    handler=m.run(0x16be978,a0=SUBDEV,a1=ARGS+0x800)
    assert m.reg('a0')==0 and m.read(ARGS+0x800,'<I')==raw
    assert '0x1757ea0' in handler['executed_pcs']
    cases.append({'input_record_u32_at_0xc':raw,'entry_u32_at_0x34':m.read(ENTRY+0x34,'<I'),
                  'computed_byte_at_0x30':m.read(ENTRY+0x30,'<B'),
                  'mapped_slot':7,'synthetic_current_index':0,'returned_u32':m.read(ARGS+0x800,'<I'),
                  'tag_8_entry_constructor_prefix':writer,'insertion':insertion,'handler_lookup_getter':handler})

# Unavailable gate and an out-of-range logical index return without calling getter.
negative=[]
for name,gate,index,expected in [('disabled',1,0,0x56),('logical_index_above_count',0,1,0x40)]:
    machine.write(PERF+0x2d7,gate,'<B')
    machine.write(TABLE+0x194,index,'<I')
    machine.write(ARGS+0x800,0xa5a5a5a5,'<I')
    trace=machine.run(0x16be978,a0=SUBDEV,a1=ARGS+0x800)
    assert machine.reg('a0')==expected and machine.read(ARGS+0x800,'<I')==0xa5a5a5a5
    assert '0x1757ea0' not in trace['executed_pcs']
    negative.append({'case':name,'status_raw':expected,'output_unchanged':True,'trace':trace})

print(json.dumps({'artifact_path':PATH,'artifact_bytes':len(DATA),'artifact_sha256':EXPECTED,
    'engine':'Unicorn '+unicorn.__version__, 'address_domain':'copied firmware ELF VA; all 0x700... instance pointers synthetic',
    'gpu_child_arguments':child,'table_constructor_prefix':construction,'allocator_substitutions':machine.allocations,
    'table_install_tail':install,'cases':cases,'negative_cases':negative,
    'limits':'Separate bounded blocks, not complete boot/factory/parser execution. Feature flags, GPU/object pointers, factory result, interface descriptor pointer, CPU heap allocations, tagged input records, guard clear and current-index selection are fixtures. Tag-8 entry constructor prefix, insertion, lookup and getter execute copied code; entry construction stops before the next component getter at 0x1687358. No physical read or runtime measurement is proved.'},indent=2))

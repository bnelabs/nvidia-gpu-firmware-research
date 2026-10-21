#!/usr/bin/env python3
"""Copied writer/direct handler/publisher, with explicit synthetic boundaries.

No firmware boot, native execution, host syscall or hardware access. RM API
dispatch, indirect entry getter and timestamp source are fixture adapters.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from export_ranges import PATH, EXPECTED
from emulate_pstate_conversion import va_bytes
from offline_io import read_artifact
from unicorn import Uc, UC_ARCH_RISCV, UC_MODE_RISCV64, UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.riscv_const import UC_RISCV_REG_A0, UC_RISCV_REG_A1, UC_RISCV_REG_A2, UC_RISCV_REG_A3, UC_RISCV_REG_A4, UC_RISCV_REG_A5, UC_RISCV_REG_SP, UC_RISCV_REG_RA, UC_RISCV_REG_PC
import unicorn

data = read_artifact(PATH)
assert hashlib.sha256(data).hexdigest() == EXPECTED
cases = [
    ('raw-P2', 2, 1, 4, True, 0, 123456),
    ('raw-P8', 2, 1, 256, True, 0, 123456),
    ('timestamp-one', 2, 1, 4, True, 0, 1),
    ('raw-composite-preserved', 2, 1, 3, True, 0, 123456),
    ('direct-entry-missing', 2, 1, 4, False, 0, 123456),
    ('RM-error', 2, 1, 4, True, 0x56, 123456),
    ('mask-off-invalidate', 0, 0, 4, True, 0, 123456),
    ('mask-off-retain', 0, 1, 4, True, 0, 123456),
]
results = []
allowed = [(0x143bde0, 0x143be9a), (0x1434cdc, 0x1434d90),
           (0x16be978, 0x16be9c6), (0x167de40, 0x167de9e),
           (0x1c25af8, 0x1c25c72), (0x18dd358, 0x18dd4b8)]
for name, mask, refresh, raw_value, found, rm_error, timestamp in cases:
    uc = Uc(UC_ARCH_RISCV, UC_MODE_RISCV64)
    for base in sorted({a & ~4095 for a, _ in allowed}):
        raw, _ = va_bytes(data, base, 4096)
        uc.mem_map(base, 4096, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_write(base, raw)
    # Copied stack canary and memset's repeated-byte multiplier; data only.
    for base in (0x4193000, 0x1ed0000):
        raw, _ = va_bytes(data, base, 4096)
        uc.mem_map(base, 4096, UC_PROT_READ)
        uc.mem_write(base, raw)
    uc.mem_map(0x41ae000, 4096, UC_PROT_READ | UC_PROT_WRITE)
    uc.mem_write(0x41ae3c0, b'\x01')  # Fixture skips unresolved special-instruction probes.
    gpu, timer, shared, subdev, parent, perf, table, entry = [0x70000000 + i*0x10000 for i in range(8)]
    for base in (gpu, timer, shared, subdev, parent, perf, table, entry):
        uc.mem_map(base, 0x10000, UC_PROT_READ | UC_PROT_WRITE)
    stack = 0x70100000
    uc.mem_map(stack, 0x10000, UC_PROT_READ | UC_PROT_WRITE)
    sentinel, dispatch, getter, clock = [0x7fff0000 - i*0x10000 for i in range(4)]
    for base in (sentinel, dispatch, getter, clock):
        uc.mem_map(base, 4096, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_write(base, b'\x13\x00\x00\x00'*1024)
    for address, value in ((gpu+0x41c0, dispatch), (timer+0x1a8, clock),
                           (subdev+0x160, parent), (parent+0xe8, gpu),
                           (gpu+0x2000, perf), (perf+0x320, table), (table+0x38, getter)):
        uc.mem_write(address, struct.pack('<Q', value))
    uc.mem_write(gpu+0x4154, struct.pack('<I', 0x1234))
    uc.mem_write(gpu+0x415c, struct.pack('<I', 0x5678))
    uc.mem_write(table+0x180, b'\xff\x00\x00\x07')
    uc.mem_write(table+0x190, struct.pack('<II', 3, 2))
    uc.mem_write(entry+0x34, struct.pack('<I', raw_value))
    record = shared+0x8e8
    uc.mem_write(record-8, bytes.fromhex('1122334455667788'))
    uc.mem_write(record, struct.pack('<QII', 777, 99, 0xaabbccdd))
    uc.mem_write(record+16, bytes.fromhex('8877665544332211'))
    for reg, value in ((UC_RISCV_REG_A0, gpu), (UC_RISCV_REG_A1, timer),
                        (UC_RISCV_REG_A2, record), (UC_RISCV_REG_A3, refresh),
                        (UC_RISCV_REG_A4, mask), (UC_RISCV_REG_SP, stack+0x8000),
                        (UC_RISCV_REG_RA, sentinel)):
        uc.reg_write(reg, value)
    executed, boundaries, writes = [], [], []

    def guard(engine, address, size, _):
        if address in (dispatch, getter, clock):
            engine.emu_stop()
            return
        if not any(start <= address < end for start, end in allowed):
            raise ValueError('unexpected firmware PC: '+hex(address))
        executed.append(hex(address))

    def record_write(engine, access, address, size, value, _):
        if record <= address < record+16:
            writes.append({'instruction_firmware_elf_va': hex(engine.reg_read(UC_RISCV_REG_PC)),
                           'record_offset': address-record, 'bytes': size,
                           'value_raw_hex': hex(value & ((1 << (size*8))-1))})

    uc.hook_add(UC_HOOK_CODE, guard)
    uc.hook_add(UC_HOOK_MEM_WRITE, record_write)
    start = 0x143bde0
    for _ in range(8):
        uc.emu_start(start, sentinel, count=10000)
        pc = uc.reg_read(UC_RISCV_REG_PC)
        if pc == sentinel:
            break
        return_pc = uc.reg_read(UC_RISCV_REG_RA)
        if pc == dispatch:
            args = [uc.reg_read(r) for r in (UC_RISCV_REG_A0, UC_RISCV_REG_A1, UC_RISCV_REG_A2, UC_RISCV_REG_A3, UC_RISCV_REG_A4, UC_RISCV_REG_A5)]
            assert args[:4] == [gpu+0x4188, 0x1234, 0x5678, 0x20802068] and args[5] == 4
            boundaries.append({'boundary': 'synthetic RM API dispatch', 'args_raw': [hex(v) for v in args],
                               'action': 'return synthetic error' if rm_error else 'route to copied handler 0x16be978'})
            if rm_error:
                uc.reg_write(UC_RISCV_REG_A0, rm_error)
                start = return_pc
            else:
                uc.reg_write(UC_RISCV_REG_A0, subdev)
                uc.reg_write(UC_RISCV_REG_A1, args[4])
                start = 0x16be978
        elif pc == getter:
            assert uc.reg_read(UC_RISCV_REG_A0) == table and uc.reg_read(UC_RISCV_REG_A1) == 7
            boundaries.append({'boundary': 'synthetic table entry getter', 'found': found,
                               'entry_value_raw_u32': raw_value if found else None})
            uc.reg_write(UC_RISCV_REG_A0, entry if found else 0)
            start = return_pc
        elif pc == clock:
            assert uc.reg_read(UC_RISCV_REG_A0) == timer
            uc.mem_write(uc.reg_read(UC_RISCV_REG_A1), struct.pack('<Q', timestamp))
            boundaries.append({'boundary': 'synthetic timestamp source', 'timestamp_raw_u64': timestamp})
            start = return_pc
        else:
            raise ValueError('instruction budget or unresolved boundary at '+hex(pc))
    else:
        raise ValueError('boundary budget exhausted')
    assert uc.reg_read(UC_RISCV_REG_PC) == sentinel
    output = bytes(uc.mem_read(record, 16))
    ts, value, padding = struct.unpack('<QII', output)
    success = mask == 2 and not rm_error and found
    assert ts == (timestamp if success else 777 if not mask and refresh else 0)
    assert value == (raw_value if success else 99)
    assert padding == (0 if success else 0xaabbccdd)
    assert bytes(uc.mem_read(record-8, 8)).hex() == '1122334455667788'
    assert bytes(uc.mem_read(record+16, 8)).hex() == '8877665544332211'
    if success:
        assert writes[0]['record_offset']==0 and writes[0]['value_raw_hex']=='0xffffffffffffffff'
        assert writes[-1]['record_offset']==0 and int(writes[-1]['value_raw_hex'],16)==timestamp
    results.append({'case': name, 'fixture_mask': mask, 'fixture_refresh': refresh,
                    'record_after_raw_hex': output.hex(), 'timestamp_raw_u64': ts,
                    'value_raw_u32': value, 'canaries_preserved': True,
                    'record_writes': writes, 'synthetic_boundaries': boundaries,
                    'executed_firmware_elf_vas': executed})
print(json.dumps({'artifact_sha256': EXPECTED, 'engine': 'Unicorn '+unicorn.__version__,
                  'entry_firmware_elf_va': '0x143bde0', 'synthetic_cases': results,
                  'limits': 'RM API dispatch routing, entry getter, timestamp and feature-flag state are synthetic. Actual copied writer/handler/lookup/publisher/memory utility instructions run. No hardware, live data, actual scheduler or concrete runtime dispatch/getter provenance verified.'}, indent=2))

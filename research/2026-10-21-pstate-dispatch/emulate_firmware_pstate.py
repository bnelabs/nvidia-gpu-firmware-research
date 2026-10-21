#!/usr/bin/env python3
"""Execute copied P-state handler/lookup with synthetic objects and one stub.

The unresolved indirect getter is replaced by a clearly marked synthetic return;
it is never executed. This checks pointer/field flow, not value provenance.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from offline_io import read_artifact
from emulate_pstate_conversion import va_bytes
from unicorn import Uc, UC_ARCH_RISCV, UC_MODE_RISCV64, UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC, UC_HOOK_CODE
from unicorn.riscv_const import UC_RISCV_REG_A0, UC_RISCV_REG_A1, UC_RISCV_REG_SP, UC_RISCV_REG_RA, UC_RISCV_REG_PC
import unicorn

expected = '4ac95cbbe55b5e61572053d0c8a410b4de7693eaa2881d1878c76b6405426f2a'
data = read_artifact('firmware-store/gsp-kernels/615-kernel-10.elf')
assert hashlib.sha256(data).hexdigest() == expected
cases = [
    ('missing-perf', False, 0, 3, 2, 0xff, False, 0x56),
    ('disabled-perf', True, 1, 3, 2, 0xff, False, 0x56),
    ('index-exceeds-count', True, 0, 1, 2, 0xff, False, 0x40),
    ('index-exceeds-nine', True, 0, 12, 10, 0xff, False, 0x40),
    ('count-eleven', True, 0, 11, 2, 0xff, False, 0x40),
    ('rejected-type', True, 0, 3, 2, 0x10, False, 0x40),
    ('synthetic-getter-null', True, 0, 3, 2, 0xff, False, 0x40),
    ('synthetic-getter-entry', True, 0, 3, 2, 0xff, True, 0),
]
results = []
for name, present, disabled, count, index, kind, getter_entry, expected_status in cases:
    uc = Uc(UC_ARCH_RISCV, UC_MODE_RISCV64)
    for base in (0x16be000, 0x167d000):
        raw, _ = va_bytes(data, base, 4096)
        uc.mem_map(base, 4096, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_write(base, raw)
    subdevice, parent, gpu, perf, table, entry, output, stack = [0x70000000 + i * 0x10000 for i in range(8)]
    for base in (subdevice, parent, gpu, perf, table, entry, output, stack):
        uc.mem_map(base, 0x10000, UC_PROT_READ | UC_PROT_WRITE)
    sentinel, getter = 0x7fff0000, 0x7ffe0000
    for base in (sentinel, getter):
        uc.mem_map(base, 4096, UC_PROT_READ | UC_PROT_EXEC)
        # Valid stop-page instructions let Unicorn deliver the hook before
        # execution. No stop-page instruction is part of the copied firmware.
        uc.mem_write(base, b'\x13\x00\x00\x00' * 1024)
    for address, value in ((subdevice + 0x160, parent), (parent + 0xe8, gpu),
                           (gpu + 0x2000, perf if present else 0), (perf + 0x320, table),
                           (table + 0x38, getter)):
        uc.mem_write(address, struct.pack('<Q', value))
    uc.mem_write(perf + 0x2d7, bytes([disabled]))
    uc.mem_write(table + 0x180, bytes([kind]))
    uc.mem_write(table + 0x181 + index, b'\x07')
    uc.mem_write(table + 0x190, struct.pack('<II', count, index))
    uc.mem_write(entry + 0x34, struct.pack('<I', 4))
    uc.mem_write(output, struct.pack('<III', 0xaabbccdd, 0xdeadbeef, 0x11223344))
    uc.reg_write(UC_RISCV_REG_A0, subdevice)
    uc.reg_write(UC_RISCV_REG_A1, output + 4)
    uc.reg_write(UC_RISCV_REG_SP, stack + 0x8000)
    uc.reg_write(UC_RISCV_REG_RA, sentinel)
    executed, stubs = [], []

    def guard(engine, address, size, _):
        if address == getter:
            stubs.append({'synthetic_receiver': hex(engine.reg_read(UC_RISCV_REG_A0)),
                          'mapped_index_argument': engine.reg_read(UC_RISCV_REG_A1),
                          'synthetic_return_pointer': hex(entry if getter_entry else 0)})
            engine.emu_stop()
            return
        if not (0x16be978 <= address < 0x16be9c6 or 0x167de40 <= address < 0x167de9e):
            raise ValueError('escaped bounded firmware code: ' + hex(address))
        executed.append(hex(address))

    uc.hook_add(UC_HOOK_CODE, guard)
    try:
        uc.emu_start(0x16be978, sentinel, count=1024)
        if uc.reg_read(UC_RISCV_REG_PC) == getter:
            uc.reg_write(UC_RISCV_REG_A0, entry if getter_entry else 0)
            resume = uc.reg_read(UC_RISCV_REG_RA)
            uc.reg_write(UC_RISCV_REG_PC, resume)
            uc.emu_start(resume, sentinel, count=1024)
    except Exception as error:
        raise RuntimeError(name + ' stopped at ' + hex(uc.reg_read(UC_RISCV_REG_PC))) from error
    assert uc.reg_read(UC_RISCV_REG_PC) == sentinel
    status = uc.reg_read(UC_RISCV_REG_A0)
    before, value, after = struct.unpack('<III', bytes(uc.mem_read(output, 12)))
    assert status == expected_status and before == 0xaabbccdd and after == 0x11223344
    assert value == (4 if status == 0 else 0xdeadbeef)
    assert len(stubs) == int(name.startswith('synthetic-getter'))
    if stubs:
        assert stubs[0]['synthetic_receiver'] == hex(table) and stubs[0]['mapped_index_argument'] == 7
    results.append({'case': name, 'status_raw': status, 'output_raw_u32': value,
                    'output_canaries_preserved': True, 'synthetic_getter_stub': stubs,
                    'executed_firmware_elf_vas': executed})
print(json.dumps({'artifact_sha256': expected, 'engine': 'Unicorn ' + unicorn.__version__,
                  'entry_firmware_elf_va': '0x16be978', 'status': 'source-decoded',
                  'synthetic_cases': results,
                  'limits': 'Only copied handler/lookup instructions execute. Unknown indirect getter is a synthetic stub. Object layouts are fixture inputs; no physical source, runtime selection, complete type bitmap, register or sensor semantics verified.'}, indent=2))

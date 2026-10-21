#!/usr/bin/env python3
"""Execute two bounded RISC-V control branches with synthetic objects only.

This does not load or boot firmware. Unknown external calls/PCs fail closed.
Only branches that need no scheduler, MMIO or firmware service are exercised.
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
results = []
for old_interval, new_interval in ((500, 500), (200, 500)):
    uc = Uc(UC_ARCH_RISCV, UC_MODE_RISCV64)
    code, _ = va_bytes(data, 0x1447000, 4096)
    uc.mem_map(0x1447000, 4096, UC_PROT_READ | UC_PROT_EXEC)
    uc.mem_write(0x1447000, code)
    subdevice, parent, gpu, params, stack, sentinel = 0x70000000, 0x70001000, 0x70010000, 0x70020000, 0x70030000, 0x7fff0000
    for address, size in ((subdevice, 8192), (gpu, 0x6000), (params, 4096), (stack, 4096)):
        uc.mem_map(address, size, UC_PROT_READ | UC_PROT_WRITE)
    uc.mem_map(sentinel, 4096, UC_PROT_READ | UC_PROT_EXEC)
    uc.mem_write(subdevice + 0x160, struct.pack('<Q', parent))
    uc.mem_write(parent + 0xe8, struct.pack('<Q', gpu))
    uc.mem_write(gpu + 0x42bc, struct.pack('<I', old_interval))
    uc.mem_write(gpu + 0x42a8, struct.pack('<Q', 2))
    uc.mem_write(gpu + 0x4f40, struct.pack('<Q', 0))
    uc.mem_write(params, struct.pack('<QII', 2, new_interval, 0))
    uc.reg_write(UC_RISCV_REG_A0, subdevice)
    uc.reg_write(UC_RISCV_REG_A1, params)
    uc.reg_write(UC_RISCV_REG_SP, stack + 0x800)
    uc.reg_write(UC_RISCV_REG_RA, sentinel)
    executed = []

    def guard(engine, address, size, _):
        if not 0x1447ac8 <= address < 0x1447b50:
            raise ValueError('escaped bounded firmware branch: ' + hex(address))
        executed.append(address)

    uc.hook_add(UC_HOOK_CODE, guard)
    uc.emu_start(0x1447ac8, sentinel, count=512)
    assert uc.reg_read(UC_RISCV_REG_PC) == sentinel
    status = uc.reg_read(UC_RISCV_REG_A0)
    stored_interval = struct.unpack('<I', bytes(uc.mem_read(gpu + 0x42bc, 4)))[0]
    assert status == 0 and stored_interval == new_interval
    results.append({'old_interval_synthetic': old_interval, 'new_interval_synthetic': new_interval,
                    'mask_synthetic': 2, 'scheduler_object_synthetic': 0,
                    'status_raw': status, 'stored_interval': stored_interval,
                    'executed_firmware_vas': [hex(x) for x in executed]})

print(json.dumps({'artifact_sha256': expected, 'engine': 'Unicorn ' + unicorn.__version__,
                  'entry_firmware_elf_va': '0x1447ac8', 'status': 'source-decoded',
                  'synthetic_cases': results,
                  'limits': 'Object pointers, masks and intervals are synthetic. This only checks the no-scheduler branch, not RPC dispatch, live polling, timing, hardware behavior or the shared-data writer.'}, indent=2))

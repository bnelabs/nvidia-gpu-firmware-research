#!/usr/bin/env python3
"""Feed synthetic firmware writer output bytes to copied x86 NVML reader.

Input is an offline writer-emulation JSON file, never a device or service.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from offline_io import read_artifact
from emulate_pstate_conversion import EXPECTED, va_bytes
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RDI, UC_X86_REG_RSI, UC_X86_REG_RDX, UC_X86_REG_RSP, UC_X86_REG_RIP, UC_X86_REG_RAX
import unicorn

host_path = 'firmware-store/gsp-kernels/libnvidia-ml-615.71.09.so'
data = read_artifact(host_path)
assert hashlib.sha256(data).hexdigest() == EXPECTED
input_bytes = read_artifact(sys.argv[1])
writer = json.loads(input_bytes)
assert writer['artifact_sha256'] == '4ac95cbbe55b5e61572053d0c8a410b4de7693eaa2881d1878c76b6405426f2a'
results = []
for case in writer['synthetic_cases']:
    record = bytes.fromhex(case['record_after_raw_hex'])
    assert len(record) == 16
    uc = Uc(UC_ARCH_X86, UC_MODE_64)
    for base in (0xf1000, 0xf3000, 0x37000, 0x246000):
        raw, _ = va_bytes(data, base, 4096)
        uc.mem_map(base, 4096, UC_PROT_READ | (UC_PROT_EXEC if base != 0x246000 else 0))
        uc.mem_write(base, raw)
    device, shared, output, stack, sentinel = 0x70000000, 0x71000000, 0x72000000, 0x73000000, 0x7fff0000
    for base, length in ((device, 0x90000), (shared, 4096), (output, 4096), (stack, 0x10000), (0x153d000, 4096)):
        uc.mem_map(base, length, UC_PROT_READ | UC_PROT_WRITE)
    uc.mem_map(sentinel, 4096, UC_PROT_READ | UC_PROT_EXEC)
    uc.mem_write(device, b'\x01')
    uc.mem_write(device+0x8b728, struct.pack('<Q', 2))
    uc.mem_write(device+0x286c8, struct.pack('<I', 1))
    uc.mem_write(device+0x286c0, struct.pack('<Q', shared))
    uc.mem_write(shared+0x8e8, record)
    uc.mem_write(output, struct.pack('<III', 0xdeadbeef, 0xdeadbeef, 0xdeadbeef))
    uc.mem_write(stack+0x8000, struct.pack('<Q', sentinel))
    for reg, value in ((UC_X86_REG_RSP, stack+0x8000), (UC_X86_REG_RDI, 0x74000000),
                        (UC_X86_REG_RSI, device), (UC_X86_REG_RDX, output+4)):
        uc.reg_write(reg, value)
    pcs, attempts = [], []

    def guard(engine, address, size, _):
        if not any(a <= address < b for a,b in ((0xf32b0,0xf33b0),(0xf1b50,0xf1f70),(0x376e0,0x37720))):
            raise ValueError('escaped copied reader: '+hex(address))
        pcs.append(hex(address))
        if address == 0xf1e5e:
            attempts.append(address)

    uc.hook_add(UC_HOOK_CODE, guard)
    uc.emu_start(0xf32b0, sentinel, count=10000)
    assert uc.reg_read(UC_X86_REG_RIP) == sentinel
    status = uc.reg_read(UC_X86_REG_RAX) & 0xffffffff
    before, value, after = struct.unpack('<III', bytes(uc.mem_read(output,12)))
    assert before == after == 0xdeadbeef
    ts, raw_value, _ = struct.unpack('<QII', record)
    expected = (raw_value.bit_length()-1 if raw_value and not raw_value & (raw_value-1) and raw_value <= 0x8000 else 32)
    assert status == (0 if ts else 10)
    assert value == (expected if ts else 0xdeadbeef)
    assert len(attempts) == (1 if ts else 5)
    results.append({'writer_case':case['case'], 'synthetic_record_raw_hex':record.hex(),
                    'status_raw':status, 'output_ordinal_u32':value,
                    'output_canaries_preserved':True, 'snapshot_attempts':len(attempts),
                    'executed_host_elf_vas':pcs})
print(json.dumps({'host_artifact_sha256':EXPECTED, 'writer_input_sha256':hashlib.sha256(input_bytes).hexdigest(),
                  'engine':'Unicorn '+unicorn.__version__, 'synthetic_cases':results,
                  'limits':'Synthetic cross-ISA record compatibility only. No actual firmware mapping, coherence, runtime pointer selection, age guarantee, hardware measurement or subscription tested.'},indent=2))

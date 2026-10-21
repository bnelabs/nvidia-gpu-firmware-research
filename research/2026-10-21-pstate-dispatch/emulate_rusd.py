#!/usr/bin/env python3
"""Execute copied RUSD read/conversion instructions on synthetic CPU memory.

No native target execution, syscalls, device nodes, mappings of hardware, or
process attachment. Initialization and subscription state are pre-populated
synthetically. Escapes into driver communication or other code fail closed.
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

data = read_artifact('firmware-store/gsp-kernels/libnvidia-ml-615.71.09.so')
if hashlib.sha256(data).hexdigest() != EXPECTED:
    raise ValueError('refusing offsets for a different artifact')

CASES = [
    ('timestamp-one-is-valid', 1, 4, None, 0, 2),
    ('stable-P8', 123456, 256, None, 0, 8),
    ('stable-P0', 123456, 1, None, 0, 0),
    ('invalid-zero-timestamp', 0, 4, None, 10, None),
    ('write-in-progress', 0xffffffffffffffff, 4, None, 10, None),
    ('sequential-even', 0xff00000000000002, 4, None, 0, 2),
    ('sequential-odd', 0xff00000000000003, 4, None, 10, None),
    ('invalid-composite-pstate', 123456, 3, None, 0, 32),
    ('single-snapshot-change', 123456, 4, 'once', 0, 8),
    ('snapshot-never-stable', 123456, 4, 'always', 10, None),
]
results = []
for name, timestamp, raw, mutation, expected_status, expected_output in CASES:
    uc = Uc(UC_ARCH_X86, UC_MODE_64)
    pages = (0xf1000, 0xf3000, 0x37000, 0x246000)
    for page in pages:
        block, _ = va_bytes(data, page, 4096)
        uc.mem_map(page, 4096, UC_PROT_READ | (UC_PROT_EXEC if page != 0x246000 else 0))
        uc.mem_write(page, block)
    # Only the log-level word is mapped in this synthetic BSS page. Zero skips
    # diagnostic calls on failure. This is not an observation of runtime state.
    uc.mem_map(0x153d000, 4096, UC_PROT_READ | UC_PROT_WRITE)
    device, shared, output, stack, sentinel, context = 0x70000000, 0x71000000, 0x72000000, 0x73000000, 0x7fff0000, 0x74000000
    uc.mem_map(device, 0x90000, UC_PROT_READ | UC_PROT_WRITE)
    uc.mem_map(shared, 4096, UC_PROT_READ | UC_PROT_WRITE)
    uc.mem_map(output, 4096, UC_PROT_READ | UC_PROT_WRITE)
    uc.mem_map(stack, 0x10000, UC_PROT_READ | UC_PROT_WRITE)
    uc.mem_map(sentinel, 4096, UC_PROT_READ | UC_PROT_EXEC)
    uc.mem_write(device, b'\x01')
    uc.mem_write(device + 0x8b728, struct.pack('<Q', 2))
    uc.mem_write(device + 0x286c8, struct.pack('<I', 1))
    uc.mem_write(device + 0x286d0, struct.pack('<I', 0))
    uc.mem_write(device + 0x286c0, struct.pack('<Q', shared))
    uc.mem_write(shared + 2280, struct.pack('<QII', timestamp, raw, 0))
    canary = 0xdeadbeef
    uc.mem_write(output, struct.pack('<III', canary, canary, canary))
    uc.mem_write(stack + 0x8000, struct.pack('<Q', sentinel))
    uc.reg_write(UC_X86_REG_RSP, stack + 0x8000)
    uc.reg_write(UC_X86_REG_RDI, context)
    uc.reg_write(UC_X86_REG_RSI, device)
    uc.reg_write(UC_X86_REG_RDX, output + 4)
    counters = {'instructions': 0, 'timestamp_attempts': 0, 'mutations': 0}
    allowed = ((0xf32b0, 0xf33b0), (0xf1b50, 0xf1db0), (0xf1db0, 0xf1f70), (0x376e0, 0x37720))

    def guard(engine, address, size, _):
        if not any(start <= address < end for start, end in allowed):
            raise ValueError('execution escaped isolated RUSD functions: ' + hex(address))
        counters['instructions'] += 1
        if address == 0xf1e5e:
            counters['timestamp_attempts'] += 1
        if address == 0xf1e84 and (mutation == 'always' or mutation == 'once' and not counters['mutations']):
            counters['mutations'] += 1
            new_ts = timestamp + counters['mutations']
            engine.mem_write(shared + 2280, struct.pack('<QII', new_ts, 256, 0))

    uc.hook_add(UC_HOOK_CODE, guard)
    uc.emu_start(0xf32b0, sentinel, count=10000)
    if uc.reg_read(UC_X86_REG_RIP) != sentinel:
        raise ValueError('instruction budget exhausted')
    status = uc.reg_read(UC_X86_REG_RAX) & 0xffffffff
    before, result, after = struct.unpack('<III', bytes(uc.mem_read(output, 12)))
    assert before == canary and after == canary, 'output canary changed'
    assert status == expected_status, (name, status)
    assert result == (canary if expected_output is None else expected_output), (name, result)
    if status == 10:
        assert counters['timestamp_attempts'] == 5
    results.append({'case': name, 'synthetic_timestamp': hex(timestamp), 'synthetic_raw_pstate': raw,
                    'status_raw': status, 'output_u32': result,
                    'output_changed': result != canary, **counters})

print(json.dumps({'artifact_sha256': EXPECTED, 'engine': 'Unicorn ' + unicorn.__version__,
                  'status': 'source-decoded', 'entry_elf_va': '0xf32b0',
                  'schema': {'buffer_offset': 2280, 'record_bytes': 16, 'value_offset': 8, 'poll_mask': 2},
                  'isolation': 'copied instruction/data pages and synthetic device/stack/shared/output memory only; all other code fails closed',
                  'fixtures': results,
                  'limits': 'Synthetic initialization skips allocation, poll requests and hardware; this proves no historical callback selection, buffer contents, sensor state or firmware writer.'}, indent=2))

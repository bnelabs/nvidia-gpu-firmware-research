#!/usr/bin/env python3
"""Stop copied host code immediately before its transport callback.

All object handles, fd and payload pointers are synthetic emulator values.
No syscall or target instruction at the transport helper is executed.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from emulate_pstate_conversion import EXPECTED, va_bytes
from offline_io import read_artifact
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_RDI, UC_X86_REG_RSI, UC_X86_REG_RDX, UC_X86_REG_RCX, UC_X86_REG_R8, UC_X86_REG_R9, UC_X86_REG_RSP
import unicorn

data = read_artifact('firmware-store/gsp-kernels/libnvidia-ml-615.71.09.so')
assert hashlib.sha256(data).hexdigest() == EXPECTED
uc = Uc(UC_ARCH_X86, UC_MODE_64)
for base, length, permissions in ((0x157000, 0x3000, UC_PROT_READ | UC_PROT_EXEC),
                                  (0x161000, 4096, UC_PROT_READ | UC_PROT_EXEC),
                                  (0x246000, 4096, UC_PROT_READ),
                                  (0x2d2000, 4096, UC_PROT_READ | UC_PROT_WRITE)):
    # The final data LOAD ends inside this page. Read only its required prefix,
    # leaving the rest of the emulated page zero rather than inventing file bytes.
    raw, _ = va_bytes(data, base, 0xb00 if base == 0x2d2000 else length)
    uc.mem_map(base, length, permissions)
    uc.mem_write(base, raw)
# A stop page exists so Unicorn can deliver the instruction hook. The real
# transport helper instructions are never run, emulated or native.
uc.mem_map(0x156000, 4096, UC_PROT_READ | UC_PROT_EXEC)
uc.mem_write(0x1567e0, b'\x90')
stack, payload = 0x70000000, 0x71000000
uc.mem_map(stack, 0x10000, UC_PROT_READ | UC_PROT_WRITE)
uc.mem_map(payload, 4096, UC_PROT_READ | UC_PROT_WRITE)
uc.mem_write(0x2d2ab0, struct.pack('<i', 123))
uc.reg_write(UC_X86_REG_RSP, stack + 0x8000)
for register, value in ((UC_X86_REG_RDI, 0x1234), (UC_X86_REG_RSI, 0x5678),
                        (UC_X86_REG_RDX, 0x20802068), (UC_X86_REG_RCX, payload),
                        (UC_X86_REG_R8, 4)):
    uc.reg_write(register, value)
executed = []
result = {}

def guard(engine, address, size, _):
    if address == 0x1567e0:
        pointer = engine.reg_read(UC_X86_REG_R8)
        raw = bytes(engine.mem_read(pointer, 32))
        client, obj, cmd, flags, params, params_size, status = struct.unpack('<IIIIQII', raw)
        result.update({'synthetic_fd': engine.reg_read(UC_X86_REG_RDI),
                       'escape_number': hex(engine.reg_read(UC_X86_REG_RSI)),
                       'envelope_bytes': engine.reg_read(UC_X86_REG_RDX),
                       'ioctl_request': hex(engine.reg_read(UC_X86_REG_RCX)),
                       'NVOS54_raw_hex': raw.hex(),
                       'NVOS54': {'synthetic_client': client, 'synthetic_object': obj,
                                  'command': hex(cmd), 'flags': flags,
                                  'synthetic_params_pointer': hex(params), 'params_bytes': params_size,
                                  'initial_status': status},
                       'status_pointer_matches_field': engine.reg_read(UC_X86_REG_R9) == pointer + 28})
        engine.emu_stop()
        return
    if not (0x157810 <= address < 0x159288 or 0x161f20 <= address < 0x161f6d):
        raise ValueError('unexpected code outside bounded dispatcher: ' + hex(address))
    executed.append(address)

uc.hook_add(UC_HOOK_CODE, guard)
uc.emu_start(0x157810, 0, count=10000)
assert result and result['synthetic_fd'] == 123
assert result['ioctl_request'] == '0xc020462a' and result['envelope_bytes'] == 32
assert result['NVOS54']['command'] == '0x20802068' and result['NVOS54']['params_bytes'] == 4
assert result['status_pointer_matches_field']
assert result['NVOS54']['synthetic_client'] == 0x1234 and result['NVOS54']['synthetic_object'] == 0x5678
print(json.dumps({'artifact_sha256': EXPECTED, 'engine': 'Unicorn ' + unicorn.__version__,
                  'status': 'source-decoded', 'synthetic_result': result,
                  'executed_host_elf_vas': [hex(x) for x in executed],
                  'limits': 'Stops before transport helper. No ioctl, native execution, driver result, live handle or hardware semantics were tested.'}, indent=2))

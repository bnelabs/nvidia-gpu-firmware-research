#!/usr/bin/env python3
"""Re-export copied host/firmware bytes, address domains and disassembly."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import capstone

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from offline_io import read_artifact
from emulate_pstate_conversion import EXPECTED, va_bytes

host_path = 'firmware-store/gsp-kernels/libnvidia-ml-615.71.09.so'
fw_path = 'firmware-store/gsp-kernels/615-kernel-10.elf'
host, fw = read_artifact(host_path), read_artifact(fw_path)
fw_hash = '4ac95cbbe55b5e61572053d0c8a410b4de7693eaa2881d1878c76b6405426f2a'
assert hashlib.sha256(host).hexdigest() == EXPECTED
assert hashlib.sha256(fw).hexdigest() == fw_hash
host_ranges = [(0x31aeb, 0x31afc), (0x31b1a, 0x31bcf), (0x1528f0, 0x152a22),
               (0x995f0, 0x99840), (0x1218f0, 0x121d20), (0xf17d0, 0xf1b50),
               (0xf1b50, 0xf1db0), (0xf1db0, 0xf1f70), (0xf32b0, 0xf33b0),
               (0xa5880, 0xa5ba0), (0xa5600, 0xa5605), (0x157810, 0x159288),
               (0x161f20, 0x161f6d), (0x1567e0, 0x1568e2), (0x1546e0, 0x1546e5),
               (0x154800, 0x1548a7)]
host_exports = []
for start, end in host_ranges:
    raw, offset = va_bytes(host, start, end - start)
    command = ['objdump', '-d', '-Mintel', '--start-address=' + hex(start), '--stop-address=' + hex(end), host_path]
    host_exports.append({'host_elf_va': hex(start), 'end_exclusive': hex(end), 'file_offset': hex(offset),
                         'raw_hex': raw.hex(), 'sha256': hashlib.sha256(raw).hexdigest(),
                         'command': command, 'assembly': subprocess.check_output(command, text=True)})
fw_ranges = [(0x1447738, 0x1447884), (0x1447ac8, 0x1447c48),
             (0x16be978, 0x16be9c6), (0x167de40, 0x167de9e)]
md = capstone.Cs(capstone.CS_ARCH_RISCV, capstone.CS_MODE_RISCV64 | capstone.CS_MODE_RISCVC)
fw_exports = []
for start, end in fw_ranges:
    raw, offset = va_bytes(fw, start, end - start)
    instructions = [{'firmware_elf_va': hex(i.address), 'bytes': i.bytes.hex(),
                      'mnemonic': i.mnemonic, 'operands': i.op_str} for i in md.disasm(raw, start)]
    assert sum(len(bytes.fromhex(i['bytes'])) for i in instructions) == len(raw)
    fw_exports.append({'firmware_elf_va': hex(start), 'end_exclusive': hex(end), 'file_offset': hex(offset),
                       'raw_hex': raw.hex(), 'sha256': hashlib.sha256(raw).hexdigest(), 'instructions': instructions})
pointers = []
for address in (0x2d1190, 0x2d1100, 0x2d12a0, 0x2d12f0, 0x2d1cf0, 0x2d20a8):
    raw, off = va_bytes(host, address, 8)
    pointers.append({'host_elf_va': hex(address), 'file_offset': hex(off), 'raw_hex': raw.hex(),
                     'u64_le': hex(struct.unpack('<Q', raw)[0])})
intercepts = []
for i in range(64):
    raw, offset = va_bytes(host, 0x246680 + i * 16, 16)
    cmd, reserved, fn = struct.unpack('<IIQ', raw)
    intercepts.append({'file_offset': hex(offset), 'raw_hex': raw.hex(), 'command': hex(cmd),
                       'reserved_raw': reserved, 'function_host_elf_va': hex(fn)})
    if cmd == 0:
        break
else:
    raise ValueError('interception table sentinel missing')
assert all(int(row['command'], 16) != 0x20802068 for row in intercepts)
print(json.dumps({'host': {'path': host_path, 'sha256': EXPECTED, 'bytes': len(host),
                           'domain': 'x86-64 host link-time ELF VA; runtime load bias unknown',
                           'code_ranges': host_exports, 'pointer_data': pointers,
                           'control_interception_table': intercepts},
                  'firmware': {'path': fw_path, 'sha256': fw_hash, 'bytes': len(fw),
                               'domain': 'RISC-V firmware ELF VA, distinct from copied ELF file offsets and host VAs',
                               'decoder': 'Capstone ' + capstone.__version__, 'code_ranges': fw_exports},
                  'constructor_address_equation': 'global_base + index*0x93418 + 0x285e0 == (global_base + 0xa0 + index*0x93418) + 0x28540',
                  'firmware_direct_call': {'auipc_va': '0x16be9a0', 'jalr_va': '0x16be9a4',
                                           'signed_upper_immediate': -0x41000, 'signed_low_immediate': 0x4a0,
                                           'target_va': hex(0x16be9a0 - 0x41000 + 0x4a0)},
                  'limits': 'Static code/data and synthetic verification; no historical/runtime identity, callback execution, hardware register or workload claim.'}, indent=2))

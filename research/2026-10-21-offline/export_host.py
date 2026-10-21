#!/usr/bin/env python3
"""Emit reproducible static host evidence; no target code is executed."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from offline_io import read_artifact
from emulate_pstate_conversion import EXPECTED, va_bytes

path = 'firmware-store/gsp-kernels/libnvidia-ml-615.71.09.so'
data = read_artifact(path)
if hashlib.sha256(data).hexdigest() != EXPECTED:
    raise ValueError('version-specific offsets require the exact artifact hash')

ranges = [(0x99a20, 0x99c00), (0x995f0, 0x99840), (0x1218f0, 0x121d20),
          (0xa5880, 0xa5ba0), (0x376e0, 0x37720), (0x1528f0, 0x152a22),
          (0xa5600, 0xa5605), (0x157810, 0x157898)]
exports = []
for start, end in ranges:
    raw, off = va_bytes(data, start, end - start)
    command = ['objdump', '-d', '-Mintel', '--start-address=' + hex(start),
               '--stop-address=' + hex(end), path]
    exports.append({'start_elf_va': hex(start), 'end_elf_va_exclusive': hex(end),
                    'file_offset': hex(off), 'raw_hex': raw.hex(),
                    'raw_sha256': hashlib.sha256(raw).hexdigest(), 'command': command,
                    'disassembly': subprocess.check_output(command, text=True)})

reloc_command = ['readelf', '-rW', path]
relocs = subprocess.check_output(reloc_command, text=True)
retained_relocs = []
for line in relocs.splitlines():
    parts = line.split()
    if len(parts) >= 4 and parts[2] == 'R_X86_64_RELATIVE':
        address = int(parts[0], 16)
        if address in (0x2d1190, 0x2d1100, 0x2d12f0, 0x2d20a8) or 0x2d2180 <= address < 0x2d2338:
            retained_relocs.append(line)

table = data[0x2d1180:0x2d1180 + 55 * 8]
mixed, mixed_off = va_bytes(data, 0x2d1180, 55 * 8)
call_target, call_off = va_bytes(data, 0x2d20a8, 8)
root_slot, root_off = va_bytes(data, 0x2d12f0, 8)
success_entry, success_off = va_bytes(data, 0x1ec0ec, 4)
success_target = 0x1ec0ec + struct.unpack('<i', success_entry)[0]
assert success_target == 0x121c68
assert struct.unpack('<Q', call_target)[0] == 0x1218f0
assert struct.unpack('<Q', root_slot)[0] == 0x2d2060
captures = []
for p in sorted(Path('06-ground-truth/nvml-pstate-trace').glob('*.log')):
    raw = read_artifact(p)
    captures.append({'path': str(p), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                     'kind': 'historical text log, not full raw pointer payloads'})
print(json.dumps({
    'artifact': {'path': path, 'bytes': len(data), 'sha256': EXPECTED,
                 'architecture': 'x86-64 host userspace', 'version': '615.71.09',
                 'load_bias': 'unknown at runtime; all VAs here are link-time ELF VAs'},
    'tool_versions': {tool: subprocess.check_output([tool, '--version'], text=True).splitlines()[0]
                      for tool in ('objdump', 'readelf')},
    'elf_loads': subprocess.check_output(['readelf', '-lW', path], text=True),
    'disassembly_ranges': exports, 'relocation_command': reloc_command,
    'selected_raw_relocations': retained_relocs,
    'callback_chain': [
        {'elf_va': '0x2d12f0', 'file_offset': hex(root_off), 'value': '0x2d2060', 'raw_hex': root_slot.hex()},
        {'elf_va': '0x2d20a8', 'file_offset': hex(call_off), 'value': '0x1218f0', 'raw_hex': call_target.hex()}],
    'status_zero_jump_table': {'table_elf_va': '0x1ec0ec', 'file_offset': hex(success_off),
                               'raw_hex': success_entry.hex(), 'signed_le_displacement': struct.unpack('<i', success_entry)[0],
                               'target_elf_va': hex(success_target)},
    'function_table': {'file_offset': '0x2d1180', 'elf_va': '0x2d2180', 'bytes': len(table),
                       'sha256': hashlib.sha256(table).hexdigest(), 'raw_hex': table.hex(),
                       'entries_elf_va': [hex(v[0]) for v in struct.iter_unpack('<Q', table)]},
    'separate_copied_template': {'elf_va': '0x2d1180', 'file_offset': hex(mixed_off),
                                  'raw_hex': mixed.hex(),
                                  'first_qwords': [hex(v) for v in struct.unpack('<8Q', mixed[:64])]},
    'captures': captures,
    'proven_boundary': '0xa58fa indirect host callback [context+0x20]. The file template selects 0xa5600 -> 0x157810; runtime context selection and the complete syscall path are not established here.',
    'runtime_path': 'not established by static export or the retained abbreviated log',
}, indent=2))

#!/usr/bin/env python3
"""Parse an explicit NVOC_CLASS_DEF from a copied ELF64 LE firmware artifact.

Layout is the source-defined RV64 NV_PRINTF_STRINGS_ALLOWED=0 variant: class info
is 16 bytes, class-def export pointer is +32, export info is {u32 count,pad,u64
entries}, and method entries are 32 bytes. No inference of live accessibility.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
from offline_io import read_artifact


def mapping(data):
    if len(data) < 64 or data[:6] != b'\x7fELF\x02\x01':
        raise ValueError('requires copied ELF64 little-endian input')
    if struct.unpack_from('<H', data, 18)[0] != 243:
        raise ValueError('this explicit NVOC layout profile requires RISC-V ELF')
    phoff = struct.unpack_from('<Q', data, 32)[0]
    stride, count = struct.unpack_from('<HH', data, 54)
    if stride != 56 or count > 1024 or phoff + stride * count > len(data):
        raise ValueError('invalid program header extent')
    segments = []
    for i in range(count):
        kind, flags, offset, va, _, size, memsize, _ = struct.unpack_from('<II6Q', data, phoff + i * stride)
        if kind == 1:
            if offset + size > len(data) or size > memsize:
                raise ValueError('truncated or inconsistent LOAD segment')
            segments.append((offset, va, size, flags))
    return segments


def region(data, segments, va, size):
    matches = [(off + va - base, flags) for off, base, length, flags in segments
               if size >= 0 and base <= va and va + size <= base + length]
    if len(matches) != 1:
        raise ValueError('ambiguous or unmapped file-backed VA: ' + hex(va))
    off, flags = matches[0]
    return data[off:off + size], off, flags


def parse(data, class_def_va):
    segments = mapping(data)
    raw, class_off, _ = region(data, segments, class_def_va, 40)
    object_size, id_visibility, provider, create, casts, exports = struct.unpack('<II4Q', raw)
    info, info_off, _ = region(data, segments, exports, 16)
    count, padding, array_va = struct.unpack('<IIQ', info)
    if not 0 < count <= 65536 or padding:
        raise ValueError('implausible export count/padding')
    table, table_off, _ = region(data, segments, array_va, count * 32)
    rows = []
    previous = -1
    for i in range(count):
        entry = table[i * 32:(i + 1) * 32]
        function, flags, access, command, size, declaring_class = struct.unpack('<QIIIIQ', entry)
        if command <= previous:
            raise ValueError('export methods are not strictly sorted')
        previous = command
        function_file = None
        executable_mapping = None
        if function:
            _, function_file, permissions = region(data, segments, function, 2)
            executable_mapping = bool(permissions & 1)
        rows.append({'index': i, 'entry_file_offset': hex(table_off + i * 32),
                     'entry_firmware_elf_va': hex(array_va + i * 32), 'raw_hex': entry.hex(),
                     'command': hex(command), 'params_bytes': size, 'flags_raw': hex(flags),
                     'access_right_raw': hex(access), 'function_firmware_elf_va': hex(function),
                     'function_file_offset': hex(function_file) if function_file is not None else None,
                     'function_in_executable_load': executable_mapping,
                     'declaring_class_info_firmware_elf_va': hex(declaring_class)})
    return {'artifact_bytes': len(data), 'artifact_sha256': hashlib.sha256(data).hexdigest(),
            'elf_machine': 243,
            'load_segments': [{'file_offset': hex(off), 'firmware_elf_va': hex(va),
                              'file_bytes': size, 'flags_raw': flags} for off, va, size, flags in segments],
            'status': 'source-decoded', 'layout': 'NVOC RV64 strings-disabled; explicit source schema',
            'class_definition': {'firmware_elf_va': hex(class_def_va), 'file_offset': hex(class_off),
                                 'raw_hex': raw.hex(), 'object_size': object_size,
                                 'class_id': hex(id_visibility & 0xffffff), 'visibility': id_visibility >> 30,
                                 'provider_id_raw': hex(provider), 'create_function_va': hex(create),
                                 'cast_info_va': hex(casts), 'export_info_va': hex(exports)},
            'export_info': {'file_offset': hex(info_off), 'raw_hex': info.hex(), 'count': count,
                            'table_va': hex(array_va), 'table_file_offset': hex(table_off),
                            'table_sha256': hashlib.sha256(table).hexdigest()},
            'methods': rows,
            'limits': 'Packaged method metadata is not live permission, per-SKU support, reachability, runtime use or complete GPU behavior.'}


def annotate(result, source_root):
    """Only copy literal identities from exact-release public source; no guesses."""
    sdk = source_root / 'src/common/sdk/nvidia/inc'
    source = source_root / 'src/nvidia/generated/g_subdevice_nvoc.c'
    manifest = []

    def source_text(path):
        raw = read_artifact(path)
        manifest.append({'path': str(path.relative_to(source_root)), 'bytes': len(raw),
                         'sha256': hashlib.sha256(raw).hexdigest()})
        return raw.decode('utf-8')

    identity = source_text(source)
    methods = {}
    for match in re.finditer(r'/\*methodId=\*/\s*(0x[0-9a-fA-F]+)u,([^;]*?)(?=/\*methodId=\*/|\Z)', identity):
        command = int(match[1], 16)
        name = re.search(r'/\*func=\*/\s*"([^"]+)"', match[2])
        if name:
            methods[command] = (name[1], identity[:match.start()].count('\n') + 1)
    defines = {}
    for path in sorted((sdk / 'ctrl').rglob('*.h')):
        text = source_text(path)
        for m in re.finditer(r'^#define\s+(NV\w*CTRL_CMD_\w+)\s+\(?(0x[\da-fA-F]+)[uUlL]*\)?', text, re.M):
            defines.setdefault(int(m[2], 16), []).append({'name': m[1], 'path': str(path.relative_to(source_root)),
                                                        'line': text[:m.start()].count('\n') + 1})
    control_path = source_root / 'src/nvidia/inc/kernel/rmapi/control.h'
    control = source_text(control_path)
    flag_bits = []
    for m in re.finditer(r'^#define\s+(RMCTRL_FLAGS_\w+)\s+(0x[\da-fA-F]+)', control, re.M):
        value = int(m[2], 16)
        if value and value & (value - 1) == 0:
            flag_bits.append((value, m[1]))
    for row in result['methods']:
        cmd = int(row['command'], 16)
        match = methods.get(cmd)
        row['public_method_name'] = match[0] if match else None
        row['public_method_source_line'] = match[1] if match else None
        row['public_command_definitions'] = defines.get(cmd, [])
        row['public_flag_bits'] = [name for value, name in flag_bits if int(row['flags_raw'], 16) & value]
    head = read_artifact(source_root / '.git/HEAD').decode().strip()
    result['public_source_reference'] = {'local_root': str(source_root),
        'source_commit': head if re.fullmatch('[0-9a-f]{40}', head) else None,
        'annotation_scope': 'literal commands and generated public Subdevice names only; missing names remain null'}
    result['annotation_source_manifest'] = manifest
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifact')
    parser.add_argument('--class-def-va', type=lambda v: int(v, 0), required=True)
    parser.add_argument('--source-root', type=Path)
    args = parser.parse_args()
    result = parse(read_artifact(args.artifact), args.class_def_va)
    if args.source_root:
        result = annotate(result, args.source_root)
    print(json.dumps(result, indent=2))

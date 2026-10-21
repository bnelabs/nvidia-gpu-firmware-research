#!/usr/bin/env python3
"""Bounded static RV64/RVC ranges; no target execution or hardware access."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from offline_io import read_artifact
from extract_nvoc_exports import mapping, region
import capstone

PATH = 'firmware-store/gsp-kernels/615-kernel-10.elf'
EXPECTED = '4ac95cbbe55b5e61572053d0c8a410b4de7693eaa2881d1878c76b6405426f2a'

def signed(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value

def references(instructions):
    refs = []
    for first, second in zip(instructions, instructions[1:]):
        if len(first.bytes) != 4 or len(second.bytes) != 4 or second.address != first.address + 4:
            continue
        a, b = int.from_bytes(first.bytes, 'little'), int.from_bytes(second.bytes, 'little')
        if a & 127 != 0x17 or ((b >> 15) & 31) != ((a >> 7) & 31) or not ((a >> 7) & 31):
            continue
        opcode, funct3 = b & 127, (b >> 12) & 7
        kind = ('direct-jalr' if opcode == 0x67 and funct3 == 0 else
                'pc-relative-load' if opcode == 3 else
                'pc-relative-address' if opcode == 0x13 and funct3 == 0 else None)
        if kind:
            upper, low = signed(a & 0xfffff000, 32), signed(b >> 20, 12)
            target = (first.address + upper + low) & ((1 << 64) - 1)
            if kind == 'direct-jalr':
                target &= ~1
            refs.append({'kind': kind, 'auipc_firmware_elf_va': hex(first.address),
                         'consumer_firmware_elf_va': hex(second.address), 'signed_upper': upper,
                         'signed_low': low, 'target_firmware_elf_va': hex(target),
                         'raw_hex': (first.bytes + second.bytes).hex()})
    return refs

def inspect(data, ranges):
    assert hashlib.sha256(data).hexdigest() == EXPECTED
    segments = mapping(data)
    md = capstone.Cs(capstone.CS_ARCH_RISCV, capstone.CS_MODE_RISCV64 | capstone.CS_MODE_RISCVC)
    output = []
    for start, end in ranges:
        if not start < end <= start + 0x10000 or start & 1 or end & 1:
            raise ValueError('requires aligned bounded range <=64KiB')
        raw, offset, flags = region(data, segments, start, end - start)
        insns = list(md.disasm(raw, start))
        covered = sum(i.size for i in insns)
        refs = references(insns)
        for ref in refs:
            address = int(ref['target_firmware_elf_va'], 16)
            try:
                target, off, permissions = region(data, segments, address, 8)
            except ValueError:
                ref.update({'target_file_offset': None, 'target_raw8_hex': None,
                            'target_u64_raw': None, 'target_mapping': 'not uniquely file-backed; contents unknown'})
            else:
                ref.update({'target_file_offset': hex(off), 'target_raw8_hex': target.hex(),
                            'target_u64_raw': hex(struct.unpack('<Q', target)[0])})
        output.append({'firmware_elf_va': hex(start), 'end_exclusive': hex(end),
                       'file_offset': hex(offset), 'load_flags_raw': flags, 'raw_hex': raw.hex(),
                       'sha256': hashlib.sha256(raw).hexdigest(), 'references': refs,
                       'decoded_bytes': covered, 'unparsed_tail_hex': raw[covered:].hex(),
                       'instructions': [{'va': hex(i.address), 'raw_hex': i.bytes.hex(),
                                         'mnemonic': i.mnemonic, 'operands': i.op_str} for i in insns]})
    return {'artifact_path': PATH, 'artifact_bytes': len(data), 'artifact_sha256': EXPECTED,
            'address_domain': 'firmware ELF VA with explicit copied-file offsets; not live addresses',
            'decoder': 'Capstone ' + capstone.__version__, 'ranges': output,
            'limits': 'Static instructions and adjacent AUIPC references only; supplied ranges, no complete CFG or live behavior proof.'}

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('range', nargs='+', help='start:end in firmware ELF VA')
    args = p.parse_args()
    print(json.dumps(inspect(read_artifact(PATH), [tuple(int(v, 0) for v in r.split(':')) for r in args.range]), indent=2))

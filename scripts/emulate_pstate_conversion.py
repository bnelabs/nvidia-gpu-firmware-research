#!/usr/bin/env python3
"""CPU-only execution of one hash-pinned x86 host-library conversion routine.

Requires Unicorn. Does not dlopen the library. Only two copied ELF pages, a
synthetic stack, and a return sentinel are mapped in emulated memory. No syscalls,
MMIO, devices, firmware, process attachment or native target execution exists.
"""
import argparse
import hashlib
import json
import struct

from offline_io import read_artifact

EXPECTED = '283793c0c30dc32f87c0e9fc9b5326fe764bad156e61afa3e997684c47b29a95'
ENTRY, END, TABLE = 0x376e0, 0x37720, 0x246220


def va_bytes(data, va, size):
    phoff = struct.unpack_from('<Q', data, 32)[0]
    stride, count = struct.unpack_from('<HH', data, 54)
    if data[:6] != b'\x7fELF\x02\x01' or stride != 56:
        raise ValueError('unsupported ELF mapping')
    for i in range(count):
        kind, flags, off, base, _, filesz, memsz, _ = struct.unpack_from('<II6Q', data, phoff + i * stride)
        if kind == 1 and base <= va and va + size <= base + filesz:
            result = data[off + va - base:off + va - base + size]
            if len(result) != size:
                raise ValueError('truncated ELF segment')
            return result, off + va - base
    raise ValueError('VA range has no file-backed LOAD mapping')


def run(data):
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_PROT_READ, UC_PROT_WRITE, UC_PROT_EXEC, UC_HOOK_CODE
    from unicorn.x86_const import UC_X86_REG_RDI, UC_X86_REG_RSP, UC_X86_REG_RIP, UC_X86_REG_RAX
    import unicorn

    if hashlib.sha256(data).hexdigest() != EXPECTED:
        raise ValueError('artifact hash mismatch; refusing version-specific offsets')
    page_code, code_file = va_bytes(data, ENTRY & ~0xfff, 4096)
    page_table, table_file = va_bytes(data, TABLE & ~0xfff, 4096)
    table, _ = va_bytes(data, TABLE, 256)
    rows = []
    inputs = [1 << i for i in range(16)] + [0, 3, 0x10000, 0xffffffff]
    for raw in inputs:
        uc = Uc(UC_ARCH_X86, UC_MODE_64)
        uc.mem_map(ENTRY & ~0xfff, 4096, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_write(ENTRY & ~0xfff, page_code)
        uc.mem_map(TABLE & ~0xfff, 4096, UC_PROT_READ)
        uc.mem_write(TABLE & ~0xfff, page_table)
        stack, sentinel = 0x70000000, 0x7fff0000
        uc.mem_map(stack, 4096, UC_PROT_READ | UC_PROT_WRITE)
        uc.mem_map(sentinel, 4096, UC_PROT_READ | UC_PROT_EXEC)
        uc.mem_write(stack + 2048, struct.pack('<Q', sentinel))
        uc.reg_write(UC_X86_REG_RSP, stack + 2048)
        uc.reg_write(UC_X86_REG_RDI, raw)
        executed = []

        def guard(engine, address, size, _):
            if not ENTRY <= address < END:
                raise ValueError('execution escaped the isolated conversion routine')
            executed.append(address)

        uc.hook_add(UC_HOOK_CODE, guard)
        uc.emu_start(ENTRY, sentinel, count=512)
        if uc.reg_read(UC_X86_REG_RIP) != sentinel:
            raise ValueError('instruction budget exhausted before synthetic return')
        value = uc.reg_read(UC_X86_REG_RAX) & 0xffffffff
        expected = raw.bit_length() - 1 if raw and not raw & (raw - 1) and raw <= 0x8000 else 32
        if value != expected:
            raise ValueError('conversion disagrees with the pinned one-hot contract')
        rows.append({'input_u32': raw, 'returned_u32': value, 'instructions': len(executed)})
    return {
        'status': 'source-decoded', 'engine': 'Unicorn ' + unicorn.__version__,
        'artifact_sha256': EXPECTED, 'domain': 'host-library link-time ELF VA, load bias zero',
        'routine_va': hex(ENTRY), 'routine_end_va_exclusive': hex(END),
        'code_page_file_offset': hex(code_file), 'table_page_file_offset': hex(table_file),
        'table_va': hex(TABLE), 'table_hex': table.hex(),
        'table_rows_u32_le': [struct.unpack_from('<4I', table, i * 16) for i in range(16)],
        'synthetic_inputs': rows,
        'limits': 'Pure conversion only. Synthetic inputs establish no current hardware P-state, callback selection, or GSP response.'
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('library')
    args = parser.parse_args()
    print(json.dumps(run(read_artifact(args.library)), indent=2))

#!/usr/bin/env python3
"""Decode a bounded, descriptor-selected boot code block from copied sources."""
import json
from pathlib import Path
import sys
import capstone

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from compare_ga102_boot import analyze, digest

results = []
for source in (
    'vendor/research-sources/61dcc93722ecb418bb5f2e00923f05b4b8051dd1/g_bindata_kgspGetBinArchiveGspRmBoot_GA102.c',
    'vendor/open-gpu-kernel-modules/src/nvidia/generated/g_bindata_kgspGetBinArchiveGspRmBoot_GA102.c',
):
    image, _, metadata = analyze(source)
    start = metadata['descriptor_fields']['bootloaderOffset']
    block = image[start:start + 128]
    decoder = capstone.Cs(capstone.CS_ARCH_RISCV, capstone.CS_MODE_RISCV64 | capstone.CS_MODE_RISCVC)
    decoded = [{'component_file_offset': hex(i.address), 'bytes_hex': i.bytes.hex(),
                'mnemonic': i.mnemonic, 'operands': i.op_str} for i in decoder.disasm(block, start)]
    import struct
    # File-relative AUIPC pairs in the decoded block lead to these literal pools.
    # Preserve the full pointer values; do not strip tags or assign register names.
    literals = [{'component_file_offset': hex(off), 'bytes_hex': image[off:off + 8].hex(),
                 'u64_le': hex(struct.unpack_from('<Q', image, off)[0])}
                for off in (0x57c8, 0x57d0, 0x5860)]
    results.append({'source': source, 'offset': hex(start), 'bytes': len(block),
                    'sha256': digest(block), 'raw_hex': block.hex(), 'instructions': decoded,
                    'referenced_literal_pool': literals,
                    'decoded_bytes': sum(len(bytes.fromhex(i['bytes_hex'])) for i in decoded)})
print(json.dumps({'status': 'hypothesis', 'decoder': 'Capstone ' + capstone.__version__,
                  'domain': 'component file offset displayed as the disassembler base; not a proven firmware VA',
                  'evidence': results,
                  'limits': 'Linear decode under explicit RV64+RVC assumption. No function boundaries, load address, branch reachability or MMIO effects proven.'}, indent=2))

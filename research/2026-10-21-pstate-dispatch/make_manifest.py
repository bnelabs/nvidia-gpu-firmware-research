#!/usr/bin/env python3
"""Hash retained inputs and exact-release source without executing artifacts."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from offline_io import read_artifact

root = Path('vendor/open-gpu-kernel-modules-615.71.09')
commit = '61dcc93722ecb418bb5f2e00923f05b4b8051dd1'
assert read_artifact(root / '.git/HEAD').decode().strip() == commit
paths = [
    'version.mk', 'src/nvidia/inc/libraries/nvoc/runtime.h',
    'src/nvidia/inc/libraries/nvoc/prelude.h', 'src/nvidia/inc/libraries/nvoc/rtti.h',
    'src/nvidia/src/libraries/nvoc/src/runtime.c', 'src/nvidia/generated/g_subdevice_nvoc.c',
    'src/nvidia/generated/g_subdevice_nvoc.h', 'src/nvidia/generated/g_gpu_user_shared_data_nvoc.c',
    'src/nvidia/src/kernel/gpu/gpu_user_shared_data.c',
    'src/common/sdk/nvidia/inc/class/cl00de.h', 'src/common/sdk/nvidia/inc/ctrl/ctrl00de.h',
    'src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080internal.h',
    'src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080perf.h',
    'src/common/sdk/nvidia/inc/nvos.h', 'src/common/sdk/nvidia/inc/nvstatuscodes.h',
    'src/nvidia/arch/nvalloc/unix/src/escape.c', 'src/nvidia/src/kernel/rmapi/resource.c',
    'src/nvidia/src/kernel/vgpu/rpc.c', 'src/nvidia/inc/kernel/rmapi/control.h',
    'src/nvidia/arch/nvalloc/unix/include/nv_escape.h', 'kernel-open/common/inc/nv-ioctl-numbers.h',
]

def digest(path):
    data = read_artifact(path)
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

sources = []
for path in paths:
    sources.append({**digest(root / path), 'source_commit': commit, 'source_path': path,
                    'url': 'https://github.com/NVIDIA/open-gpu-kernel-modules/blob/' + commit + '/' + path})
linux_commit = '7d0a66e4bb9081d75c82ec4957c50034cb0ea449'
for local, path in [
    ('linux-ctrl.txt', 'drivers/gpu/drm/nouveau/nvkm/subdev/gsp/rm/r535/ctrl.c'),
    ('linux-gsp-main.txt', 'drivers/gpu/drm/nouveau/nvkm/subdev/gsp/rm/r535/gsp.c'),
    ('linux-nova-gsp.rs', 'drivers/gpu/nova-core/gsp.rs'),
    ('linux-nova-gsp-boot.rs', 'drivers/gpu/nova-core/gsp/boot.rs'),
]:
    sources.append({**digest(Path('vendor/research-sources') / local), 'source_commit': linux_commit,
                    'source_path': path, 'url': 'https://github.com/torvalds/linux/blob/' + linux_commit + '/' + path})
artifacts = [digest(path) for path in (
    'firmware-store/gsp-kernels/libnvidia-ml-615.71.09.so',
    'firmware-store/gsp-kernels/615-kernel-10.elf',
    '06-ground-truth/nvml-pstate-trace/probe-005239-interleaved.log')]
packet = Path('research/2026-10-21-pstate-dispatch')
analysis_paths = sorted(packet.glob('*.py')) + [packet / 'layout.c', packet / 'reproduce.sh']
analysis_paths += [Path('scripts') / name for name in (
    'extract_nvoc_exports.py', 'offline_io.py', 'emulate_pstate_conversion.py', 'run_cpu_only.sh')]
versions = {}
for program in ('objdump', 'readelf', 'cc'):
    versions[program] = subprocess.check_output([program, '--version'], text=True).splitlines()[0]
print(json.dumps({
    'artifacts': artifacts, 'inspected_sources': sources,
    'source_directory_receipts': [digest(packet / 'source-receipts/nova-gsp-directory.json')],
    'analysis_inputs': [digest(path) for path in analysis_paths], 'local_tool_versions': versions,
    'sdk_annotation_manifest': 'gsp-subdevice-exports.json:annotation_source_manifest (207 source files)',
    'source_acquisition': 'Separate detached 615.71.09 checkout; existing vendor tree unchanged. No driver built or loaded.',
    'isa_reference': {'url': 'https://docs.riscv.org/reference/isa/v20260120/unpriv/rv32.html',
        'version': '20260120, RV32I 2.1; AUIPC/JALR semantics also used by RV64',
        'scope': 'Instruction arithmetic only; versioned online reference, not a downloaded hash-keyed source artifact'},
    'context': {'historical_identity': 'RTX 3090 / GPU-8a9c05b3-fea1-4d89-5113-b56acbb1eba9',
        'historical_os': 'UNKNOWN', 'historical_privilege': 'UNKNOWN',
        'current_gpu_driver_gsp_mode_workload': 'UNKNOWN; not queried',
        'firmware_scope': 'RM ELF retained from gsp_ga10x 615.71.09; not asserted to be GA102-exclusive'},
    'limits': 'Input identity and static/synthetic provenance only; no runtime measurements or complete access inventory.'
}, indent=2))

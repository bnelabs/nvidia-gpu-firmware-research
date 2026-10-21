#!/usr/bin/env python3
"""Retained artifact and exact-source hash/excerpt manifest, CPU-only."""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from offline_io import read_artifact

def digest(path):
    raw = read_artifact(path)
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

nvidia=Path('vendor/open-gpu-kernel-modules-615.71.09')
commit='61dcc93722ecb418bb5f2e00923f05b4b8051dd1'
assert read_artifact(nvidia/'.git/HEAD').decode().strip()==commit
sources=[]
for name,ranges in [
    ('src/common/sdk/nvidia/inc/class/cl00de.h',[(35,64),(140,147),(425,450),(528,540),(622,633)]),
    ('src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080perf.h',[(878,901)]),
    ('src/common/sdk/nvidia/inc/nvstatuscodes.h',[(91,95),(113,117)]),
    ('src/nvidia/src/kernel/gpu/gpu_user_shared_data.c',[(300,322),(414,434)]),
]:
    raw=read_artifact(nvidia/name)
    lines=raw.decode().splitlines()
    sources.append({**digest(nvidia/name),'source_commit':commit,'source_path':name,
        'url':'https://github.com/NVIDIA/open-gpu-kernel-modules/blob/'+commit+'/'+name,
        'excerpts':[{'start_line':a,'end_line':b,'text':'\n'.join(lines[a-1:b])} for a,b in ranges]})
linux_commit='7d0a66e4bb9081d75c82ec4957c50034cb0ea449'
for local,name,ranges in [
    ('linux-ctrl.txt','drivers/gpu/drm/nouveau/nvkm/subdev/gsp/rm/r535/ctrl.c',[(69,95)]),
    ('linux-gsp-main.txt','drivers/gpu/drm/nouveau/nvkm/subdev/gsp/rm/r535/gsp.c',[(2116,2120)]),
    ('linux-nova-gsp.rs','drivers/gpu/nova-core/gsp.rs',[(1,23)]),
    ('linux-nova-gsp-boot.rs','drivers/gpu/nova-core/gsp/boot.rs',[(99,145)]),
]:
    path=Path('vendor/research-sources')/local
    lines=read_artifact(path).decode().splitlines()
    sources.append({**digest(path),'source_commit':linux_commit,'source_path':name,
        'url':'https://github.com/torvalds/linux/blob/'+linux_commit+'/'+name,
        'excerpts':[{'start_line':a,'end_line':b,'text':'\n'.join(lines[a-1:b])} for a,b in ranges]})
packet=Path('research/2026-10-21-pstate-writers')
analysis=list(sorted(packet.glob('*.py')))+[packet/'reproduce.sh',Path('tests/test_firmware_references.py')]
analysis += [Path('scripts')/s for s in ('offline_io.py','run_cpu_only.sh','extract_nvoc_exports.py','emulate_pstate_conversion.py')]
print(json.dumps({'artifact_inputs':[digest(p) for p in (
    'firmware-store/gsp-kernels/615-kernel-10.elf',
    'firmware-store/gsp-kernels/libnvidia-ml-615.71.09.so')],
    'sources':sources, 'analysis_inputs':[digest(p) for p in analysis],
    'prior_evidence':[digest('research/2026-10-21-pstate-dispatch/'+p) for p in (
        'SHA256SUMS','gsp-subdevice-exports.json','source-manifest.json')],
    'isa_reference':{'url':'https://docs.riscv.org/reference/isa/v20260120/unpriv/rv32.html',
        'scope':'AUIPC/JALR signed PC-relative arithmetic only, versioned online reference'},
    'context':{'firmware':'retained RM ELF from gsp_ga10x 615.71.09; not asserted GA102-exclusive',
        'historical_board':'RTX 3090 / GA102 reported by prior retained log',
        'historical_os_and_privilege':'UNKNOWN', 'current_device_driver_gsp_workload':'UNKNOWN; not queried',
        'timestamp_units':'UNKNOWN; timestamp source is synthetic and concrete timer callback unresolved'},
    'limits':'Source/static correspondence and synthetic execution, not live measurements or complete writer coverage.'},indent=2))

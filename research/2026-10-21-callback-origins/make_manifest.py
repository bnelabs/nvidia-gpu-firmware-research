#!/usr/bin/env python3
"""Record exact artifacts, source excerpts and analysis hashes without hardware."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from offline_io import read_artifact

def digest(path):
    b=read_artifact(path)
    return {'path':str(path),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}

root=Path('vendor/open-gpu-kernel-modules-615.71.09')
commit='61dcc93722ecb418bb5f2e00923f05b4b8051dd1'
assert read_artifact(root/'.git/HEAD').decode().strip()==commit
sources=[]
for name,ranges in [
    ('src/nvidia/src/kernel/gpu/gpu.c',[(758,860),(889,914)]),
    ('src/nvidia/inc/kernel/rmapi/rmapi.h',[(171,213),(253,268)]),
    ('src/common/sdk/nvidia/inc/nvsecurityinfo.h',[(30,74)]),
    ('src/common/sdk/nvidia/inc/nvstatuscodes.h',[(85,95),(113,117)]),
    ('src/nvidia/inc/libraries/nvoc/rtti.h',[(46,72)]),
    ('src/nvidia/inc/libraries/nvoc/runtime.h',[(70,89)]),
    ('src/nvidia/src/libraries/nvoc/src/runtime.c',[(307,360)]),
    ('src/common/sdk/nvidia/inc/class/cl00de.h',[(140,146)]),
    ('src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080perf.h',[(878,901)]),
]:
    path=root/name
    lines=read_artifact(path).decode().splitlines()
    sources.append({**digest(path),'source_commit':commit,'source_path':name,
        'url':'https://github.com/NVIDIA/open-gpu-kernel-modules/blob/'+commit+'/'+name,
        'excerpts':[{'start_line':a,'end_line':b,'text':'\n'.join(lines[a-1:b])} for a,b in ranges]})
linux='7d0a66e4bb9081d75c82ec4957c50034cb0ea449'
for file,name,ranges in [
    ('linux-ctrl.txt','drivers/gpu/drm/nouveau/nvkm/subdev/gsp/rm/r535/ctrl.c',[(69,95)]),
    ('linux-nova-gsp.rs','drivers/gpu/nova-core/gsp.rs',[(1,23)]),
]:
    path=Path('vendor/research-sources')/file
    lines=read_artifact(path).decode().splitlines()
    sources.append({**digest(path),'source_commit':linux,'source_path':name,
        'url':'https://github.com/torvalds/linux/blob/'+linux+'/'+name,
        'excerpts':[{'start_line':a,'end_line':b,'text':'\n'.join(lines[a-1:b])} for a,b in ranges]})
packet=Path('research/2026-10-21-callback-origins')
analysis=sorted(packet.glob('*.py'))+[packet/'reproduce.sh']
analysis += [Path('scripts')/name for name in ('run_cpu_only.sh','offline_io.py','extract_nvoc_exports.py')]
analysis += [Path('research/2026-10-21-pstate-writers')/name for name in ('export_ranges.py','scan_stores.py')]
print(json.dumps({'artifacts':[digest('firmware-store/gsp-kernels/615-kernel-10.elf')],
    'sources':sources,'analysis_inputs':[digest(p) for p in analysis],
    'prior_evidence':[digest('research/'+name+'/SHA256SUMS') for name in (
        '2026-10-21-offline','2026-10-21-pstate-dispatch','2026-10-21-pstate-writers')],
    'source_scope':'Exact detached 615.71.09 public source plus pinned Linux comparison; copied firmware binary offsets remain artifact-specific.',
    'context':{'firmware_origin':'retained RM ELF from gsp_ga10x 615.71.09; not asserted GA102-exclusive',
        'historical_board':'RTX 3090/GA102 reported previously','historical_os_privilege':'UNKNOWN',
        'current_device_driver_gsp_mode_workload':'UNKNOWN; not queried',
        'instance_pointers_handles_and_context':'synthetic fixtures; no runtime pointer snapshot'},
    'isa_reference':{'url':'https://docs.riscv.org/reference/isa/v20260120/unpriv/rv32.html','scope':'Signed AUIPC/JALR arithmetic only'},
    'limits':'Static assignment and bounded synthetic consumers, not runtime selection, physical value origin, full security proof or complete firmware map.'},indent=2))

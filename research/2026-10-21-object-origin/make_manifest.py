#!/usr/bin/env python3
"""Hash copied artifacts, exact source and the new bounded analysis programs."""
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
for name in [
    'src/nvidia/src/kernel/gpu/gpu.c', 'src/nvidia/generated/g_gpu_nvoc.h',
    'src/nvidia/generated/g_gpu_nvoc.c','src/nvidia/generated/g_eng_desc_nvoc.h',
    'src/nvidia/generated/g_eng_state_nvoc.h','src/nvidia/generated/g_kern_perf_nvoc.c',
    'src/nvidia/inc/libraries/nvoc/rtti.h','src/nvidia/src/libraries/nvoc/src/runtime.c',
    'src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080perf.h',
    'src/common/sdk/nvidia/inc/class/cl00de.h',
]:
    sources.append({**digest(root/name),'source_path':name,'source_commit':commit,
        'url':'https://github.com/NVIDIA/open-gpu-kernel-modules/blob/'+commit+'/'+name})
linux='7d0a66e4bb9081d75c82ec4957c50034cb0ea449'
envy='f102b82381f3f11cee113d16374c87091db039d9'
for path,name,rev,repo in [
    ('linux-'+linux+'/perf.c','drivers/gpu/drm/nouveau/nvkm/subdev/bios/perf.c',linux,'torvalds/linux'),
    ('linux-ctrl.txt','drivers/gpu/drm/nouveau/nvkm/subdev/gsp/rm/r535/ctrl.c',linux,'torvalds/linux'),
    ('linux-nova-gsp.rs','drivers/gpu/nova-core/gsp.rs',linux,'torvalds/linux'),
    ('envytools-'+envy+'/power.c','nvbios/power.c',envy,'envytools/envytools'),
]:
    sources.append({**digest(Path('vendor/research-sources')/path),'source_path':name,'source_commit':rev,
                    'url':'https://github.com/'+repo+'/blob/'+rev+'/'+name})
packet=Path('research/2026-10-21-object-origin')
analyses=sorted(packet.glob('*.py'))+[packet/'reproduce.sh']
analyses += [Path('scripts')/n for n in ('run_cpu_only.sh','offline_io.py','extract_nvoc_exports.py')]
analyses += [Path('research/2026-10-21-pstate-writers/export_ranges.py')]
print(json.dumps({'artifacts':[digest('firmware-store/gsp-kernels/615-kernel-10.elf')],
    'sources':sources,'analysis_inputs':[digest(p) for p in analyses],
    'prior_packet_checksums':[digest(Path('research')/n/'SHA256SUMS') for n in (
        '2026-10-21-offline','2026-10-21-pstate-dispatch','2026-10-21-pstate-writers','2026-10-21-callback-origins')],
    'integration_base_commit':'6f8e387a693a03f9f5d9ec1f3e841f4c1b347292',
    'context':{'artifact_origin':'retained RM ELF from gsp_ga10x 615.71.09; not GA102-exclusive',
        'historical_board':'RTX 3090/GA102 previously reported; not a current observation',
        'historical_os_and_privilege':'UNKNOWN','current_hardware_driver_gsp_mode_workload_health':'UNKNOWN; no collection',
        'execution':'CPU-only bwrap namespace: private /dev, no sysfs, network, host sockets or device passthrough',
        'fixtures':'GPU/object graph, feature flags, heap allocation, current index, parser inputs and availability gate'},
    'limits':'Copied blocks and source comparisons; no complete parser/boot emulation, actual policy selection, physical sensor, exhaustive access map or hardware validation.'},indent=2))

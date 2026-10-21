#!/usr/bin/env python3
"""Hash copied firmware, exact source and the programs used for this analysis."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from offline_io import read_artifact
def digest(path):
    b=read_artifact(path);return {'path':str(path),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
root=Path('vendor/open-gpu-kernel-modules-615.71.09');commit='61dcc93722ecb418bb5f2e00923f05b4b8051dd1'
assert read_artifact(root/'.git/HEAD').decode().strip()==commit
sources=[]
for path in ('src/nvidia/src/kernel/gpu/mem_mgr/mem_desc.c','src/nvidia/inc/kernel/gpu/mem_mgr/mem_desc.h',
             'src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080boardobj.h',
             'src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080perf.h'):
    sources.append({**digest(root/path),'source_commit':commit,'source_path':path,
                    'url':'https://github.com/NVIDIA/open-gpu-kernel-modules/blob/'+commit+'/'+path})
linux='7d0a66e4bb9081d75c82ec4957c50034cb0ea449';envy='f102b82381f3f11cee113d16374c87091db039d9'
for path,source,rev,repo in [
    ('linux-'+linux+'/perf.c','drivers/gpu/drm/nouveau/nvkm/subdev/bios/perf.c',linux,'torvalds/linux'),
    ('linux-ctrl.txt','drivers/gpu/drm/nouveau/nvkm/subdev/gsp/rm/r535/ctrl.c',linux,'torvalds/linux'),
    ('linux-nova-gsp.rs','drivers/gpu/nova-core/gsp.rs',linux,'torvalds/linux'),
    ('envytools-'+envy+'/power.c','nvbios/power.c',envy,'envytools/envytools')]:
    sources.append({**digest(Path('vendor/research-sources')/path),'source_commit':rev,'source_path':source,
                    'url':'https://github.com/'+repo+'/blob/'+rev+'/'+source})
packet=Path('research/2026-10-21-record-producer')
programs=sorted(packet.glob('*.py'))+[packet/'reproduce.sh',Path('scripts/run_cpu_only.sh'),Path('scripts/offline_io.py'),
    Path('scripts/extract_nvoc_exports.py'),Path('research/2026-10-21-pstate-writers/export_ranges.py')]
print(json.dumps({'artifacts':[digest('firmware-store/gsp-kernels/615-kernel-10.elf')],
    'sources':sources,'analysis_inputs':[digest(p) for p in programs],
    'prior_analysis_checksums':[digest('research/2026-10-21-object-origin/SHA256SUMS')],
    'context':{'origin':'retained RM ELF from gsp_ga10x 615.71.09; not GA102-exclusive',
               'historical_board':'RTX 3090/GA102 previously reported; OS/privilege UNKNOWN',
               'current_gpu_driver_gsp_mode_workload_health':'UNKNOWN; not queried',
               'execution':'CPU-only bwrap namespace; no devices/network/sysfs/service sockets',
               'fixtures':'serialized table, object graph, allocator returns; execution begins after unexecuted transfer'},
    'limits':'One decoded schema/mask branch and value-copy prefix; no source-object physical identity, actual input table, complete parser validation or runtime selection proof.'},indent=2))

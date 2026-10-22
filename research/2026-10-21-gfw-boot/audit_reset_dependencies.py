"""File-only reset/firmware lifecycle comparison at immutable source pins."""
import hashlib
import json
import re
import sys
from pathlib import Path

PINS={'615.71.09':'61dcc93722ecb418bb5f2e00923f05b4b8051dd1',
      '615.78.08':'ca2d03e6fafd4d4b56b383497d931c25b283bfcf'}
FUNCTIONS={
 'kbifDoFunctionLevelReset_TU102':'src/nvidia/src/kernel/gpu/bif/arch/turing/kernel_bif_tu102.c',
 'kbifClearDownstreamReadCounter_GA100':'src/nvidia/src/kernel/gpu/bif/arch/ampere/kernel_bif_ga100.c',
 'kbifDoSecondaryBusHotReset_GM107':'src/nvidia/src/kernel/gpu/bif/arch/maxwell/kernel_bif_gm107.c',
 'kgspInitRm_IMPL':'src/nvidia/src/kernel/gpu/gsp/kernel_gsp.c',
 'kgspTeardown_TU102':'src/nvidia/src/kernel/gpu/gsp/arch/turing/kernel_gsp_tu102.c'}


def function(text,name):
    match=re.search(r'(?m)^(?:[A-Za-z_][A-Za-z0-9_]*[ \t*]+)*'+re.escape(name)+r'\s*\(',text)
    if not match:raise ValueError('Missing source function '+name)
    start=match.start() if not match.group().startswith(name) else text.rfind('\n',0,match.start()-1)+1
    opening=text.index('{',match.start());depth=0
    for i in range(opening,len(text)):
        if text[i]=='{':depth+=1
        elif text[i]=='}':
            depth-=1
            if depth==0:return text[start:i+1],text[:start].count('\n')+1,text[:i+1].count('\n')+1
    raise ValueError('Unbalanced function')


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    directory=Path(sys.argv[1]);versions={};bodies={}
    for version,commit in PINS.items():
        root=directory/version;rows={};bodies[version]={}
        for name,path in FUNCTIONS.items():
            data=(root/path).read_bytes();body,start,end=function(data.decode(),name)
            rows[name]={'path':path,'source_sha256':sha(data),'source_bytes':len(data),
                        'function_text_sha256':sha(body.encode()),'start_line':start,'end_line':end,
                        'url':f'https://github.com/NVIDIA/open-gpu-kernel-modules/blob/{commit}/{path}'}
            bodies[version][name]=body
        versions[version]={'commit':commit,'functions':rows}
    primary=bodies['615.71.09'];boot=primary['kgspInitRm_IMPL']
    copied=Path(__file__).with_name('copied-flr-function.inc').read_text()
    copied_body,_,_=function(copied,'kbifDoFunctionLevelReset_TU102')
    if copied_body!=primary['kbifDoFunctionLevelReset_TU102']:
        raise ValueError('FLR replay body differs from pinned NVIDIA source')
    order=[boot.index(s) for s in ['kgspParseFwsecUcodeFromVbiosImg(',
                                  'kgspWaitForGfwBootOk_HAL(', '_kgspBootGspRm(']]
    assert order==sorted(order)
    assert 'kgspPrepareForFwsecSb_HAL(' not in boot
    body=primary['kbifDoFunctionLevelReset_TU102']
    assert body.index('gpuWaitForGfwBootComplete_HAL(')<body.index('kbifClearDownstreamReadCounter_HAL(')
    chip_path='src/nvidia/generated/g_chips2halspec_nvoc.c'
    chips=(directory/'615.71.09'/chip_path).read_bytes()
    match=re.search(r'// GA102\s+else if\(arch == 0x17 && impl == 0x2\)\s*\{\s*pChipHal->__nvoc_HalVarIdx = (\d+);',chips.decode())
    if not match:raise ValueError('GA102 source identity changed')
    index=int(match[1]);dispatch_path='src/nvidia/generated/g_kernel_bif_nvoc.c'
    dispatch=(directory/'615.71.09'/dispatch_path).read_bytes()
    block=dispatch.decode().split('// kbifClearDownstreamReadCounter --',1)[1].split('// kbifDoSecondaryBusResetOrFunctionLevelReset --',1)[0]
    mask=int(re.search(r'& (0x[0-9a-f]+)UL',block)[1],16)
    assert index>>5==1 and (1<<(index&31))&mask
    assert 'kbifClearDownstreamReadCounter_GA100' in block
    extra=[]
    for path,start,end in [(chip_path,45,53),(dispatch_path,1496,1505),
       ('src/common/inc/swref/published/ampere/ga100/dev_nv_xve.h',27,33),
       ('src/common/sdk/nvidia/inc/nvstatuscodes.h',27,29),
       ('src/common/sdk/nvidia/inc/nvstatuscodes.h',114,116)]:
        data=(directory/'615.71.09'/path).read_bytes()
        extra.append({'path':path,'sha256':sha(data),'line_start':start,'line_end':end,
                      'excerpt':'\n'.join(data.decode().splitlines()[start-1:end])})
    linux=(directory/'linux-pci.c').read_bytes();linux_text=linux.decode();linux_rows=[]
    for name in ['pci_reset_secondary_bus','pci_bridge_secondary_bus_reset']:
        f,start,end=function(linux_text,name)
        linux_rows.append({'function':name,'start_line':start,'end_line':end,'text':f})
    adapter=(directory/'ms7d25-recover.py').read_bytes()
    print(json.dumps({'versions':versions,
         'nearby_version_function_text_identical':{name:bodies['615.71.09'][name]==bodies['615.78.08'][name] for name in FUNCTIONS},
         'ga102_dispatch':{'source_chip_hal_index':index,'mask':hex(mask),'target':'kbifClearDownstreamReadCounter_GA100','proof':extra},
         'source_decoded_findings':[
          'FWSEC is parsed before the GFW readiness gate; normal runtime bootstrap follows the gate.',
          'The selected kgspInitRm source function has no explicit FWSEC-SB preparation fallback at that gate.',
          'Vendor FLR waits for GFW readiness before downstream-counter cleanup; an error jumps past cleanup. The separate copied-source C replay checks this path.',
          'The exact-source GA102 dispatch selects the GA100-named counter cleanup. A cross-architecture name alone was not used as evidence.',
          'FWSEC-SB exists in teardown, but its availability does not prove it can repair an incomplete boot under all hardware states.'],
         'linux_comparison':{'commit':'7d0a66e4bb9081d75c82ec4957c50034cb0ea449','path':'drivers/pci/pci.c','source_sha256':sha(linux),'reviewed_functions':linux_rows,
           'limit':'Core bridge reset uses a platform hook and waits for the downstream bus. This is not an audit of every platform override, device quirk or the installed distro kernel.'},
         'reviewed_adapter':{'repository':'bnelabs/ms7d25-gpu-recovery','commit':'1983fff1e6798652e6f82952f139a5e2186a41f7','path':'recover.py','sha256':sha(adapter),
           'scope':'restore_pci restores BARs, optional ReBAR and memory decode; it has no explicit NVIDIA downstream-counter-cleanup stage. No runtime omission is inferred from text search alone.'},
         'unresolved':['Actual counter value, pending status, causal connection to progress 0x1 and effectiveness of a cleanup intervention.',
                       'Production/debug firmware equivalence and physical survival of the step word across the attempted resets.',
                       'Safe applicability of manually starting FWSEC-SB before the normal boot gate.'],
         'next_discriminator':'Determine from copied firmware and loader dependencies whether the counter can affect pre-runtime GFW boot; do not assume that a missing later cleanup repairs an earlier boot failure.'},indent=2))


if __name__=='__main__':main()

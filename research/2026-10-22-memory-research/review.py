"""Review pinned, file-only utilities and queue layouts in a CPU sandbox.

No CUDA sources, setup scripts, dumpers, modifiers or exploit helpers execute.
All exercise inputs are synthetic. Upstream utilities stay outside active code.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PACKET=Path(__file__).resolve().parent
ROOT=PACKET.parent.parent


def checked_sources():
    manifest=json.loads((PACKET/'sources.json').read_text())
    for item in manifest['files']:
        raw=(ROOT/item['retained_file']).read_bytes()
        assert len(raw)==item['bytes']
        assert hashlib.sha256(raw).hexdigest()==item['sha256']
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==item['git_blob_sha1']
    return manifest


def module(path):
    spec=importlib.util.spec_from_file_location('reviewed_file_utility',ROOT/path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def queue_layout(header, scratch, label, hwasan=False):
    text=header.read_text()
    match=re.search(r'typedef struct (?:NV_ABI_STABLE )?GSP_MSG_QUEUE_ELEMENT\s*\{.*?\}\s*GSP_MSG_QUEUE_ELEMENT;',text,re.S)
    if not match:raise ValueError('missing pinned queue structure')
    legacy='NvU32 checkSum;' in match[0]
    c='''#include <stdint.h>
#include <stdio.h>
#include <stddef.h>
typedef uint8_t NvU8;
typedef uint32_t NvU32;
#define NV_ABI_STABLE
#define NV_DECLARE_ALIGNED(decl, alignment) decl __attribute__((aligned(alignment)))
typedef struct { unsigned char unknown_rpc_bytes[16]; } rpc_message_header_v;
typedef struct { NvU8 authTagBuffer[16]; } GSP_MSG_QUEUE_ENCRYPTION_TAG;
'''+match[0]+'\nint main(void) {\n'
    fields={'checkSum':'checkSum','seqNum':'seqNum','elemCount':'elemCount','rpc':'rpc'} if legacy else {
        'mctpMagic':'mctpMagic','mctpPayloadSize':'mctpPayloadSize','mctpHeader':'mctpHeader',
        'nvdmHeader':'nvdmHeader','no_cc_size':'noEncryption.nvdmPayloadSize',
        'no_cc_payload':'noEncryption.payload','cc_tag':'withEncryption.encryptionTag',
        'cc_size':'withEncryption.nvdmPayloadSize','cc_payload':'withEncryption.payload'}
    for name,field in fields.items():
        c+=f'printf("{name}=%zu\\n", offsetof(GSP_MSG_QUEUE_ELEMENT, {field}));\n'
    c+='return 0; }\n'
    source=scratch/(label+'.c');binary=scratch/label;source.write_text(c)
    command=['cc','-std=gnu11','-Wall','-Wextra','-Werror']
    if hwasan:command+=['-DGSPRM_HWASAN_ENABLE']
    subprocess.run(command+[str(source),'-o',str(binary)],check=True)
    output=subprocess.check_output([str(binary)],text=True)
    return dict(fields={k:int(v) for k,v in (s.split('=') for s in output.splitlines())},
                structure_sha256=hashlib.sha256(match[0].encode()).hexdigest(),
                hwasan=hwasan,
                limits='Copied structure compiled with integer aliases and a synthetic 16-byte RPC placeholder. Reported member offsets do not establish full RPC size, runtime queue selection, receiver safety or firmware compatibility.')


def main():
    manifest=checked_sources();results={}
    with tempfile.TemporaryDirectory(prefix='memory-review-') as directory:
        scratch=Path(directory)
        layout=module('vendor/memory-research/GeForge/fuzzer/scripts/gen_layout_1_bank.py')
        base=0x100000000;size=0x400000
        mapping={layout._norm_2mb_key(0x200000):base}
        cases=[]
        for pa,expected in [(0x200000,base),(0x3fffff,base+0x1fffff),(0x400000,None)]:
            got=layout.translate_pa(pa,mapping,base,size);assert got==expected
            cases.append(dict(input_synthetic_pa=hex(pa),translated_va=None if got is None else hex(got)))
        assert layout.translate_pa(0x200000,mapping,base+1,size) is None
        results['retained_map_translation']=dict(cases=cases,window_exclusion_preserved=True,
            limits='Explicit synthetic 2 MiB mapping only; missing mappings stay missing. No board hash, PA acquisition or GA102 runtime mapping is supplied.')

        extract=module('vendor/memory-research/GeForge/fuzzer/scripts/extract_PA-VA-2MB-Mapping.py')
        source=scratch/'synthetic-pagewalk.txt'
        source.write_text('0-->2MB-Page@0x200000 VA: 0x100000000\n1-->2MB-Page@0x200000 VA: 0x200000000\n')
        warnings=io.StringIO()
        with contextlib.redirect_stdout(warnings):parsed,aliases=extract.parse_file(source)
        assert parsed=={'0x200000':'0x100000000'}
        assert aliases=={'0x200000':{'0x100000000','0x200000000'}}
        results['mapping_aliases']=dict(default_export=dict(parsed),
            aliases={k:sorted(v) for k,v in aliases.items()},warning=warnings.getvalue().strip(),
            implication='The default JSON map keeps one VA; retain the alias set separately. This can be legitimate aliasing, not proof of corrupt page tables.')

        hops=scratch/'synthetic.hops';matches=scratch/'synthetic.online'
        hops.write_text('0\n1\n2\n');matches.write_text(''.join(str(i*0x200000)+'\n' for i in [0,1,2,10,11,12]))
        script=ROOT/'vendor/memory-research/GeForge/page-anchoring/scripts/align_anchor.py'
        result=subprocess.run([sys.executable,str(script),str(hops),str(matches),'--target-idx','512'],capture_output=True,text=True,check=True)
        assert 'page 0' in result.stdout and not result.stderr
        results['ambiguous_anchor']=dict(synthetic_fingerprint_pages=[0,1,2],
            synthetic_observed_pages=[0,1,2,10,11,12],equally_matching_candidates=[0,10],
            upstream_stdout=result.stdout.strip(),upstream_stderr=result.stderr,
            implication='Upstream picks the first highest score without reporting this tie. Its inferred PA is not unique evidence and must not become a measured address.')

        flips=module('vendor/memory-research/GDDRHammer/rowhammer/util/parse_flips.py')
        log=scratch/'synthetic-flips.txt'
        log.write_text('Bit-flip detected!\nObserved 1 bit-flip(s) in Row 7, Byte 3, Address 0x1234\nThe 2nd bit flipped from 0 to 1 (Data Pattern: synthetic)\n')
        rows=flips.parse_file(log);assert len(rows)==1
        total,complete,partial,unique,perbank=flips.summarize(rows)
        assert complete==1 and rows[0]['bank'] is None
        results['flip_record_without_bank']=dict(parsed=[{k:v for k,v in row.items() if k!='file'} for row in rows],
            upstream_summary=dict(total=total,complete=complete,partial=partial,unique=unique),
            implication='Upstream complete status excludes bank/address checks. Preserve missing bank and the source address domain; this fixture proves no physical bit flip.')

        delays=module('vendor/memory-research/GDDRHammer/rowhammer/util/process_delays.py')
        values=[1,2];index=delays.find_stable_delay_index(values);assert index==-1
        with contextlib.redirect_stdout(io.StringIO()):fallback=delays.compute_stable_value(values)
        assert fallback==1001
        results['no_stable_timing_window']=dict(input_synthetic=values,stable_index=index,
            upstream_fallback_delay=fallback,
            implication='No stable window was found. Retain that outcome instead of treating the numeric fallback as calibrated timing. Comment says index+2000 but implementation uses +1000; acquisition units/range must be checked separately.')

        paths=[ROOT/'vendor/memory-research'/('nvidia-'+v)/'message_queue_priv.h' for v in ['580.95.05','615.71.09','615.78.08']]
        old,current,nearby=[queue_layout(p,scratch,'layout'+str(i)) for i,p in enumerate(paths)]
        sanitized=queue_layout(paths[1],scratch,'layout-hwasan',True)
        assert old['fields']==dict(checkSum=32,seqNum=36,elemCount=40,rpc=48)
        assert current==nearby
        assert current['fields']['no_cc_payload']==24 and current['fields']['cc_payload']==40
        assert sanitized['fields']['no_cc_payload']==32 and sanitized['fields']['cc_payload']==48
        results['queue_layout_comparison']={'580.95.05':old,'615.71.09':current,'615.78.08':nearby,
            '615.71.09_hwasan':sanitized,
            'headers_byte_identical_615_pair':paths[1].read_bytes()==paths[2].read_bytes(),
            'implication':'GPUBreach legacy checksum/sequence/element-count offsets are not fields of the copied 615 MCTP/NVDM element. This format difference alone proves neither vulnerability remediation nor incident causality. Runtime transport, encryption and HWASAN build configuration are unknown.'}
    print(json.dumps(dict(checked_source_files=len(manifest['files']),results=results,
        limits='All utility fixtures and C aliases/structures are CPU-only. No CUDA application, attack, dumper, modifier, setup, live query or original smoke dispatcher ran. Third-party results are leads, not measurements of our GPU. These applications require a running CUDA/driver environment and provide no demonstrated recovery for the retained pre-runtime GFW_BOOT failure.'),indent=2))


if __name__=='__main__':main()

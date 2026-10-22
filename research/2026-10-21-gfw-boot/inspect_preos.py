"""Pinned ROM record 0x2f / BIT PRE_OS identity and copied code/data replays."""
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path
from compare_fwsec import INPUTS
from replay_early_gates import run

CODE_SHA='45ed86ec62e8ceba8fb402e472f5a3ceea206c37c22772e2ef922e78bf89c6fc'
FIELDS=['stored_size','uncompressed_size','virtual_entry','interface_offset',
        'imem_phys_base','imem_load_size','imem_virt_base','imem_sec_base',
        'imem_sec_size','dmem_offset','dmem_phys_base','dmem_load_size']


def sha(data):return hashlib.sha256(data).hexdigest()


def extract(path):
    rom=path.read_bytes();digest=sha(rom)
    if digest not in INPUTS.values():raise ValueError('Unrecognized copied ROM')
    parsed=json.loads(subprocess.check_output([sys.executable,str(Path(__file__).with_name('inspect_fwsec.py')),str(path)],text=True))
    def u32(p):return struct.unpack_from('<I',rom,p)[0]
    assert rom[0x5000:0x5008]==b'RFRD\x03\x00\x28\x00'
    container=u32(0x501c);table=container+u32(container+0x14)
    assert u32(table)&0xffffff==0x50102 and u32(table+4)==128
    count=rom[table+13];assert 1<=count<=0x74
    matches=[]
    for i in range(count):
        p=table+128+52*i;row=rom[p:p+52]
        if len(row)!=52:raise ValueError('Truncated record')
        if row[0]==2 and struct.unpack_from('<H',row,2)[0]&0xfff==0x2f:matches.append((i,p,row))
    assert len(matches)==1
    index,p,row=matches[0];n=struct.unpack_from('<I',row,8)[0]&0xfffff
    offset=parsed['expansion_image_file_offset']+struct.unpack_from('<I',row,4)[0]
    assert offset+n<=len(rom)
    payload=rom[offset:offset+n]
    assert hashlib.sha256(payload).digest()==row[20:52]
    entry=next(e for e in parsed['entries'] if e['application_id']==1 and e['target_id']==1)
    bit_offset=parsed['falcon_pointer_base_file_offset']+entry['descriptor_pointer_raw']
    assert bit_offset==offset
    desc=dict(zip(FIELDS,struct.unpack_from('<12I',payload)))
    assert desc['stored_size']==desc['uncompressed_size']==n-48
    assert desc['imem_phys_base']==desc['imem_virt_base']==desc['dmem_phys_base']==0
    assert desc['virtual_entry']==0 and desc['imem_sec_base']==desc['imem_sec_size']==0
    assert desc['dmem_offset']==desc['imem_load_size']
    code=payload[48:48+desc['imem_load_size']]
    start=48+desc['dmem_offset'];data=payload[start:start+desc['dmem_load_size']]
    assert len(data)==desc['dmem_load_size'] and start+len(data)==len(payload)
    assert sha(code)==CODE_SHA
    words={i:struct.unpack_from('<I',data,i)[0] for i in range(0,len(data),4)}
    prefix_reads=[]
    assert code[0x465:0x469]==bytes.fromhex('808c0500')
    for pc,stop,registers in [(0x2b0,0x2cc,[15,14,13,12,11,10,0,9]),
                              (0x46b,0x47d,[9,15,14,13,12,11])]:
        result=run(code,{},start_pc=pc,ranges=[(pc,stop)],stops={stop:'before_unmodeled_context'},
                   register_fixture={0:0x58c} if pc==0x46b else None,
                   memory_fixture=words,return_state=True)
        prefix_reads.append({'pc':hex(pc),'stop':hex(stop),
                             'entry_register_fixture':'r0=0x58c from copied instruction 0x465; intervening canary store excluded' if pc==0x46b else 'no additional initialized registers',
                             'copied_data_register_results':{f'r{i}':result['registers'][i] for i in registers},
                             'trace':result['trace']})
    item={'file':path.name,'rom_sha256':digest,'record_index':index,
          'record_file_offset':p,'record_raw':row.hex(),'payload_file_offset':offset,
          'payload_bytes':n,'payload_sha256':sha(payload),
          'bit_entry_raw':entry['raw'],'bit_descriptor_pointer_raw':entry['descriptor_pointer_raw'],
          'bit_resolved_descriptor_file_offset':bit_offset,
          'legacy_descriptor_raw':payload[:48].hex(),'legacy_descriptor':desc,
          'imem_file_offset':offset+48,'imem_sha256':sha(code),
          'dmem_file_offset':offset+start,'dmem_sha256':sha(data),
          'copied_data_prefix_reads':prefix_reads}
    return item,code,data


def main():
    if sys.argv[1]=='--compare':
        directory=Path(sys.argv[2]);rows=[];reference=None
        for name in INPUTS:
            item,_,data=extract(directory/name)
            if reference is None:reference=data
            assert len(data)==len(reference)
            changed=[i for i,(a,b) in enumerate(zip(reference,data)) if a!=b]
            item['dmem_byte_differences_from_msi']=[{'offset':hex(i),'msi_raw':reference[i],'this_raw':data[i]} for i in changed]
            item['changed_bytes']=len(changed);rows.append(item)
        print(json.dumps({'inputs':rows,
             'same_imem_all_four':len({r['imem_sha256'] for r in rows})==1,
             'same_dmem_all_four':len({r['dmem_sha256'] for r in rows})==1,
             'same_legacy_descriptor_all_four':len({r['legacy_descriptor_raw'] for r in rows})==1,
             'limits':'Same GA102 version family, differing board variants, no chronology inferred. Changed data is consumed by copied instruction prefixes; physical field meanings and runtime values remain unknown. No replacement firmware or recovery method is implied.'},indent=2))
        return
    item,code,data=extract(Path(sys.argv[1]));cases=[];instructions={}
    for row in item['copied_data_prefix_reads']:
        for step in row['trace']:instructions[step['firmware_imem_va']]=step['raw']
    for value in [0,1,0x200,0x80000000,0xffffffff]:
        for label,pc,stop,expected in [('clear',0x136,0x14e,value&0xfffffdff),
                                      ('set',0x15c,0x169,value|0x200)]:
            result=run(code,{},start_pc=pc,ranges=[(pc,stop)],stops={stop:'fragment_boundary'},
                       memory_fixture={0x140205e4:value},store_ranges=[(0x140205e4,0x140205e8)],
                       return_state=True)
            assert result['memory']['0x140205e4']==expected
            cases.append({'name':f'{label}_{value:08x}','input_synthetic':value,
                          'expected':expected,'result':result})
    ready=run(code,{},start_pc=0xfa,ranges=[(0xfa,0x10c)],stops={0x10c:'before_unexecuted_initialization'},
              memory_fixture={0x14001724:0x20000000},return_state=True)
    cases.append({'name':'entry_wait_ready','input_synthetic':0x20000000,'result':ready})
    rejected=False
    try:
        run(code,{},start_pc=0xfa,ranges=[(0xfa,0x10c)],stops={0x10c:'ready'},memory_fixture={0x14001724:0})
    except ValueError as error:
        if str(error)!='instruction budget':raise
        rejected=True
    assert rejected
    for case in cases:
        result=case['result'];trace=[]
        for step in result['trace']:
            pc=step['firmware_imem_va'];raw=step['raw']
            if pc in instructions:assert instructions[pc]==raw
            instructions[pc]=raw;trace.append([pc,step['next_pc']])
        result['trace']=trace;result.pop('memory',None);result.pop('registers',None)
    print(json.dumps({'component':item,'instructions':instructions,'cases_passed':len(cases),
         'entry_not_ready_rejected_by_budget':rejected,'cases':cases,
         'address_domains':'PCs are PRE_OS IMEM VAs, not FWSEC PCs. D[0x140205e4] and D[0x14001724] are large Falcon data-space operands. ROM/descriptor locations are file offsets. A physical PRI alias is not implemented or established by this replay.',
         'limits':'Copied code and copied data only. Writer/entry register values are synthetic. Clear stops before I[0x16c] and its predicate; initialization callback dispatch is unexecuted. A related low-address bit pattern is not proof of aperture semantics, installed-image identity, actual completion or safe reload.'},indent=2))


if __name__=='__main__':main()

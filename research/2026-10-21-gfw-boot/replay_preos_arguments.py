"""Copied FWSEC argument writer and PRE_OS return fragments, never hardware.

The interface walk is a checked file parser, not an emulated PIO reader.
PRI/IO completion, capacity, stack and callback returns are explicit fixtures.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path
from inspect_preos import extract
from replay_early_gates import SHA, run


def words(data, base=0):
    if len(data) % 4:raise ValueError('unaligned copied bytes')
    return {base+i:struct.unpack_from('<I',data,i)[0] for i in range(0,len(data),4)}


def interface(data, offset):
    if offset+4>len(data):raise ValueError('interface header outside copied DMEM')
    version,header,entry,count=data[offset:offset+4]
    if (version,header,entry)!=(1,4,8):raise ValueError('unrecognized interface layout')
    end=offset+header+entry*count
    if end>len(data):raise ValueError('interface entries outside copied DMEM')
    rows=[]
    for pos in range(offset+header,end,entry):
        ident,target=struct.unpack_from('<II',data,pos)
        if target+4>len(data):raise ValueError('interface target outside copied DMEM')
        rows.append({'entry_dmem_offset':hex(pos),'id':hex(ident),
                     'target_dmem_offset':hex(target),'raw':data[pos:pos+entry].hex(),
                     'target_first_word_raw':data[target:target+4].hex()})
    selected=[r for r in rows if r['id']=='0xe' and
              int.from_bytes(bytes.fromhex(r['target_first_word_raw'])[:2],'little')==1]
    if len(selected)!=1:raise ValueError('expected one ID 0xe/version 1 record')
    target=int(selected[0]['target_dmem_offset'],16)
    if target+12>len(data):raise ValueError('argument record outside copied DMEM')
    record=data[target:target+12]
    if struct.unpack_from('<HHH',record)!=(1,12,2):raise ValueError('unexpected argument header')
    return {'header_dmem_offset':hex(offset),'header_raw':data[offset:offset+4].hex(),
            'entries':rows,'selected_offset':hex(target),'original_record_raw':record.hex()},target,record


def main():
    rom,fwpath=map(Path,sys.argv[1:3]);fw=fwpath.read_bytes()
    if hashlib.sha256(fw).hexdigest()!=SHA:raise ValueError('wrong decoded FWSEC')
    component,preos,data=extract(rom)
    parsed,dest,record=interface(data,component['legacy_descriptor']['interface_offset'])
    fw_instructions={};pre_instructions={}

    def retain(result,catalog):
        for step in result['trace']:
            pc,raw=step['firmware_imem_va'],step['raw']
            if pc in catalog:assert catalog[pc]==raw
            catalog[pc]=raw
        # Full memory remains local; outputs retain outcomes and exact executed bytes.
        return {'stop_pc':result['stop_pc'],'stop_reason':result['stop_reason'],
                'events':result['events'],
                'trace':[[s['firmware_imem_va'],s['next_pc']] for s in result['trace']]}

    patch=run(fw,{},start_pc=0x44af,ranges=[(0x44af,0x44c7)],
              stops={0x44da:'before_parameter_publication_setup'},
              register_fixture={1:0x1000},memory_fixture=words(record,0x1000),
              store_ranges=[(0x1000,0x100c)],return_state=True)
    patched=b''.join(struct.pack('<I',patch['memory'][hex(i)]) for i in range(0x1000,0x100c,4))
    assert patched==bytes.fromhex('01000c000200000040000000')
    publication_setup=run(fw,{},start_pc=0x44da,ranges=[(0x44da,0x44ee)],
              stops={0x44ee:'before_writer_call'},register_fixture={1:0x1000},
              memory_fixture={0xe04c:dest},return_state=True)
    assert publication_setup['registers'][10:14]==[0xe018,0x1000,dest,12]
    writer_cases=[]

    def writer(name,changes=None,pri_changes=None,io_status=0,omit_capacity=False):
        regs={i:0 for i in range(5)}
        regs.update({10:0x2000,11:0x1000,12:dest,13:12})
        regs.update(changes or {})
        pri={0x10a108:0x10<<9,0x122118:0xa5a5a5bf,0x122128:0,
             0x143c:0,0x12212c:0}
        pri.update(pri_changes or {})
        if omit_capacity:del pri[0x10a108]
        stops={0xffff:'writer_return',**{p:'copied_trap_boundary' for p in
               [0x6b20,0x6b26,0x6b2e,0x6b38,0x6b40,0x6b5e,0x6b65,0x6b6f,0x6786]}}
        result=run(fw,pri,start_pc=0x6b04,
              ranges=[(0x6b04,0x6bbb),(0x66de,0x67bd),(0x1014,0x1067)],
              stops=stops,register_fixture=regs,
              memory_fixture={**words(patched,0x1000),0x2000:0x10a000,0xdffc:0xffff},
              store_ranges=[(0xdf00,0xe000)],calls=[0x66de,0x673a,0x1014],
              io_fixture={} if io_status is None else {0x1c000:io_status},initial_sp=0xdffc,
              expected_stop_sp=0xe000 if not changes and not pri_changes else
                  0xdfe4 if changes else 0xdfdc,
              return_state=True)
        events=result['events'];writes=[e for e in events if e['kind']=='synthetic_falcon_io_write']
        reconstructed=None
        if result['stop_pc']=='0xffff':
            assert [(int(e['address'],16),e['value']) for e in writes]==[
                pair for value in struct.unpack('<III',patched) for pair in
                [(0x1c100,0x10a1c4),(0x1c200,value),(0x1c000,0x800000f3)]]
            assert pri[0x10a1c0]==0x1000000|dest
            # File-only reconstruction from emitted data words. Auto-increment
            # is a source-backed adapter, not a simulated physical bus result.
            reconstructed=bytearray(data)
            position=dest
            for event in writes:
                if event['address']=='0x1c200':
                    struct.pack_into('<I',reconstructed,position,event['value']);position+=4
            assert reconstructed[dest:dest+12]==patched
        writer_cases.append({'name':name,'synthetic_arguments':regs,
              'synthetic_pri_initial':{hex(k):v for k,v in {0x10a108:0x10<<9,0x122118:0xa5a5a5bf,
                  0x122128:0,0x143c:0,0x12212c:0,**(pri_changes or {})}.items()},
              'synthetic_io_status':io_status,
              'reconstructed_argument_raw':None if reconstructed is None else reconstructed[dest:dest+12].hex(),
              'result':retain(result,fw_instructions)})
        return result

    writer('three_words_complete')
    for name,changes,pc in [
        ('null_engine',{10:0},0x6b20),('null_source',{11:0},0x6b26),
        ('unaligned_destination',{12:dest+1},0x6b2e),
        ('unaligned_source',{11:0x1001},0x6b38),('unaligned_size',{13:11},0x6b40),
        ('destination_at_capacity',{12:0x1000},0x6b5e),
        ('size_exceeds_capacity',{13:0x1004},0x6b65),
        ('span_exceeds_capacity',{12:0xffc},0x6b6f)]:
        assert writer(name,changes)['stop_pc']==hex(pc)
    assert writer('post_transfer_status_40_traps',pri_changes={0x122128:0x40000000})['stop_pc']=='0x6786'
    rejected=[]
    try:writer('transport_stalled',io_status=0x1000)
    except ValueError as error:
        if str(error)!='instruction budget':raise
        rejected.append({'name':'transport_stalled','outcome':'instruction budget, not firmware timeout'})
    else:raise AssertionError('stalled transport accepted')
    for name,options,message in [
        ('missing_capacity',{'omit_capacity':True},'missing synthetic PRI value 10a108'),
        ('missing_transport_status',{'io_status':None},'missing synthetic Falcon IO value 1c000')]:
        try:writer(name,**options)
        except ValueError as error:
            if str(error)!=message:raise
            rejected.append({'name':name,'outcome':message})
        else:raise AssertionError('missing service accepted')

    patched_data=bytearray(data);patched_data[dest:dest+12]=patched
    branch_cases=[]
    for label,flags,command in [('copied_default',1,0x16),('selector1',0,0x40),
                                ('word40_flag_retained',1,0x40),('flag_cleared_word16',0,0x16)]:
        fixture=bytearray(patched_data);struct.pack_into('<H',fixture,dest+6,flags)
        struct.pack_into('<I',fixture,dest+8,command)
        for start,stops in [(0x169,{0x1d5:'exit_callback_dispatch',0x176:'recurring_callback_dispatch'}),
                            (0x1fe,{0x25d:'return_tail',0x20b:'additional_cleanup_register_path'})]:
            result=run(preos,{},start_pc=start,ranges=[(start,start+0x10)],
                       stops=stops,memory_fixture=words(fixture))
            assert result['stop_pc']==hex((0x1d5 if flags==0 else 0x176) if start==0x169 else
                                           (0x25d if flags==0 else 0x20b))
            branch_cases.append({'name':label,'flag_halfword':flags,'raw_word_plus8':command,
                                 'result':retain(result,pre_instructions)})

    boundaries=[]
    for name,start,ranges,stops,calls in [
        ('first_init_callback',0x116,[(0x116,0x136)],{0x6c85:'unexecuted_init_callback'},[0x6c85]),
        ('third_exit_callback',0x1d5,[(0x1d5,0x1e5),(0x1ee,0x1fe),(0x6c83,0x6c85),(0x27b,0x27d)],
         {0x5e92:'unexecuted_exit_callback'},[0x6c83,0x27b,0x5e92])]:
        result=run(preos,{},start_pc=start,ranges=ranges,stops=stops,calls=calls,
                   memory_fixture=words(patched_data),expected_stop_sp=0xdffc,return_state=True)
        boundaries.append({'name':name,'result':retain(result,pre_instructions)})
    # Begin AFTER unexecuted exit callbacks. Stack return addresses are fixture values
    # taken from the copied call sites, not a retained runtime stack.
    return_cases=[]
    for status in [0,0x12340000,0xffffa5a5]:
        stack={0xdfe4:3,0xdfe8:2,0xdfec:1,0xdff0:0,0xdff4:0x79bc,0xdff8:0,0xdffc:0xc}
        result=run(preos,{},start_pc=0x1fe,
               ranges=[(0x1fe,0x20b),(0x25d,0x277),(0x79bc,0x79fd),(0x79ff,0x7a03)],
               stops={0x79f9:'before_unexecuted_crypto_cleanup'},calls=[0x79ff],
               initial_sp=0xdfe4,expected_stop_sp=0xdff8,
               memory_fixture={**words(patched_data),**stack,0x14001404:status,0x14001418:0xa5a5ffff},
               store_ranges=[(0x14001404,0x14001408),(0x14001418,0x1400141c)],return_state=True)
        assert result['memory']['0x14001404']==status
        assert result['memory']['0x14001418']==0xa5a55fff
        assert result['registers'][0]==status>>16
        return_cases.append({'input_synthetic_status_word':status,'returned_main_status':status>>16,
                 'post_scratch_word':result['memory']['0x14001418'],
                 'result':retain(result,pre_instructions)})
    # The cleanup routine itself exits at 0x7a85 before its trailing ret.
    # Do not substitute a return from it to make 0x79fd -> entry 0xc reachable.
    # Start after unexecuted crypto/IO/cauth operations, preserving that boundary.
    final=run(preos,{},start_pc=0x7a65,ranges=[(0x7a65,0x7a85)],
              stops={0x7a85:'before_cleanup_exit_instruction'},initial_sp=0xdff4,
              expected_stop_sp=0xdff4,return_state=True)
    assert final['registers']==[0]*16
    assert preos[0x7a85:0x7a87]==preos[0xc:0xe]==bytes.fromhex('f802')

    # The +8 word has a demonstrated bit consumer, without an invented command
    # name: the last initialization callback tests bit 6 before calling 0x1484.
    word_consumers=[]
    for label,command in [('copied_word16_skips',0x16),('selector1_word40_calls',0x40)]:
        fixture=bytearray(patched_data);struct.pack_into('<I',fixture,dest+8,command)
        result=run(preos,{},start_pc=0x5d51,ranges=[(0x5d51,0x5dbb)],
                   stops={0x1484:'unexecuted_bit6_selected_service',0xffff:'callback_return'},
                   calls=[0x1484],initial_sp=0xdffc,
                   expected_stop_sp=0xdff8 if command&0x40 else 0xe000,
                   memory_fixture={**words(fixture),0xdffc:0xffff,0x14001404:0xdeadbeef,0x14001418:0},
                   store_ranges=[(0x14001404,0x14001408),(0x14001418,0x1400141c)],return_state=True)
        word_consumers.append({'name':label,'argument_word':command,'result':retain(result,pre_instructions)})
    for service_status in [0,0x1234]:
        result=run(preos,{},start_pc=0x5d80,ranges=[(0x5d80,0x5dbb)],
                   stops={0x5c8f:'unexecuted_next_service',0xffff:'callback_return'},calls=[0x5c8f],
                   initial_sp=0xdffc,expected_stop_sp=0xdff8 if service_status==0 else 0xe000,
                   register_fixture={10:service_status},
                   memory_fixture={0xdffc:0xffff,0x14001404:0,0x14001418:0},
                   store_ranges=[(0x14001404,0x14001408),(0x14001418,0x1400141c)],return_state=True)
        if service_status:assert result['memory']['0x14001404']==service_status<<16
        word_consumers.append({'name':'continuation_after_unexecuted_1484',
                'service_return_is_synthetic':service_status,'result':retain(result,pre_instructions)})

    tables={}
    for label,base,count,stride in [('init',0x13c,data[0x1ac],4),
                                  ('recurring',0x164,data[0x1ad],8),('exit',0x18c,data[0x1ae],4)]:
        tables[label]=[{'entry_dmem_offset':hex(base+i*stride),
                        'raw':data[base+i*stride:base+(i+1)*stride].hex(),
                        'target_imem_va':hex(struct.unpack_from('<I',data,base+i*stride)[0])}
                       for i in range(count)]
    print(json.dumps({'fwsec_debug_sha256':SHA,'preos_imem_sha256':component['imem_sha256'],
        'preos_dmem_sha256':component['dmem_sha256'],'interface_file_parse':parsed,
        'selector1_patch':{'after_raw':patched.hex(),'result':retain(patch,fw_instructions)},
        'publication_call_setup':retain(publication_setup,fw_instructions),
        'writer_cases':writer_cases,'rejected':rejected,'preos_branch_cases':branch_cases,
        'copied_callback_tables':tables,'callback_boundaries':boundaries,
        'conditional_return_cases':return_cases,'cleanup_integer_tail':retain(final,pre_instructions),
        'argument_word_bit6_consumer':word_consumers,
        'cleanup_exit_instruction':{'pc':'0x7a85','raw':preos[0x7a85:0x7a87].hex()},
        'entry_exit_instruction':{'pc':'0xc','raw':preos[0xc:0xe].hex(),
             'reachability':'Not established: normal cleanup exits before its trailing ret and the startup epilogue.'},
        'fwsec_instructions':fw_instructions,'preos_instructions':pre_instructions,
        'address_domains':'Separate FWSEC/PRE_OS IMEM VAs; engine-object/source/stack are synthetic local DMEM. PRI operands and Falcon IO ports are distinct. Destination 0x1c comes from copied PRE_OS interface. Large PRE_OS D[0x140...] operands are not aliased to physical PRI.',
        'limits':'Interface walk is a file parser cross-checked against retained instructions; upstream firmware load/PIO reads are unexecuted. Writer executes copied control code with synthetic PRI and IO adapters. Capacity 4096 and transport completion/status are fixtures. IO writes are event records, not physical bus emulation. DMEM reconstruction uses documented auto-increment semantics, not observed GPU memory. Callback dispatch stops at first nontrivial init/exit targets; no whole callback sequence completes. A separate bit-6 consumer reaches unexecuted 0x1484; its continuation cases supply explicitly synthetic service returns. Return fragments start after the unexecuted exit callbacks and stop before crypto cleanup. A separate integer-register clearing tail reaches the cleanup exit; crypto, IO and cauth operations before that tail remain unexecuted. The normal copied cleanup exits before returning to the startup epilogue. No whole boot, installed-ROM identity, debug/production equivalence, outage diagnosis, actual HALTED result or recovery method is proven.'},indent=2))


if __name__=='__main__':main()

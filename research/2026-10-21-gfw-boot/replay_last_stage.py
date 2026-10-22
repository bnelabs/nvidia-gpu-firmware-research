"""Copied FWSEC final pre-progress-2 branches and one nested wait, CPU-only."""
import hashlib
import json
import sys
from pathlib import Path
from replay_early_gates import SHA, run

RANGES=[(0x4653,0x4757),(0x279a,0x282d),(0x37b0,0x38aa),(0x2f6b,0x2fd3)]
RET=0xf000


def stack():return {**{p:0xa5a5a5a5 for p in range(0xde00,0xe004,4)},0xe000:RET}


def main():
    image=Path(sys.argv[1]).read_bytes()
    if hashlib.sha256(image).hexdigest()!=SHA:raise ValueError('Wrong copied debug IMEM')
    cases=[]
    base={0x11823c:0x800000a0,0x118238:(3<<8)|(4<<20),
          0x1404:0x800,0x1418:0x12345fff,0x823824:0xffffffff,
          0x9a000c:0xffffffff,0x823b00:0x4000}
    specifications=[('step_state_2_bypasses_body',{0x11823c:0x820000a0},RET),
                    ('step_state_1_traps',{0x11823c:0x810000a0},0x4696),
                    ('step_state_3_traps',{0x11823c:0x830000a0},0x4696),
                    ('middle_field_fff_absent',{0x118238:(0xfff<<8)|(4<<20)},RET),
                    ('high_field_fff_absent',{0x118238:(3<<8)|(0xfff<<20)},RET),
                    ('middle_field_zero_leaves_flag_zero',{0x118238:4<<20},RET),
                    ('high_field_zero_leaves_flag_zero',{0x118238:3<<8},RET),
                    ('derived_words_present_loader_bypassed',{},RET),
                    ('conditional_823824_write',{0x1404:0x1800},RET),
                    ('conditional_823b00_write',{0x823b00:0xffffffff},RET),
                    ('loader_43a8_required_boundary',{0x1404:0x1000},0x46d8)]
    continuation=None
    for name,overrides,stop in specifications:
        pri={**base,**overrides};before=pri.copy()
        result=run(image,pri,start_pc=0x4653,ranges=RANGES,
                   stops={RET:'function_return',0x4696:'invalid_step_trap',0x46d8:'before_unexecuted_loader_43a8'},
                   register_fixture={i:0 for i in range(9)},memory_fixture=stack(),
                   calls=(0x279a,0x37b0,0x2f6b),store_ranges=[(0xde00,0xe004)],
                   expected_stop_sp=0xe004 if stop==RET else 0xdfe8,return_state=True)
        assert int(result['stop_pc'],16)==stop
        if stop==RET:
            assert result['registers'][10]==0 and (pri[0x11823c]>>24)&3==2
            assert pri[0x11823c]&0xfcffffff==before[0x11823c]&0xfcffffff
        if 'absent' in name or 'zero' in name:
            assert pri[0x1418]==(before[0x1418]&0xfffffc00)|0x44
        if name=='conditional_823824_write':assert pri[0x823824]==0xfffffffd
        if name=='conditional_823b00_write':assert pri[0x823b00]==0x4bff
        if stop==0x46d8:continuation=(result,pri.copy())
        derived={key:result['memory'][key] for key in ['0xdfec','0xdff0','0xdff4','0xdff8']}
        cases.append({'name':name,'inputs':{hex(k):v for k,v in before.items()},
                      'all_hardware_values_synthetic':True,'local_words':derived,'result':result})
    # This continuation supplies an explicit opaque-call result; the loader
    # itself and its successful initialization are not substituted as executed.
    assert continuation is not None
    first,pri0=continuation
    for status in [0,0xbc,0x9e]:
        pri=pri0.copy();registers={i:v for i,v in enumerate(first['registers']) if v is not None}
        registers[10]=status
        result=run(image,pri,start_pc=0x46dc,ranges=RANGES,initial_sp=0xdfe8,
                   stops={RET:'function_return'},register_fixture=registers,
                   memory_fixture={int(k,16):v for k,v in first['memory'].items()},
                   calls=(0x2f6b,),store_ranges=[(0xde00,0xe004)],
                   expected_stop_sp=0xe004,return_state=True)
        assert result['registers'][10]==status and (pri[0x11823c]>>24)&3==2
        cases.append({'name':f'opaque_loader_result_{status:x}',
                      'opaque_result_fixture':status,'step_word_after':pri[0x11823c],'result':result})
    # This selector-1 loader branch uses the HALTED wait, not the raw-bc poll.
    descriptor=run(image,{},start_pc=0x615f,ranges=[(0x615f,0x61f1)],
                   stops={RET:'descriptor_return'},register_fixture={10:1,11:0x2000},
                   memory_fixture={**stack(),**{p:0xa5a5a5a5 for p in range(0x2000,0x2018,4)}},
                   store_ranges=[(0xde00,0xe004),(0x2000,0x2018)],
                   calls=(),expected_stop_sp=0xe004,return_state=True)
    assert [descriptor['memory'][hex(p)] for p in range(0x2000,0x2014,4)]==[0x10a000,0x10b000,0x10ac00,0x10ae00,1]
    cases.append({'name':'selector_1_engine_descriptor','result':descriptor})
    branch=run(image,{},start_pc=0x447b,ranges=[(0x447b,0x44da)],stops={0x44da:'before_unexecuted_loader_setup'},
               register_fixture={4:1,1:0x2000},memory_fixture={0x2004:0xffff0000,0x2008:0xffffffff},
               store_ranges=[(0x2000,0x200c)],return_state=True)
    assert branch['registers'][0]==0xaa and branch['registers'][3]==3 and branch['memory']['0x2008']==0x40
    cases.append({'name':'selector_1_selects_raw_aa_mode','result':branch})
    branch=run(image,{},start_pc=0x4524,ranges=[(0x4524,0x452a)],
               stops={0x452a:'before_selected_halted_wait_669d',0x4532:'alternate_raw_bc_poll'},
               register_fixture={0:0xaa,1:0x2000},return_state=True)
    assert branch['stop_pc']=='0x452a'
    cases.append({'name':'raw_aa_selects_halted_wait_not_bc_poll','result':branch})
    halt_memory={**stack(),0x2000:0x10a000,0x2004:0x10b000}
    for core,selected,mode in [('falcon',0x10a100,0),('riscv',0x10b388,0x10)]:
        for values in [[0x10],[0,0x10]]:
            reads={selected:values.copy()}
            result=run(image,{0x10b668:mode},start_pc=0x669d,
                       ranges=[(0x663a,0x66de)],stops={RET:'halted_wait_return'},
                       register_fixture={0:0,10:0x2000},memory_fixture=halt_memory,
                       pri_read_sequences=reads,calls=(0x663a,),
                       store_ranges=[(0xde00,0xe004)],expected_stop_sp=0xe004,return_state=True)
            assert result['registers'][10]==1 and not reads[selected]
            assert len([e for e in result['events'] if e['address']==hex(selected)])==len(values)
            cases.append({'name':f'{core}_halted_after_{len(values)}_reads',
                          'all_hardware_values_synthetic':True,'core_select_fixture':mode,
                          'halt_reads_fixture':values,'result':result})
    # The helper reads its scratch operand twice. Demonstrate separate snapshots,
    # without claiming the hardware can or did change between the two accesses.
    sequence=[2<<8,5<<20]
    result=run(image,{},start_pc=0x279a,ranges=[(0x279a,0x282d)],
               stops={RET:'helper_return'},register_fixture={**{i:0 for i in range(5)},10:0x2000,11:0x2004,12:0x2008,13:0x200c},
               memory_fixture={**stack(),**{p:0xa5a5a5a5 for p in range(0x2000,0x2010,4)}},
               store_ranges=[(0xde00,0xe004),(0x2000,0x2010)],
               pri_read_sequences={0x118238:sequence},calls=(),expected_stop_sp=0xe004,return_state=True)
    assert not sequence
    assert [result['memory'][k] for k in ['0x2000','0x2004','0x2008']]==[0x2000,0x1e00,0x5000]
    cases.append({'name':'two_explicit_scratch_snapshots','all_hardware_values_synthetic':True,'result':result})
    waits=[]
    for name,values,ticks,stop in [
        ('ready_immediately',[0x200],[123],0x456c),
        ('ready_on_second_read',[0,0x200],[123,124],0x456c),
        ('exact_threshold_accepted',[0,0x200],[0,0x8000000],0x456c),
        ('over_threshold_timeout',[0,0],[0,0x8000001],0x4617),
        ('late_ready_still_timeout',[0,0x200],[0,0x8000001],0x4617),
        ('timer_wraparound',[0,0x200],[0xfffffff0,0x10],0x456c)]:
        reads={0x205e4:values.copy()};clock={0xb00:ticks.copy()}
        result=run(image,{},start_pc=0x4532,ranges=[(0x4532,0x456c)],
                   stops={0x456c:'wait_passed_next_branch',0x4617:'raw_bc_error_tail'},
                   pri_read_sequences=reads,io_read_sequences=clock,return_state=True)
        assert int(result['stop_pc'],16)==stop and not reads[0x205e4] and not clock[0xb00]
        if stop==0x4617:assert result['registers'][2]==0xbc
        waits.append({'name':name,'pri_reads_fixture':values,'falcon_io_ticks_fixture':ticks,'result':result})
    rejected=[]
    for label,kw,reason in [('stalled_timer',{'io_fixture':{0xb00:0}},'instruction budget'),
                           ('exhausted_timer_fixture',{'io_read_sequences':{0xb00:[0]}},'exhausted synthetic Falcon IO sequence b00')]:
        try:
            run(image,{0x205e4:0},start_pc=0x4532,ranges=[(0x4532,0x456c)],
                stops={0x456c:'ready',0x4617:'timeout'},**kw)
        except ValueError as error:
            if str(error)!=reason:raise
            rejected.append(label)
    assert len(rejected)==2
    try:
        run(image,{0x10b668:0,0x10a100:0},start_pc=0x669d,ranges=[(0x663a,0x66de)],
            stops={RET:'halted'},register_fixture={0:0,10:0x2000},memory_fixture=halt_memory,
            calls=(0x663a,),store_ranges=[(0xde00,0xe004)],expected_stop_sp=0xe004)
    except ValueError as error:
        if str(error)!='instruction budget':raise
        rejected.append('halted_bit_never_set')
    assert len(rejected)==3
    instructions={}
    for row in cases+waits:
        result=row['result'];trace=[]
        for step in result['trace']:
            pc=step['firmware_imem_va'];raw=step['raw']
            if pc in instructions:assert instructions[pc]==raw
            instructions[pc]=raw;trace.append([pc,step['next_pc']])
        result['trace']=trace
        result.pop('registers',None);result.pop('memory',None)
    print(json.dumps({'debug_imem_sha256':SHA,'instructions':instructions,
         'address_domains':'PCs are debug FWSEC Falcon IMEM VAs; scratch/PRI keys are synthetic GPU register operands. I[0xb00] is Falcon IO; output/stack words are synthetic Falcon data space.',
         'last_stage_cases_passed':len(cases),'wait_cases_passed':len(waits),'rejected_cases':rejected,
         'cases':cases,'wait_cases':waits,
         'limits':'No full loader execution, installed-byte identity, production equivalence or actual error attribution. Opaque loader results are explicit continuation fixtures. Selector 1 chooses raw-aa mode and the core HALTED wait; the raw-bc timed poll is an alternate branch. Timer threshold is raw 0x8000000 with unknown time unit/rate. Neither a stalled timer nor an unset HALTED bit is converted into an invented hardware timeout.'},indent=2))


if __name__=='__main__':main()

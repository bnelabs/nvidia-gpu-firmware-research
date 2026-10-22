"""Copied FWSEC entry/restart-state and following-gate replay; CPU data only."""
import hashlib
import json
import sys
from pathlib import Path
from replay_early_gates import run, SHA

ENTRY_RANGES=[(0x4d5c,0x4e87),(0x59a3,0x59ae),(0x3dbf,0x3dfe),(0x217c,0x21aa)]
FOLLOW_RANGES=[(0x4ec5,0x4f1a),(0x59bd,0x59ca),(0x2f26,0x2f6b)]


def main():
    image=Path(sys.argv[1]).read_bytes()
    if hashlib.sha256(image).hexdigest()!=SHA:raise ValueError('Wrong copied debug IMEM')
    cases=[]
    base={0x118c6c:0,0x11839c:0xff,0x11823c:0xa5a55a5a,
          0x100ce0:0,0x1180f4:0,0x1fa800:0x20,0x1180fc:0xffffffff,
          0x22410:0,0x12e0:1,0x1728:0}
    specifications=[('entry_preserves_step_word',{},0x4e87,None),
                    ('entry_initializes_step_word',{0x118c6c:1},0x4e87,None),
                    ('restart_rejects_nonzero_100ce0',{0x118c6c:1,0x100ce0:1},0x5888,0xb7),
                    ('restart_rejects_1180f4_high_bits',{0x118c6c:1,0x1180f4:0x10000},0x5888,0xb7),
                    ('restart_rejects_1fa800_bit5_clear',{0x118c6c:1,0x1fa800:0},0x5888,0xb7),
                    ('entry_rejects_record_0',{0x11839c:0},0x587c,0xba),
                    ('entry_record_1_accepted',{0x11839c:1},0x4e87,None),
                    ('entry_record_1_requires_12e0_bit0',{0x11839c:1,0x12e0:0},0x587c,0xb8),
                    ('entry_record_1_rejects_1728_nonzero',{0x11839c:1,0x1728:1},0x587c,0xbb)]
    for name,overrides,stop,error in specifications:
        pri={**base,**overrides};before=pri.copy()
        result=run(image,pri,start_pc=0x4d5c,ranges=ENTRY_RANGES,
                   stops={0x4e87:'before_progress_1',0x587c:'entry_error',0x5888:'entry_restart_error'},
                   register_fixture={n:0 for n in range(9)},
                   memory_fixture={0x1000000:0,0x1000008:0},
                   store_ranges=[(0xdf00,0xe000),(0x3410,0x341c),(0x1000000,0x1000100)],
                   calls=(0x3dbf,0x217c),expected_stop_sp=0xdf94,return_state=True)
        assert int(result['stop_pc'],16)==stop
        if error is not None:assert result['raw_r1']==error
        expected=0x8a000 if name=='entry_initializes_step_word' else before[0x11823c]
        assert pri[0x11823c]==expected
        cases.append({'name':name,'all_hardware_state_synthetic':True,
                      'inputs':{hex(k):v for k,v in sorted(before.items())},
                      'step_word_after':pri[0x11823c],'result':result})
    followbase={0x820434:1,0x8204f4:0,0x8204e4:0,0x1728:0,0x1724:0x8000000}
    specs=[('following_gates_accept_fuse_route',{},0,0x4f1a,None),
           ('following_gates_accept_falcon_io_route',{0x820434:0},0x100000,0x4f1a,None),
           ('following_gates_reject_both_routes',{0x820434:0},0,0x587c,0x213),
           ('following_selected_checks_pass',{0x8204f4:1,0x8204e4:1},0,0x4f1a,None),
           ('following_1728_mask_rejected',{0x8204f4:1,0x8204e4:1,0x1728:0x800000},0,0x587c,0x41b),
           ('following_1724_bit27_required',{0x8204f4:1,0x8204e4:1,0x1724:0},0,0x587c,0x2aa)]
    for name,overrides,io,stop,error in specs:
        pri={**followbase,**overrides};before=pri.copy()
        result=run(image,pri,start_pc=0x4ec5,ranges=FOLLOW_RANGES,
                   stops={0x4f1a:'before_12e0_predicate',0x587c:'following_gate_error'},
                   io_fixture={0x10200:io},calls=(0x2f26,),return_state=True)
        assert int(result['stop_pc'],16)==stop
        if error is not None:assert result['raw_r1']==error
        cases.append({'name':name,'all_hardware_state_synthetic':True,
                      'inputs':{hex(k):v for k,v in sorted(before.items())},
                      'falcon_io_inputs':{'0x10200':io},'result':result})
    # Two state selectors: value 2 can skip a step or select another callee.
    # Stop before the chosen callee/trap; no unknown initialization is stubbed.
    for label,start,low,ranges,stops,expected in [
        ('step_bits_1_0',0x500f,0,[(0x500f,0x5026)],
         {0x5026:'execute_step',0x515f:'bypass_step_body',0x5024:'trap_boundary'},
         [0x5026,0x5024,0x515f,0x5024]),
        ('step_bits_23_22',0x531d,22,[(0x531d,0x5338)],
         {0x5338:'select_callee_158e',0x5358:'select_callee_14f1',0x5332:'trap_boundary'},
         [0x5338,0x5332,0x5358,0x5332])]:
        for state in range(4):
            word=0x80000000 | (state << low)
            pri={0x11823c:word}
            result=run(image,pri,start_pc=start,ranges=ranges,stops=stops,
                       register_fixture={9:0xdf80,15:0},return_state=True)
            assert int(result['stop_pc'],16)==expected[state]
            cases.append({'name':f'{label}_value_{state}',
                          'all_hardware_state_synthetic':True,
                          'inputs':{'0x11823c':word},'result':result})
    rejected=[]
    for label,blob,inputs in [('unknown_instruction',image[:0x4ec5]+b'\xfe'+image[0x4ec6:],followbase),
                              ('missing_io',image,followbase)]:
        try:
            run(blob,inputs.copy(),start_pc=0x4ec5,ranges=FOLLOW_RANGES,
                stops={0x4f1a:'next',0x587c:'error'},calls=(0x2f26,))
        except ValueError:rejected.append(label)
    assert len(rejected)==2
    instructions={}
    for case in cases:
        path=[]
        for instruction in case['result']['trace']:
            key=instruction['firmware_imem_va']
            if key in instructions:assert instructions[key]==instruction['raw']
            instructions[key]=instruction['raw']
            path.append([key,instruction['next_pc']])
        case['result']['trace']=path
    print(json.dumps({'debug_imem_sha256':SHA,'instructions':instructions,
                      'address_domains':'PCs are copied debug Falcon IMEM VAs. PRI keys are modeled GPU register operands, IO 0x10200 is Falcon IO, and memory fixtures are Falcon data space. They are not interchangeable.',
                      'limits':'These are copied-code branches with synthetic hardware values and entry objects. No production equivalence, register survival across reset, complete initialization or actual failure attribution is established.',
                      'cases_passed':len(cases),'rejected_cases':rejected,'cases':cases},indent=2))


if __name__=='__main__':main()

"""Copied table constructor prefix and saved-register restore fragments only."""
import hashlib
import json
import sys
from pathlib import Path
from replay_early_gates import SHA, run


def main():
    image=Path(sys.argv[1]).read_bytes()
    if hashlib.sha256(image).hexdigest()!=SHA:raise ValueError('Wrong copied debug IMEM')
    # The selector-1 constructor prefix defines addresses/kinds, not saved values.
    # All data-space backing is explicit fixture memory, not a DMEM capture.
    memory={p:0 for p in range(0x8c84,0x8e04,4)}
    constructor=run(image,{},start_pc=0x5cde,ranges=[(0x5cde,0x5d3b)],
                    stops={0x5d3b:'before_unexecuted_predicate_3dbf'},
                    register_fixture={10:1},memory_fixture=memory,
                    store_ranges=[(0x8c84,0x8e04)],return_state=True)
    state={int(k,16):v for k,v in constructor['memory'].items()}
    expected=[0x118fd0,0x823800,0x80,0x1200a0,0x137f34,0x20324,0x2082c,0x20820]
    rows=[]
    for index,address in enumerate(expected):
        base=0x8c84+12*index
        assert state[base]==address and state[base+8]&255==1
        rows.append({'data_address':hex(base),'pri_operand':hex(address),
                     'kind_byte':1,'saved_value_status':'Runtime read by 0x5b2f, not produced by this constructor prefix',
                     'active_byte_status':'Runtime publication at 0x5bbc; fixture zero here is not an observed value'})
    assert state[0x8e00]&255==8
    # Execute an actual write followed by a separate readback fragment. Between
    # them only the synthetic device response changes; no instruction is patched.
    cases=[]
    for name,active,readback in [('restore_matches',1,0x2468ace0),
                                  ('restore_mismatch',1,0x13579bdf),
                                  ('inactive_row_skipped',0,None)]:
        address=expected[0];saved=0x2468ace0
        mem={0xdf80:0x8c84,0x8c84:address,0x8c88:saved,0x8c8c:0x101 if active else 1}
        pri={address:0xffffffff}
        first=run(image,pri,start_pc=0x5a36,ranges=[(0x5a36,0x5a57)],
                  stops={0x5a57:'after_write_before_readback',0x5a8d:'inactive_row_next'},
                  register_fixture={1:0,2:0,3:0xdf80,4:0},memory_fixture=mem,return_state=True)
        if not active:
            assert first['stop_pc']=='0x5a8d' and not first['events']
            cases.append({'name':name,'result':first});continue
        assert pri[address]==saved
        pri[address]=readback # Explicit synthetic readback response, not hardware.
        registers={i:v for i,v in enumerate(first['registers']) if v is not None}
        second=run(image,pri,start_pc=0x5a57,ranges=[(0x5a57,0x5a8d)],
                   stops={0x5a83:'readback_mismatch_trap',0x5a8d:'restored_row_next'},
                   register_fixture=registers,
                   memory_fixture={int(k,16):v for k,v in first['memory'].items()},
                   store_ranges=[(0x8c84,0x8c90)],return_state=True)
        if readback==saved:
            assert second['stop_pc']=='0x5a8d' and second['memory']['0x8c8c']==1
        else:
            assert second['stop_pc']=='0x5a83'
            assert pri[0x146c]==address and pri[0x1470]==readback
            assert second['memory']['0x8c8c']==0x101
        cases.append({'name':name,'saved_value_fixture':saved,'readback_fixture':readback,
                      'write_fragment':first,'result':second})
    rejected=False
    try:
        run(image,{},start_pc=0x5a36,ranges=[(0x5a36,0x5a57)],stops={0x5a57:'after_write'},
            register_fixture={2:0,3:0xdf80},
            memory_fixture={0xdf80:0x8c84,0x8c84:expected[0],0x8c8c:0x101})
    except ValueError as error:
        if str(error)!='unmodeled DMEM 8c88':raise
        rejected=True
    assert rejected
    instructions={}
    for result in [constructor]+[part for c in cases for part in [c.get('write_fragment'),c['result']] if part]:
        trace=[]
        for step in result['trace']:
            key=step['firmware_imem_va'];raw=step['raw']
            if key in instructions:assert instructions[key]==raw
            instructions[key]=raw;trace.append([key,step['next_pc']])
        result['trace']=trace
    print(json.dumps({'debug_imem_sha256':SHA,'instructions':instructions,
       'address_domains':'PCs are debug Falcon IMEM VAs; table/stack keys are synthetic Falcon data memory; PRI operands are synthetic GPU registers.',
       'table_stride':12,'selector_1_prefix_rows':rows,'constructor_prefix':constructor,
       'restore_cases_passed':len(cases),'missing_saved_value_rejected':rejected,'cases':cases,
       'source_decoded_relationship':'Main 0x5737 loads selector 1 before calling 0x59fe. Routine 0x5be3 selects existing table/count pointers. Constructor 0x5c9a fills addresses/kinds. Routine 0x5ab2 reads current register values into row+4 at 0x5b33 and marks row+9 at 0x5bbc after a modifying write/readback. Routine 0x59fe restores row+4 for active rows and clears row+9 only after a matching readback.',
       'limits':'Constructor prefix only: later predicates and conditional appended rows do not execute. Saved values, active flags, backing memory and readback responses are fixtures, not retained GPU state. Table values are not fixed boot defaults. No full save/modify/restore cycle, trap handler, production equivalence or recovery effectiveness is established.'},indent=2))


if __name__=='__main__':main()

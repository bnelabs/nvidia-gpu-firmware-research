"""Copied PRE_OS bit-6-selected input acquisition and handshake fragments.

All large D[] reads/writes are file-backed fixtures; no physical alias is
assumed. Opaque parsing, allocation and method results stay separate cases.
"""
import hashlib
import json
import struct
import sys
from pathlib import Path
from inspect_preos import extract
from compare_fwsec import INPUTS
from replay_early_gates import run


def words(data, base=0):
    return {base+i:struct.unpack_from('<I',data,i)[0] for i in range(0,len(data),4)}


def main():
    if sys.argv[1]=='--compare':
        rows=[]
        for name in INPUTS:
            item,image,data=extract(Path(sys.argv[2])/name)
            rows.append(dict(rom=name,rom_sha256=item['rom_sha256'],
                imem_sha256=item['imem_sha256'],dmem_sha256=item['dmem_sha256'],
                schema_table_raw=data[0x24c:0x2ec].hex(),
                type8_schema_raw=data[0x2ac:0x2b8].hex(),
                type8_format_raw=data[0x3fa:data.index(0,0x3fa)+1].hex(),
                acquisition_function_sha256=hashlib.sha256(image[0x1484:0x154c]).hexdigest(),
                consumer_function_sha256=hashlib.sha256(image[0x5c8f:0x5d51]).hexdigest()))
        keys=['schema_table_raw','type8_schema_raw','type8_format_raw',
              'acquisition_function_sha256','consumer_function_sha256']
        assert all(len({row[k] for row in rows})==1 for k in keys)
        print(json.dumps(dict(inputs=rows,identical_fields=keys,
             limits='Four copied GA102 board variants in version family 94.02.42.00; no chronology inferred. This compares copied code/schema, not acquired records, runtime guards, register responses, installed ROM or production FWSEC equivalence.'),indent=2))
        return
    component,code,data=extract(Path(sys.argv[1]));catalog={};cases=[];rejected=[]
    canary=0x13579bdf
    base={**words(data),0x5b8:canary,0x5bc:0,0x700:0,0x714:0,0x718:0,
          0xdffc:0xffff,0xdff4:0}

    def compact(result):
        for step in result['trace']:
            pc,raw=step['firmware_imem_va'],step['raw']
            if pc in catalog:assert catalog[pc]==raw
            catalog[pc]=raw
        return dict(stop_pc=result['stop_pc'],reason=result['stop_reason'],
                    events=result['events'],trace=[[s['firmware_imem_va'],s['next_pc']] for s in result['trace']])

    def acquire(name,first,second,guard=0,expected=0x1506,seed=None,omit=None):
        header=bytes(range(128))
        fixture={**base,**{p:0xa5a5a5a5 for p in range(0xa18,0xa98,4)},
                 **(seed or {}),0x5bc:guard<<16,0xdffc:0xffff,
                 0x14118238:(first<<8)|(second<<20)}
        fixture.update(words(header,0x14300000+(first<<12)))
        if omit is not None:del fixture[omit]
        result=run(code,{},start_pc=0x1484,
            ranges=[(0x1484,0x154c),(0x724a,0x72a1),(0x70e9,0x7148),
                    (0x722e,0x724a),(0x6f11,0x6f67),(0x6fa3,0x6fbf),(0x7091,0x7096)],
            stops={0x1506:'before_unexecuted_object_factory',0xffff:'acquisition_return'},
            register_fixture={0:0,1:0,2:0,3:0,4:0,5:0},memory_fixture=fixture,
            store_ranges=[(0xdf00,0xe000),(0x5bc,0x5c0),(0xa18,0xa98)],
            calls=[0x724a,0x70e9,0x6f11],initial_sp=0xdffc,
            expected_stop_sp=0xdfdc if expected==0x1506 else 0xe000,
            return_state=True,instruction_budget=5000)
        assert result['stop_pc']==hex(expected)
        assert (result['memory']['0x5bc']>>16)&255==1
        row=dict(name=name,synthetic_first_field=first,synthetic_second_field=second,
                 initial_guard_byte=guard,guard_after=1,result=compact(result))
        if expected==0x1506:
            copied=b''.join(struct.pack('<I',result['memory'][hex(i)]) for i in range(0xa18,0xa98,4))
            assert copied==header
            assert result['registers'][10]==first<<12
            assert result['registers'][11]==0x07060504
            row.update(header_fixture_raw=header.hex(),copied_header_sha256=hashlib.sha256(copied).hexdigest(),
                       factory_arguments={'r10_source_word':result['registers'][10],
                                          'r11_copied_header_plus4':result['registers'][11]})
        else:row['returned_raw_status']=result['registers'][10]
        cases.append(row);return result

    acquire('header_copied_before_factory',1,2)
    assert acquire('guard_already_set',1,2,guard=1,expected=0xffff)['registers'][10]==0x2010
    missing=acquire('first_field_zero',0,2,expected=0xffff)
    assert missing['registers'][10]==0x2011
    for name,a,b in [('second_field_zero',1,0),('first_sentinel',0xfff,2),('second_sentinel',1,0xfff)]:
        assert acquire(name,a,b,expected=0xffff)['registers'][10]==0x2011
    assert acquire('reader_range_rejected',0x200,2,expected=0xffff)['registers'][10]==0x2e8
    retry=acquire('second_call_after_missing_input',1,2,guard=1,expected=0xffff,
                  seed={int(k,16):v for k,v in missing['memory'].items()})
    assert retry['registers'][10]==0x2010
    for name,address in [('missing_source_fields',0x14118238),('missing_header_word',0x14301000)]:
        try:acquire(name,1,2,omit=address)
        except ValueError as error:
            if str(error)!=f'unmodeled DMEM {address:x}':raise
            rejected.append(dict(name=name,outcome=str(error)))
        else:raise AssertionError('missing acquisition input accepted')

    # Constructor stores following unexecuted allocator/zeroing calls. They
    # prove a method assignment, not that allocation or parsing succeeds.
    construction=run(code,{},start_pc=0x4445,ranges=[(0x4445,0x4495)],
        stops={0x4495:'before_constructor_return_tail'},register_fixture={0:0x1000,1:0x1000,2:0x1234},
        memory_fixture={0x1000:0x4000},store_ranges=[(0x4000,0x409c)],return_state=True)
    assert construction['memory']['0x4094']==0x4a76
    cases.append(dict(name='copied_method_assignment',allocator_object_is_synthetic=True,
                      method_offset='0x94',method_imem_va='0x4a76',result=compact(construction)))

    for label,pointer,target,status in [('factory_null',0,None,0x2013),
                                       ('factory_object_method',0x4000,0x4a76,None)]:
        result=run(code,{},start_pc=0x150a,ranges=[(0x150a,0x154c)],
            stops={0x4a76:'before_unexecuted_object_method',0xffff:'acquisition_return'},
            register_fixture={0:0,10:pointer},
            memory_fixture={**base,0xdfdc:2,0xdfe0:1,0xdfe4:0,0xdff8:canary,
                            0x4094:construction['memory']['0x4094']},
            store_ranges=[(0xa98,0xa9c)],calls=[0x4a76],initial_sp=0xdfdc,
            expected_stop_sp=0xdfd8 if target else 0xe000,return_state=True)
        if status is not None:assert result['registers'][10]==status
        cases.append(dict(name=label,factory_return_is_synthetic=pointer,
                          returned_raw_status=result['registers'][10] if status is not None else None,
                          result=compact(result)))
    for value in [0,5]:
        result=run(code,{},start_pc=0x1520,ranges=[(0x1520,0x154c)],
            stops={0xffff:'acquisition_return'},register_fixture={0:0,10:value},
            memory_fixture={**base,0xdfdc:2,0xdfe0:1,0xdfe4:0,0xdff8:canary},
            initial_sp=0xdfdc,return_state=True)
        assert result['registers'][10]==(0x2000+value if value else 0)
        cases.append(dict(name='continuation_after_unexecuted_method',method_return_is_synthetic=value,
                          returned_raw_status=result['registers'][10],result=compact(result)))

    lookup=run(code,{},start_pc=0x1346,ranges=[(0x1346,0x13a5)],stops={0x13a5:'before_record_parse_call'},
        register_fixture={0:0,1:0,10:8,11:0xaa0},memory_fixture={**base,0xaa0:0},
        initial_sp=0xdffc,expected_stop_sp=0xdff0,return_state=True)
    assert lookup['registers'][0]==0x24c+8*12
    schema=data[0x2ac:0x2b8]
    assert schema[:3]==b'RRL'
    assert lookup['registers'][10:15]==[0x2ac,0x3fa,0xaa1,0x2714,1]
    assert lookup['memory']['0xdff0']==0xffffffff
    format_end=data.index(0,0x3fa)
    cases.append(dict(name='type8_schema_selection',selected_dmem_offset='0x2ac',
                      copied_schema_raw=schema.hex(),ascii_tag_only='RRL',
                      format_dmem_offset='0x3fa',copied_format_raw=data[0x3fa:format_end+1].hex(),
                      copied_format_ascii=data[0x3fa:format_end].decode('ascii'),
                      parser_call_arguments={f'r{i}':lookup['registers'][i] for i in range(10,15)},
                      parser_stack_argument=lookup['memory']['0xdff0'],result=compact(lookup)))

    handshakes=[]
    def consume(name,index=0,selector=0,mask=0,poll=None,capacity=512,count=1,stop=0xffff,service_status=0,header_word=1):
        command=0x149001f0+(index<<14)+(selector<<2)
        memory={0x2714:header_word,0x2730:capacity,0x2734:count,0x273c:index|(selector<<5),
                0x2748:0xabcdef7c,0x14820c14:mask,
                0xdfec:3,0xdff0:2,0xdff4:1,0xdff8:0,0xdffc:0xffff}
        sequence={} if poll is None else {command:list(poll)}
        result=run(code,{},start_pc=0x5c9b,ranges=[(0x5c9b,0x5d51)],
            stops={0xffff:'consumer_return',0x5cbb:'capacity_trap',0x5cc8:'count_trap',
                   0x5cf1:'index_trap',0x5d40:'completion_trap'},
            register_fixture={0:0,1:0,2:0,3:0,10:service_status},memory_fixture=memory,
            store_ranges=[(command,command+4),(command+8,command+12)],
            dmem_read_sequences=sequence,record_memory_events=True,initial_sp=0xdfec,
            expected_stop_sp=0xe000 if stop==0xffff else 0xdfec,return_state=True)
        assert result['stop_pc']==hex(stop)
        stores=[e for e in result['events'] if e['kind']=='dmem_store']
        if stop==0xffff and header_word and capacity and count and not(mask & (1<<index)) and service_status==0:
            assert [(int(e['address'],16),e['value']) for e in stores]==[(command+8,0xabcdef7d),(command,0x7d)]
        elif mask or service_status or count==0 or capacity==0 or header_word==0:assert not stores
        handshakes.append(dict(name=name,synthetic_fields=dict(index=index,selector=selector,mask=mask,
                capacity=capacity,count=count,prior_service_status=service_status,header_word=header_word),
                synthetic_command_read_sequence=poll,
                large_data_command_operand=hex(command),result=compact(result)))

    consume('record_handshake_completes',poll=[1,1,0x100])
    consume('index5_second_selector',index=5,selector=1,poll=[0x100])
    consume('masked_index_skips',mask=1)
    consume('empty_count_skips',count=0)
    consume('zero_header_skips',header_word=0)
    consume('zero_capacity_skips',capacity=0)
    consume('prior_service_error_skips',service_status=0x2029)
    consume('wrong_capacity_traps',capacity=511,stop=0x5cbb)
    consume('count_above_capacity_traps',count=513,stop=0x5cc8)
    consume('index6_traps',index=6,stop=0x5cf1)
    consume('busy_clear_completion_bit_missing',poll=[0],stop=0x5d40)
    for name,options,message in [
        ('busy_never_clears',{'poll':[1]*500},'instruction budget'),
        ('missing_poll_value',{'poll':[]},'exhausted synthetic DMEM sequence 149001f0')]:
        try:consume(name,**options)
        except ValueError as error:
            if str(error)!=message:raise
            rejected.append(dict(name=name,outcome=message))
        else:raise AssertionError('incomplete handshake accepted')

    print(json.dumps(dict(component=component,instructions=catalog,acquisition_cases=cases,
        handshake_cases=handshakes,rejected=rejected,
        address_domains='PCs are PRE_OS Falcon IMEM VAs. Copied schema/source data offsets and synthetic stack/object pointers are local D[] addresses. 0x14118238, 0x14300000+offset, 0x14820c14 and 0x149001f0+offset remain large Falcon D[] operands, not silently aliased to physical GPU PRI or PCI configuration.',
        limits='All large data values, reader configuration, header bytes, canary, objects and poll results are synthetic. Only the selected aligned mode-0 reader path executes; upper-window and DMA modes remain excluded. The input guard is local DMEM state, not proven persistent across boots; startup clears BSS. Factory/method/record-loader services remain unexecuted or separated explicit continuation inputs. RRL is an observed three-byte tag, not a proven expanded name or physical purpose. Handshake records are synthetic; source metadata and hardware meanings are unknown. No complete startup, installed image identity, debug/production equivalence, actual failed dependency or working recovery is established.'),indent=2))


if __name__=='__main__':main()

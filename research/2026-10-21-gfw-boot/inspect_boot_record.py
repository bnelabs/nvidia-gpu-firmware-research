"""Decode one copied GA102 boot record and replay its bounded consumer bytes."""
import hashlib
import json
import struct
import sys
from pathlib import Path
from replay_early_gates import SHA, run

ROM_SHA='6dd01dee331f4d0faf5dbd8bc58e31dd58eb88c7d403c7f7ae13e412927e8711'


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    rom=Path(sys.argv[1]).read_bytes();image=Path(sys.argv[2]).read_bytes()
    if sha(rom)!=ROM_SHA or sha(image)!=SHA:raise ValueError('Unrecognized copied artifact')
    def u32(p):return struct.unpack_from('<I',rom,p)[0]
    # These pinned container offsets are checked against raw signatures/lengths.
    # They are not a universal parser or a live PROM address translation.
    directory=0x5000
    assert rom[directory:directory+8]==b'RFRD\x03\x00\x28\x00'
    container=u32(directory+0x1c)
    assert u32(container)==0x30 and u32(container+4)==0x1c
    table=container+u32(container+0x14)
    assert u32(table)&0xffffff==0x50102 and u32(table+4)==0x80
    assert struct.unpack_from('<H',rom,table+8)[0]==2
    count=rom[table+13]
    assert 1<=count<=0x74 and table+0x80+count*52<=len(rom)
    records=[]
    for index in range(count):
        p=table+0x80+index*52;row=rom[p:p+52]
        assert row[0]==2
        if struct.unpack_from('<H',row,2)[0]&0xfff==0x41:records.append((index,p,row))
    assert len(records)==1
    index,p,row=records[0]
    length=struct.unpack_from('<I',row,8)[0]&0xfffff
    assert length==0x81
    digest=row[20:52]
    # Independent file-only discriminator: every possible 129-byte window.
    # A matching digest does not authenticate a signature or installed firmware.
    matches=[offset for offset in range(len(rom)-length+1)
             if hashlib.sha256(rom[offset:offset+length]).digest()==digest]
    assert len(matches)==1
    payload_offset=matches[0];payload=rom[payload_offset:payload_offset+length]
    raw_offset=struct.unpack_from('<I',row,4)[0]
    assert payload_offset==0x2f600+raw_offset
    assert payload[0]<=64 and 1+payload[0]*2<=len(payload)
    values=list(struct.unpack_from('<'+'H'*payload[0],payload,1))
    # Firmware receives already parsed/copied data here. Loading, hash engine,
    # signature checks and reader hardware are deliberately not stubbed as passed.
    def words(address,data):
        result={}
        for i,byte in enumerate(data):
            key=(address+i)&~3
            result[key]=result.get(key,0) | byte<<(((address+i)&3)*8)
        return result
    primary=u32(table+0x28)&0xffff
    cases=[]
    for name,device,stop in [('primary_device_matches',0x2204,0x523a),
                             ('primary_device_differs',0x2205,0x51ed)]:
        result=run(image,{0x88000:(device<<16)|0x10de},start_pc=0x51a7,
                   ranges=[(0x51a7,0x51ed)],
                   stops={0x523a:'next_boot_stage',0x51ed:'unmodeled_getter_16fa'},
                   register_fixture={0:0x2000,1:0},
                   store_ranges=[(0xdf00,0xe100)],
                   memory_fixture=words(0x2000,rom[table:table+0x80]))
        assert int(result['stop_pc'],16)==stop
        cases.append({'name':name,'synthetic_device_id':device,'result':result})
    specs=[('copied_zero_list_fallback_enabled',0x2205,1,0,values,0x5995),
           ('copied_zero_list_fallback_disabled',0x2205,0,0,values,0x523a),
           ('synthetic_matching_list',0x2205,1,0,[0x2205],0x523a),
           ('synthetic_empty_list',0x2205,1,0,[],0x5995),
           ('getter_status_failure',0x2205,1,7,values,0x587c)]
    for name,device,getter_value,getter_status,entries,stop in specs:
        memory={0xe048:getter_status,**words(0x2f10,b'\x00\x00'+bytes([len(entries),0])),
                **words(0x2f14,struct.pack('<'+'H'*len(entries),*entries))}
        result=run(image,{},start_pc=0x51f1,ranges=[(0x51f1,0x523a)],
                   stops={0x523a:'next_boot_stage',0x5995:'raw_4c_error_boundary',0x587c:'getter_error'},
                   register_fixture={0:0xe048,1:0,2:device,10:getter_value},memory_fixture=memory)
        assert int(result['stop_pc'],16)==stop
        cases.append({'name':name,'synthetic_getter_status':getter_status,
                      'synthetic_getter_value':getter_value,'synthetic_device_id':device,
                      'list_provenance':'copied_candidate_record_41' if entries is values else 'synthetic_fixture',
                      'result':result})
    instructions={}
    for case in cases:
        trace=case['result']['trace'];case['result']['trace']=[]
        for step in trace:
            pc=step['firmware_imem_va'];raw=step['raw']
            if pc in instructions:assert instructions[pc]==raw
            instructions[pc]=raw
            case['result']['trace'].append([pc,step['next_pc']])
    print(json.dumps({'rom_sha256':ROM_SHA,'debug_imem_sha256':SHA,
       'address_domains':'ROM locations are file offsets. Consumers are debug Falcon IMEM VAs. D[0x2f12]/D[0x2f14] are synthetic Falcon data memory; 0x88000 is a synthetic GPU PRI operand.',
       'rom_directory':{'file_offset':directory,'raw':rom[directory:directory+40].hex()},
       'container':{'file_offset':container,'raw_header':rom[container:container+28].hex()},
       'table':{'file_offset':table,'raw_header':rom[table:table+128].hex(),'record_count':count,
                'primary_device_halfword_at_28':primary,'records_sha256':sha(rom[table+128:table+128+count*52])},
       'record_41':{'index':index,'file_offset':p,'raw':row.hex(),'raw_offset':raw_offset,
                    'raw_length_word':struct.unpack_from('<I',row,8)[0],
                    'digest_bytes_20_51':digest.hex(),'matching_sha256_window_file_offsets':matches,
                    'payload_file_offset':payload_offset,'payload_raw':payload.hex(),
                    'payload_sha256':sha(payload),'halfword_count':len(values),'halfwords':values,
                    'empirical_mapping':'first type-0xe0 image file start 0x2f600 plus record offset; independently digest-matched. This differs from the Falcon-ucode pointer expansion adjustment.'},
       'interpretation':'Copied debug consumer compares the primary device halfword, then conditionally checks the halfword list on a getter-dependent fallback path. No official table/field names are assigned.',
       'limits':'Candidate ROM only, not installed bytes. Full parser, signature/hash engine, real table publication and getter 0x16fa do not execute. Their success is not assumed. Getter results, hardware values and entry objects in the separated consumer fragments are synthetic. No actual boot failure or working reset is identified.',
       'cases_passed':len(cases),'instructions':instructions,'cases':cases},indent=2))


if __name__=='__main__':main()

"""File-only comparison of FWSEC in four retained GA102 VBIOS candidates."""
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import parse_vbios_bit as bit

INPUTS={
 'msi-3090-F4-candidate.rom':'6dd01dee331f4d0faf5dbd8bc58e31dd58eb88c7d403c7f7ae13e412927e8711',
 'evga-3090-94.02.42.00.0B.rom':'4ef3c1ab655035a370ea2e0db88d244e17a007fe9cc45c8bdaf2876062942bb5',
 'evga-3090-94.02.42.00.0F.rom':'4a04d081631e22697b3a07ce6e605747b37bcc77f6435aa7200d89c91de21ace',
 'evga-3090-94.02.42.00.44.rom':'42dd161e7cc6c55d8fb2b8085f55216bcdb568f06e8a86af1e403079c23f7533',
}


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    directory=Path(sys.argv[1]);rows=[]
    for name, expected in INPUTS.items():
        path=directory/name
        data=bit.read_artifact(path)
        if sha(data)!=expected:raise ValueError('Input hash mismatch: '+name)
        result=json.loads(subprocess.check_output([sys.executable,str(Path(__file__).with_name('inspect_fwsec.py')),str(path)],text=True))
        rom=bit.find_inner_rom(data);offset,header=bit.find_bit(data,rom)
        token=next(t for t in bit.parse_tokens(data,rom,offset,header) if t['id']==0x42 and t['ver'] in (1,2) and t['size']>=5)
        version,oem=struct.unpack_from('<IB',data,token['target'])
        decoded_version='.'.join(f'{x:02X}' for x in [version>>24,(version>>16)&255,(version>>8)&255,version&255,oem])
        row={'file':name,'file_sha256':expected,'bytes':len(data),
             'rom_version_from_bit_B':decoded_version,'version_field_file_offset':token['target'],
             'version_field_raw':data[token['target']:token['target']+5].hex(),
             'legacy_pci_device_id':result['images'][0]['device'],
             'provenance':'public download URL recorded in sibling source JSON' if name.startswith('msi') else 'pre-existing retained GA102 file and SHA256SUMS; original acquisition URL unresolved',
             'components':{}}
        for app,label in [(0x45,'debug'),(0x85,'production')]:
            entry=next(e for e in result['entries'] if e['application_id']==app)
            d=result['falcon_pointer_base_file_offset']+entry['descriptor_pointer_raw']
            values=struct.unpack_from('<9IHBBHH',data,d)
            descsize=values[0]>>16;imemsize=values[5];dmemsize=values[8]
            start=d+descsize;end=start+imemsize+dmemsize
            if (values[0]>>8)&255!=3 or end>len(data) or imemsize+dmemsize>values[1]:
                raise ValueError('Unsupported descriptor or bounds')
            imem=data[start:start+imemsize];dmem=data[start+imemsize:end]
            c={'descriptor_file_offset':d,'descriptor_bytes':descsize,'descriptor_sha256':sha(data[d:start]),
               'imem_file_offset':start,'imem_bytes':imemsize,'stored_imem_sha256':sha(imem),
               'dmem_file_offset':start+imemsize,'dmem_bytes':dmemsize,'stored_dmem_sha256':sha(dmem)}
            if app==0x45:
                decoded=subprocess.check_output(['openssl','enc','-d','-aes-128-ecb','-K','25EFCDAB896745231032547698BADCFE','-nopad'],input=imem)
                c['decoded_debug_imem_sha256']=sha(decoded)
            row['components'][label]=c
        rows.append(row)
    equality={}
    for component in ['debug','production']:
        fields=['descriptor_sha256','stored_imem_sha256','stored_dmem_sha256']
        if component=='debug':fields.append('decoded_debug_imem_sha256')
        equality[component]={key:len({r['components'][component][key] for r in rows})==1 for key in fields}
    print(json.dumps({'address_domain':'All offsets are ROM file offsets; component IMEM/DMEM are separate Falcon-engine domains. Hash equality is byte equality of stored artifacts, not installed/runtime identity.',
                      'version_source':{'commit':'61dcc93722ecb418bb5f2e00923f05b4b8051dd1','path':'src/nvidia/src/kernel/gpu/gsp/kernel_gsp_fwsec.c','lines':'75-88 BIT_DATA_BIOSDATA_BINVER'},
                      'limits':'Same GA102 PCI device ID and nearby VBIOS version family, different board vendors/variants. No chronology inferred from OEM suffix; no production-key decode or proof that every ROM component matches.',
                      'inputs':rows,'all_four_equal':equality},indent=2))


if __name__=='__main__':main()

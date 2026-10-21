"""File-only FWSEC inventory using pinned NVIDIA and nouveau layouts."""
import sys,json,struct,hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import parse_vbios_bit as bit
path=Path(sys.argv[1]);data=bit.read_artifact(path)
def need(off,n): bit.require(data,off,n,'FWSEC file range')
def u32(off):need(off,4);return struct.unpack_from('<I',data,off)[0]
rom=bit.find_inner_rom(data);chain=[];pos=rom
for _ in range(32):
 need(pos,0x1a)
 romsig=struct.unpack_from('<H',data,pos)[0]
 assert romsig in (0xaa55,0x4e56,0xbb77)
 pcir=pos+struct.unpack_from('<H',data,pos+0x18)[0];need(pcir,0x18)
 assert data[pcir:pcir+4] in (b'PCIR',b'NPDS',b'RGIS')
 units=struct.unpack_from('<H',data,pcir+0x10)[0]
 assert units>0
 image={'rom_signature_raw':data[pos:pos+2].hex(),'data_signature_raw':data[pcir:pcir+4].hex(),'pcir_off':hex(pcir),'vendor':hex(struct.unpack_from('<H',data,pcir+4)[0]),'device':hex(struct.unpack_from('<H',data,pcir+6)[0]),'image_size_512units':units,'code_type':data[pcir+0x14],'last_image':bool(data[pcir+0x15]&0x80)}
 length=struct.unpack_from('<H',data,pcir+0x0a)[0]
 npde=(pcir+length+15)&~15;need(npde,4)
 subunits=image['image_size_512units'];last=image['last_image']
 if data[npde:npde+4]==b'NPDE':
  need(npde,10)
  revision,size,subunits=struct.unpack_from('<HHH',data,npde+4)
  assert revision in (0x100,0x101) and size>=10
  need(npde,size)
  if size>=11:last=bool(data[npde+10]&0x80)
  elif subunits<image['image_size_512units']:last=False
  image['nvidia_extension']={'file_offset':npde,'revision':revision,'size':size,'raw':data[npde:npde+size].hex(),'subimage_512units':subunits,'effective_last':last}
 assert subunits>0
 need(pos,subunits*512)
 chain.append({'file_offset':pos,**image})
 if last:break
 pos+=subunits*512
else:raise ValueError('Too many option-ROM images')
extensions=[r for r in chain if r['code_type']==0xe0]
assert extensions,extensions # NVIDIA selects the first type-0xe0 image.
legacy=next(row for row in chain if row['code_type']==0)
legacy_size=legacy.get('nvidia_extension',{}).get('subimage_512units',legacy['image_size_512units'])*512
ext_image=extensions[0]['file_offset']
ext=ext_image-legacy_size # Exact NVIDIA expansionRomOffset: extRomOffset minus baseRomSize.
bo,hdr=bit.find_bit(data,rom);tokens=bit.parse_tokens(data,rom,bo,hdr)
p=next(t for t in tokens if t['id']==0x70 and t['ver']==2 and t['size']>=4)
ptr=u32(p['target']);table=ext+ptr;need(table,6)
version,hsize,stride,count=struct.unpack_from('4B',data,table)
assert version==1 and hsize>=6 and stride>=6
need(table,hsize+stride*count)
result={'path':str(path),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'address_domain':'All absolute offsets are file offsets. Falcon pointers use the NVIDIA expansion adjustment: first type-0xe0 image offset minus base image size, added to raw pointer. All terms include the outer wrapper file mapping explicitly. IMEM/DMEM addresses remain separate firmware-engine domains.','option_rom_file_offset':rom,'images':chain,'expansion_image_file_offset':ext_image,'falcon_pointer_base_file_offset':ext,'base_image_size':legacy_size,'falcon_pointer_raw':ptr,'falcon_table_file_offset':table,'falcon_header_raw':data[table:table+hsize].hex(),'entries':[],'interpretation_limit':'Names decode copied-file metadata only. Signature authenticity, installed-byte identity, runtime selection and reset recovery are unverified.'}
for i in range(count):
 row=table+hsize+i*stride;app,target,descptr=struct.unpack_from('<BBI',data,row)
 entry={'index':i,'file_offset':row,'raw':data[row:row+stride].hex(),'application_id':app,'target_id':target,'descriptor_pointer_raw':descptr};result['entries'].append(entry)
 if app!=0x85:continue
 desc=ext+descptr;need(desc,44)
 vals=struct.unpack_from('<9IHBBHH',data,desc)
 names=['header','stored_size','pkc_data_offset','interface_offset','imem_phys_base','imem_load_size','imem_virt_base','dmem_phys_base','dmem_load_size','engine_id_mask','ucode_id','signature_count','signature_versions','reserved']
 d=dict(zip(names,vals));d['payload_encoding_status']='Unresolved from descriptor flag alone; clear bit is not proof of plaintext IMEM';ver=(d['header']>>8)&255;size=d['header']>>16
 assert d['header']&1 and ver==3 and size>=44
 assert not d['header']&4,'Descriptor encrypted bit set: this parser does not support this descriptor'
 need(desc,size)
 payload=desc+size;aligned=(d['stored_size']+255)&~255;need(payload,aligned)
 assert d['imem_load_size']<=aligned and d['imem_load_size']+d['dmem_load_size']<=aligned
 imem=payload;dm=payload+d['imem_load_size'];end=dm+d['dmem_load_size']
 assert d['pkc_data_offset']+384<=d['dmem_load_size']
 d.update(descriptor_file_offset=desc,descriptor_version=ver,descriptor_size=size,descriptor_sha256=hashlib.sha256(data[desc:desc+size]).hexdigest(),payload_file_offset=payload,payload_sha256=hashlib.sha256(data[payload:payload+d['stored_size']]).hexdigest(),imem_file_offset=imem,imem_sha256=hashlib.sha256(data[imem:imem+d['imem_load_size']]).hexdigest(),dmem_file_offset=dm,dmem_sha256=hashlib.sha256(data[dm:end]).hexdigest())
 interface=dm+d['interface_offset'];assert dm<=interface and interface+4<=end
 iv,ih,ie,ic=struct.unpack_from('4B',data,interface);assert iv==1 and ih>=4 and ie>=8 and interface+ih+ie*ic<=end
 d['interfaces']=[]
 for j in range(ic):
  off=interface+ih+ie*j;ident,dmem_offset=struct.unpack_from('<II',data,off)
  item={'id':ident,'dmem_offset':dmem_offset,'entry_file_offset':off};d['interfaces'].append(item)
  if ident!=4:continue
  mapper=dm+dmem_offset;assert dm<=mapper and mapper+64<=end
  sig,mv,ms=struct.unpack_from('<IHH',data,mapper)
  assert sig==0x50414d44 and mv==3 and ms>=64 and mapper+ms<=end
  fields=['cmd_in_buffer_offset','cmd_in_buffer_size','cmd_out_buffer_offset','cmd_out_buffer_size','nvf_img_data_buffer_offset','nvf_img_data_buffer_size','printf_buffer_hdr','ucode_build_time_stamp','ucode_signature','init_cmd','ucode_feature','ucode_cmd_mask0','ucode_cmd_mask1','multi_tgt_tbl']
  item['mapper']={'file_offset':mapper,'signature_raw':data[mapper:mapper+4].hex(),'version':mv,'size':ms,**dict(zip(fields,struct.unpack_from('<14I',data,mapper+8)))}
  for start,length in [('cmd_in_buffer_offset','cmd_in_buffer_size'),('cmd_out_buffer_offset','cmd_out_buffer_size')]:
   fits=item['mapper'][start]+item['mapper'][length]<=d['dmem_load_size']
   item.setdefault('buffer_address_domains',{})[start]={'raw':item['mapper'][start],'bytes':item['mapper'][length],'fits_copied_dmem':fits,'interpretation':'bounded copied DMEM range' if fits else 'unresolved firmware address; not dereferenced or relabeled as a file offset'}
 entry['fwsec_prod_source_decoded']=d
assert any('fwsec_prod_source_decoded' in e for e in result['entries'])
print(json.dumps(result,indent=2))

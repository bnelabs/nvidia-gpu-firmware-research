#!/usr/bin/env python3
"""Compile only the exact public RM_API struct and SDK types on CPU."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from offline_io import read_artifact
root=Path('vendor/open-gpu-kernel-modules-615.71.09')
path=root/'src/nvidia/inc/kernel/rmapi/rmapi.h'
raw=read_artifact(path)
text=raw.decode()
start=text.index('struct _RM_API\n{')
end=text.index('\n};',start)+3
declaration=text[start:end]
code='''#include <stddef.h>
#include <stdio.h>
#include "nvtypes.h"
#include "nvos.h"
#include "nvsecurityinfo.h"
typedef struct _RM_API RM_API;
'''+declaration+'''
int main(void) {
printf("{\\\"size\\\":%zu,\\\"Control\\\":%zu,\\\"AllocWithHandle\\\":%zu,\\\"Free\\\":%zu,\\\"defaultSecInfo\\\":%zu,\\\"pPrivateContext\\\":%zu,\\\"RS_PRIV_LEVEL_KERNEL\\\":%u,\\\"PARAM_LOCATION_KERNEL\\\":%u}\\n",
sizeof(RM_API),offsetof(RM_API,Control),offsetof(RM_API,AllocWithHandle),offsetof(RM_API,Free),offsetof(RM_API,defaultSecInfo),offsetof(RM_API,pPrivateContext),(unsigned)RS_PRIV_LEVEL_KERNEL,(unsigned)PARAM_LOCATION_KERNEL);
}
'''
with tempfile.TemporaryDirectory() as folder:
    source=Path(folder)/'layout.c'; binary=Path(folder)/'layout'
    source.write_text(code)
    command=['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-isystem',str(root/'src/common/sdk/nvidia/inc'),str(source),'-o',str(binary)]
    subprocess.run(command,check=True)
    layout=json.loads(subprocess.check_output([str(binary)],text=True))
    dependencies=subprocess.check_output(['cc','-std=c11','-M','-isystem',str(root/'src/common/sdk/nvidia/inc'),str(source)],text=True)
    vendor_headers=[]
    for file in sorted(set(dependencies.replace('\\\n',' ').split())):
        if file.startswith(str(root)+'/'):
            b=read_artifact(file)
            vendor_headers.append({'path':file,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
assert layout=={'size':240,'Control':56,'AllocWithHandle':8,'Free':24,'defaultSecInfo':184,'pPrivateContext':232,'RS_PRIV_LEVEL_KERNEL':2,'PARAM_LOCATION_KERNEL':1}
print(json.dumps({'source_path':str(path),'source_sha256':hashlib.sha256(raw).hexdigest(),
    'source_commit':'61dcc93722ecb418bb5f2e00923f05b4b8051dd1','declaration_start_line':text[:start].count('\n')+1,
    'extracted_struct_sha256':hashlib.sha256(declaration.encode()).hexdigest(),'compiled_source':code,
    'compiled_source_sha256':hashlib.sha256(code.encode()).hexdigest(),'layout':layout,
    'compiled_vendor_header_inputs':vendor_headers,
    'compiler':subprocess.check_output(['cc','--version'],text=True).splitlines()[0],
    'limits':'Host 64-bit C layout of exact isolated declaration, corroborated against copied RV64 offsets; no driver build, execution or runtime state.'},indent=2))

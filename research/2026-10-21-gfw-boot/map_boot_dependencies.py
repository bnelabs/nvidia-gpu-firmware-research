"""Conservative CFG of copied FWSEC SB main; calls remain opaque boundaries."""
import hashlib
import json
import re
import sys
from pathlib import Path
from replay_early_gates import SHA


def main():
    image=Path(sys.argv[1]).read_bytes()
    if hashlib.sha256(image).hexdigest()!=SHA:raise ValueError('Wrong copied IMEM')
    listing=Path(__file__).with_name('secure-boot-main.dis').read_bytes()
    nodes={}
    for line in listing.decode().splitlines():
        m=re.match(r'^([0-9a-f]{8}):\s+((?:[0-9a-f]{2} )*[0-9a-f]{2})\s+(?:[CB ]\s+)?(.*)$',line)
        if not m:raise ValueError('Unrecognized listing line: '+line)
        pc=int(m[1],16);raw=bytes.fromhex(m[2]);asm=m[3].strip()
        # Decoder labels are display metadata, not a source of instruction identity.
        asm=re.sub(r'^[BC]\s+','',asm)
        if image[pc:pc+len(raw)]!=raw:raise ValueError('Instruction byte mismatch')
        if '?' in asm or 'unknown' in asm:raise ValueError('Unresolved decode in main')
        nodes[pc]={'raw':raw.hex(),'assembly':asm,'next':pc+len(raw)}
    ordered=sorted(nodes)
    for a,b in zip(ordered,ordered[1:]):
        if nodes[a]['next']!=b:raise ValueError('Listing gap or overlap')
    edges={};calls=[]
    for pc,n in nodes.items():
        asm=n['assembly'];mnemonic=asm.split()[0]
        if mnemonic in ('lbra','bra'):
            target=int(re.search(r'0x([0-9a-f]+)$',asm)[1],16)
            raw=bytes.fromhex(n['raw'])
            if mnemonic=='lbra':decoded=int.from_bytes(raw[1:4],'little')
            elif raw[0] in (0xf4,0xf5):decoded=pc+int.from_bytes(raw[2:],'little',signed=True)
            elif raw[0]&0x3f==0x33:
                mode=raw[1]&15;imm=2 if mode in (10,11,14,15) else 1
                decoded=pc+int.from_bytes(raw[2+imm:],'little',signed=True)
            else:raise ValueError('Unsupported branch encoding')
            if decoded!=target:raise ValueError('Branch target disagrees with raw encoding')
            edges[pc]=[target] if mnemonic=='lbra' else [n['next'],target]
        elif mnemonic in ('ret','mpopaddret','trap','exit'):
            edges[pc]=[]
        else:
            edges[pc]=[n['next']]
        if mnemonic=='lcall':
            target=int(asm.split()[-1],16)
            if bytes.fromhex(n['raw'])[0]!=0x7e or int.from_bytes(bytes.fromhex(n['raw'])[1:],'little')!=target:
                raise ValueError('Call target mismatch')
            calls.append({'call_pc':hex(pc),'target_imem_va':hex(target),'raw':n['raw']})
    start,stop=0x4ec5,0x577a
    edges[stop]=[]

    def reachable(seed,graph):
        seen=set();todo=[seed]
        while todo:
            n=todo.pop()
            if n in seen:continue
            seen.add(n);todo.extend(x for x in graph.get(n,[]) if x in nodes)
        return seen

    forward=reachable(start,edges)
    reverse={n:[] for n in nodes}
    for n,children in edges.items():
        for child in children:
            if child in reverse:reverse[child].append(n)
    viable=forward & reachable(stop,reverse)
    dom={n:{n} if n==start else set(viable) for n in viable}
    changed=True
    while changed:
        changed=False
        for n in sorted(viable-{start}):
            predecessors=[p for p in reverse[n] if p in viable]
            new={n}|set.intersection(*(dom[p] for p in predecessors))
            if new!=dom[n]:dom[n]=new;changed=True
    relevant_calls=[c for c in calls if int(c['call_pc'],16) in viable]
    for c in relevant_calls:c['structurally_dominates_progress_2']=int(c['call_pc'],16) in dom[stop]
    journal=[]
    for pc,n in nodes.items():
        if 'mov $r10 0x11823c' not in n['assembly']:continue
        following=[];cursor=n['next']
        for _ in range(7):
            if cursor not in nodes:break
            following.append({'pc':hex(cursor),**nodes[cursor]});cursor=nodes[cursor]['next']
        field=next((re.search(r'extr \$r\d+ \$r10 0x([0-9a-f]+):0x([0-9a-f]+)',v['assembly']) for v in following if v['assembly'].startswith('extr ')),None)
        if field:
            journal.append({'read_address_load_pc':hex(pc),'bit_low':int(field[1],16),'bit_high':int(field[2],16),'following':following})
    print(json.dumps({'debug_imem_sha256':SHA,'listing_sha256':hashlib.sha256(listing).hexdigest(),
                      'start_pc':hex(start),'target_progress_2_pc':hex(stop),
                      'scope':'Instruction graph of copied debug main only. Calls are opaque and modeled as returning; returns, traps and exits are treated as terminal. Branch feasibility, trap-handler behavior and callee effects are not established. Structural dominance is not a full boot proof.',
                      'instructions_parsed':len(nodes),'can_reach_progress_2_in_main_graph':len(viable),
                      'call_sites_on_potential_routes':relevant_calls,
                      'step_word_reads':journal},indent=2))


if __name__=='__main__':main()

"""Execute bounded copied Falcon early-gate bytes with synthetic PRI services.

Unknown instructions, calls, memory and register inputs fail closed. This is
not a hardware model, reset implementation or full FWSEC emulator.
"""
import hashlib
import json
import sys
from pathlib import Path

SHA = 'dee558dc5bbe329bd7ff4d20bc7d7bd0d47d91c1c8d301e759dc6d66348d7ecb'
RANGES = [(0x4e87, 0x4ec5), (0x45b, 0x4ac), (0x3d1a, 0x3d6c),
          (0x3f1c, 0x3f7d), (0x587c, 0x5899), (0x58ce, 0x58ed),
          (0x59ae, 0x59bd)]
STOPS = {0x4ec5: 'next_boot_precondition', 0x58ed: 'error_tail',
         0x58d3: 'unmodeled_recovery_branch'}


def run(image, pri, initial_r0=0x55, *, start_pc=0x4e87,
        ranges=None, stops=None, register_fixture=None, memory_fixture=None,
        io_fixture=None, store_ranges=None, calls=None, expected_stop_sp=0xe000,
        return_state=False, pri_read_sequences=None, io_read_sequences=None,
        initial_sp=0xe000, dmem_read_sequences=None, record_memory_events=False,
        instruction_budget=500):
    regs = [None] * 16
    regs[0] = initial_r0
    for index, value in (register_fixture or {}).items():regs[index] = value
    memory = {0x5a0: 0x13579bdf}  # Synthetic canary, not a firmware dump.
    memory.update(memory_fixture or {})
    ranges = RANGES if ranges is None else ranges
    stops = STOPS if stops is None else stops
    calls = (0x45b, 0x3d1a, 0x3f1c) if calls is None else calls
    store_ranges = [(0xdf00, 0xe000)] if store_ranges is None else store_ranges
    pc, sp, zero, signed_less, unsigned_below = start_pc, initial_sp, None, None, None
    trace, events = [], []

    def readreg(index):
        if regs[index] is None:
            raise ValueError(f'uninitialized register r{index} at {pc:x}')
        return regs[index]

    def putreg(index, value):
        regs[index] = value & 0xffffffff

    def readmem(address):
        if address & 3:raise ValueError(f'unmodeled DMEM {address:x}')
        if dmem_read_sequences is not None and address in dmem_read_sequences:
            if not dmem_read_sequences[address]:raise ValueError(f'exhausted synthetic DMEM sequence {address:x}')
            value=dmem_read_sequences[address].pop(0)
            events.append({'kind':'synthetic_dmem_read','address':hex(address),'value':value})
            return value
        if address & 3 or address not in memory:
            raise ValueError(f'unmodeled DMEM {address:x}')
        return memory[address]

    def readsmall(address, width):
        value = 0
        for byte in range(width):
            pos = address + byte
            value |= ((readmem(pos & ~3) >> ((pos & 3)*8)) & 255) << (byte*8)
        return value

    def fixture_read(address, fixed, sequences, domain):
        if sequences is not None and address in sequences:
            if not sequences[address]:raise ValueError(f'exhausted synthetic {domain} sequence {address:x}')
            return sequences[address].pop(0)
        if fixed is None or address not in fixed:
            raise ValueError(f'missing synthetic {domain} value {address:x}')
        return fixed[address]

    def writesmall(address, value):
        if not any(a <= address and address+1 <= b for a,b in store_ranges):
            raise ValueError('byte store outside synthetic memory')
        aligned=address & ~3;shift=(address & 3)*8
        # Preserve only explicitly supplied neighboring fixture bytes.
        previous=readmem(aligned)
        memory[aligned]=(previous & ~(255<<shift)) | ((value & 255)<<shift)
        if record_memory_events:
            events.append({'kind':'dmem_store','address':hex(address),'width':1,'value':value & 255})

    def push(value):
        nonlocal sp
        sp -= 4
        memory[sp] = value

    def pop():
        nonlocal sp
        value = readmem(sp)
        sp += 4
        return value

    for _ in range(instruction_budget):
        if pc in stops:
            assert sp == expected_stop_sp, (hex(sp), hex(expected_stop_sp))
            result = {'stop_pc': hex(pc), 'stop_reason': stops[pc],
                      'raw_r1': regs[1], 'events': events, 'trace': trace}
            if return_state:
                result['registers'] = regs
                result['memory'] = {hex(k):v for k,v in sorted(memory.items())}
            return result
        if not any(a <= pc < b for a, b in ranges):
            raise ValueError(f'outside copied ranges at {pc:x}')
        op, arg = image[pc:pc+2]
        size, target = 0, None
        if op <= 0x0f or 0x40 <= op <= 0x4f or 0x80 <= op <= 0x8f or 0xd0 <= op <= 0xdf:
            size = 2 if op <= 15 else 3 if op <= 0x4f else 4 if op <= 0x8f else 5
            putreg(op & 15, int.from_bytes(image[pc+1:pc+size], 'little', signed=True))
        elif op == 0xf4 and arg == 0x30:
            size = 3
            sp += int.from_bytes(image[pc+2:pc+3], 'little', signed=True)
        elif op == 0xfe and arg >> 4 == 4 and image[pc+2] == 1:
            size = 3
            putreg(arg & 15, sp)
        elif op == 0xbf:
            size = 2
            putreg(arg & 15, readmem(readreg(arg >> 4)))
        elif op == 0x98:
            size = 3
            putreg(arg & 15, readmem(readreg(arg >> 4) + image[pc+2]*4))
        elif op == 0xbc and image[pc+2] & 15 == 8:
            size = 3
            putreg(image[pc+2] >> 4, readmem(readreg(arg >> 4)+readreg(arg & 15)*4))
        elif op in (0x18, 0x58, 0x3f, 0x7f):
            size = 3 if op in (0x18,0x58) else 2
            width = 2 if op in (0x58,0x7f) else 1
            address = readreg(arg >> 4) + (image[pc+2]*width if size==3 else 0)
            putreg(arg & 15, readsmall(address, width))
        elif op in (0xa0, 0xb5):
            size = 2 if op == 0xa0 else 3
            address = readreg(arg >> 4) + (image[pc+2]*4 if op == 0xb5 else 0)
            if address & 3 or not any(a <= address and address+4 <= b for a,b in store_ranges):
                raise ValueError('store outside synthetic stack')
            memory[address] = readreg(arg & 15)
            if record_memory_events:
                events.append({'kind':'dmem_store','address':hex(address),'width':4,'value':memory[address]})
        elif op == 0xb0 and arg & 15 == 1:
            size=3
            address=sp+image[pc+2]*4
            if not any(a<=address and address+4<=b for a,b in store_ranges):
                raise ValueError('store outside synthetic stack')
            memory[address]=readreg(arg >> 4)
        elif op in (0x20, 0x35):
            size = 2 if op == 0x20 else 3
            address=readreg(arg >> 4)+(image[pc+2] if op==0x35 else 0)
            writesmall(address,readreg(arg & 15))
        elif op in (0x60,0x75):
            size=2 if op==0x60 else 3
            address=readreg(arg >> 4)+(image[pc+2]*2 if op==0x75 else 0)
            value=readreg(arg & 15)
            writesmall(address,value);writesmall(address+1,value>>8)
        elif op == 0x10:
            size = 3
            value = (readreg(arg >> 4)+image[pc+2]) & 255
            putreg(arg & 15, value)
            zero = value == 0
        elif op in (0x90, 0x92):
            size = 3
            value = readreg(arg >> 4) + (image[pc+2] if op == 0x90 else -image[pc+2])
            putreg(arg & 15, value)
            zero = (value & 0xffffffff) == 0
        elif op == 0xb8 and image[pc+4] in (0,2):
            size=5
            immediate=int.from_bytes(image[pc+2:pc+4],'little')
            value=readreg(arg >> 4)+(immediate if image[pc+4]==0 else -immediate)
            putreg(arg & 15,value)
            zero=(value & 0xffffffff)==0
        elif op in (0xb2,0x32):
            size = 2
            putreg(arg & 15, readreg(arg >> 4) & (255 if op==0x32 else 0xffffffff))
        elif op in (0xbd,0x3d,0x7d) and arg & 15 == 4:
            size = 2
            putreg(arg >> 4, 0)
            zero = True
        elif op == 0xbb and image[pc+2]==2:
            size=3
            value=readreg(arg >> 4)-readreg(arg & 15)
            putreg(arg >> 4,value)
            zero=(value & 0xffffffff)==0
        elif op == 0xbc and image[pc+2] & 15 == 0:
            size=3
            value=readreg(arg >> 4)+readreg(arg & 15)
            putreg(image[pc+2] >> 4,value)
            zero=(value & 0xffffffff)==0
        elif op in (0xb0,0x30) and arg & 15 == 6:
            size = 3
            bits=32 if op==0xb0 else 8
            left, right = readreg(arg >> 4) & ((1<<bits)-1), image[pc+2]
            zero = left == right
            signed_less = (left ^ (1<<(bits-1))) < (right ^ (1<<(bits-1)))
            unsigned_below = left < right
        elif op in (0xa6, 0x66, 0x26):
            size = 2
            bits = 32 if op == 0xa6 else 16 if op == 0x66 else 8
            left, right = (readreg(arg >> 4) & ((1 << bits)-1),
                           readreg(arg & 15) & ((1 << bits)-1))
            zero = left == right
            signed_less = (left ^ (1 << (bits-1))) < (right ^ (1 << (bits-1)))
            unsigned_below = left < right
        elif op in (0xff, 0xfd):
            size = 3
            sub = image[pc+2] & 15
            if sub not in (4,5):raise ValueError('unsupported logical opcode')
            dst = image[pc+2] >> 4 if op == 0xff else arg >> 4
            value = readreg(arg >> 4) & readreg(arg & 15) if sub == 4 else readreg(arg >> 4) | readreg(arg & 15)
            putreg(dst, value)
            zero = value == 0
        elif op == 0xc4:
            size = 3
            value = readreg(arg >> 4) & image[pc+2]
            putreg(arg & 15, value)
            zero = value == 0
        elif op == 0xc5:
            size=3
            value=readreg(arg >> 4)|image[pc+2]
            putreg(arg & 15,value)
            zero=value==0
        elif op == 0xbc and image[pc+2] & 15 in (2,4):
            size=3
            left,right=readreg(arg >> 4),readreg(arg & 15)
            value=left-right if image[pc+2] & 15==2 else left << (right & 31)
            putreg(image[pc+2] >> 4,value)
            zero=(value & 0xffffffff)==0
        elif op in (0xe4,0xe5):
            size=4
            immediate=int.from_bytes(image[pc+2:pc+4],'little')
            value=(readreg(arg >> 4)&immediate if op==0xe4 else readreg(arg >> 4)|immediate)
            putreg(arg & 15,value)
            zero=value==0
        elif op == 0xe7:
            size=4
            immediate=int.from_bytes(image[pc+2:pc+4],'little')
            low,width=immediate & 31,(immediate >> 5)+1
            if low+width>32:raise ValueError('unsupported wide bit extraction')
            putreg(arg & 15,(readreg(arg >> 4)>>low)&((1<<width)-1))
        elif op == 0xf0 and arg & 15 in (2,3):
            size=3
            dst=arg >> 4;immediate=image[pc+2]
            if arg & 15==2:
                if immediate>31:raise ValueError('unsupported sign extension')
                mask=(1<<(immediate+1))-1;sign=1<<immediate
                value=((readreg(dst)&mask)^sign)-sign
                zero=value==0
            else:value=(readreg(dst)&0xffff)|(immediate<<16)
            putreg(dst,value)
        elif op in (0xf0, 0xf1) and arg & 15 in (4, 5):
            size = 3 if op == 0xf0 else 4
            dst = arg >> 4
            immediate = int.from_bytes(image[pc+2:pc+size], 'little')
            value = readreg(dst) & immediate if arg & 15 == 4 else readreg(dst) | immediate
            putreg(dst, value)
            zero = value == 0
        elif op == 0xc7:
            size = 3
            immediate = image[pc+2]
            low, width = immediate & 31, (immediate >> 5) + 1
            putreg(arg & 15, (readreg(arg >> 4) >> low) & ((1 << width)-1))
        elif op == 0xb6 and arg & 15 in (4,5):
            size = 3
            dst = arg >> 4
            value = readreg(dst) << image[pc+2] if arg & 15 == 4 else readreg(dst) >> image[pc+2]
            putreg(dst, value)
            zero = (value & 0xffffffff) == 0
        elif op == 0x95:
            size = 3
            value = readreg(arg >> 4) >> image[pc+2]
            putreg(arg & 15, value)
            zero = value == 0
        elif op == 0x94:
            size=3
            value=readreg(arg >> 4)<<image[pc+2]
            putreg(arg & 15,value)
            zero=(value & 0xffffffff)==0
        elif op == 0xcf and image[pc+2] == 0:
            size = 3
            address = readreg(arg >> 4)
            value=fixture_read(address,io_fixture,io_read_sequences,'Falcon IO')
            putreg(arg & 15,value)
            events.append({'kind':'synthetic_falcon_io_read','address':hex(address),'value':value})
        elif op == 0xfa and image[pc+2] in (0,1):
            size = 3
            events.append({'kind':'synthetic_falcon_io_write',
                           'address':hex(readreg(arg >> 4)), 'value':readreg(arg & 15),
                           'instruction':'iowrs' if image[pc+2] else 'iowr'})
        elif op == 0x3e:
            size = 4
            target = int.from_bytes(image[pc+1:pc+4], 'little')
        elif op in (0xf4, 0xf5) and arg in (0x08,0x0b,0x0c,0x0d,0x18,0x1b,0x1e):
            size = 3 if op == 0xf4 else 4
            if arg in (0x08,0x0c,0x0d,0x18):
                if unsigned_below is None or zero is None:raise ValueError('unmodeled unsigned comparison')
                taken=(unsigned_below if arg==0x08 else not unsigned_below if arg==0x18 else not(unsigned_below or zero) if arg==0x0c else unsigned_below or zero)
            elif arg == 0x1e:
                if signed_less is None:raise ValueError('unmodeled signed comparison')
                taken = signed_less
            else:
                if zero is None:raise ValueError('unmodeled flags')
                taken = zero if arg == 0x0b else not zero
            if taken:target = pc + int.from_bytes(image[pc+2:pc+size], 'little', signed=True)
        elif op in (0xb3,0x33) and arg & 15 in (0, 4, 9, 10, 11, 13, 14, 15):
            mode = arg & 15
            imm_size = 2 if mode in (10,11,14,15) else 1
            offset_size = 2 if mode in (9,11,13,15) else 1
            size = 2 + imm_size + offset_size
            immediate = int.from_bytes(image[pc+2:pc+2+imm_size], 'little')
            equal = (readreg(arg >> 4) & (0xff if op==0x33 else 0xffffffff)) == immediate
            if equal == (mode in (0, 9,10,11)):
                target = pc + int.from_bytes(image[pc+2+imm_size:pc+size], 'little', signed=True)
        elif op == 0xf9 and arg & 15 == 2:
            size = 2
            for r in range((arg >> 4) + 1):push(readreg(r))
        elif op == 0xf9 and arg & 15 == 5:
            size = 2
            call = readreg(arg >> 4)
            if call not in calls:raise ValueError(f'unmodeled indirect call {call:x}')
            push(pc+size)
            target = call
        elif op == 0xfb and arg & 15 == 1:
            size = 2
            for r in reversed(range((arg >> 4) + 1)):putreg(r, pop())
            target = pop()
        elif op == 0xfb and arg & 15 == 5:
            size = 3
            for r in reversed(range((arg >> 4) + 1)):putreg(r, pop())
            sp += int.from_bytes(image[pc+2:pc+3], 'little', signed=True)
            target = pop()
        elif op == 0xf8 and arg == 0:
            size, target = 2, pop()
        elif op == 0x7e:
            size = 4
            call = int.from_bytes(image[pc+1:pc+4], 'little')
            if call in (0x1117, 0x1171):
                address = readreg(10)
                if call == 0x1117:
                    value=fixture_read(address,pri,pri_read_sequences,'PRI')
                    putreg(10, value)
                    events.append({'kind': 'synthetic_read', 'address': hex(address), 'value': value})
                else:
                    value = readreg(11)
                    pri[address] = value
                    regs[10] = None
                    events.append({'kind': 'synthetic_write', 'address': hex(address), 'value': value})
                regs[9] = regs[15] = None  # Helpers clobber these; no invented return state.
                zero = None
            elif call in calls:
                push(pc + size)
                target = call
            else:
                raise ValueError(f'unmodeled call {call:x}')
        else:
            raise ValueError(f'unsupported bytes at {pc:x}: {image[pc:pc+6].hex()}')
        if op not in (0xa6, 0x66, 0x26) and not (op in (0xb0,0x30) and arg & 15 == 6):
            signed_less = unsigned_below = None
        trace.append({'firmware_imem_va': hex(pc), 'raw': image[pc:pc+size].hex(),
                      'next_pc': hex(pc+size if target is None else target)})
        pc = pc + size if target is None else target
    raise ValueError('instruction budget')


def main():
    image = Path(sys.argv[1]).read_bytes()
    if hashlib.sha256(image).hexdigest() != SHA:raise ValueError('wrong debug IMEM')
    cases = []
    specifications = [('gate_137090_bit17_clear', 0, 0, 0, 0xb3)]
    for bits in range(1, 8):
        code = 0x2e9 if bits & 1 else 0x2ef if bits & 2 else 0x2f0
        specifications.append((f'gate_825800_bits_{bits}', 0x20000, bits, 0, code))
    specifications += [('first_checks_pass',0x20000,0,0,None),
                       ('next_gate_failure',0x20000,0,0x10,0x2ee)]
    for name, first, bits, next_value, error in specifications:
        pri = {0x118234: 0x12345600, 0x137090: first, 0x825800: bits,
               0x22410: 0, 0x1070: 0, 0x137808: 1, 0x137810: next_value}
        result = run(image, pri)
        writes = [e for e in result['events'] if e['kind']=='synthetic_write']
        if error is None:
            assert result['stop_reason']=='next_boot_precondition'
            assert not any(e['address']=='0x200bc' for e in writes)
        else:
            assert result['stop_reason']=='error_tail'
            assert any(e['address']=='0x200bc' and e['value']==error for e in writes)
        assert pri[0x118234]==0x12345601
        cases.append({'name':name,'all_inputs_synthetic':True,'result':result})
    # The reporting predicate can suppress publication even for the same error.
    for address, value in [(0x22410,1),(0x1070,1)]:
        pri={0x118234:0,0x137090:0,0x22410:0,0x1070:0}
        pri[address]=value
        result=run(image,pri)
        assert not any(e['kind']=='synthetic_write' and e['address']=='0x200bc' for e in result['events'])
        cases.append({'name':f'publication_suppressed_by_{address:x}','all_inputs_synthetic':True,'result':result})
    print(json.dumps({'debug_imem_sha256':SHA,'limits':'Only selected copied early-gate/control-flow bytes execute. All PRI services, canary, stack and entry r0=0x55 are fixtures. Stops before the next boot precondition or remaining error tail; no hardware, full boot, installed-byte or production-code proof.', 'cases_passed':len(cases),'cases':cases},indent=2))


if __name__=='__main__':main()

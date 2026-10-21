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


def run(image, pri, initial_r0=0x55):
    regs = [None] * 16
    regs[0] = initial_r0
    memory = {0x5a0: 0x13579bdf}  # Synthetic canary, not a firmware dump.
    pc, sp, zero = 0x4e87, 0xe000, None
    trace, events = [], []

    def readreg(index):
        if regs[index] is None:
            raise ValueError(f'uninitialized register r{index} at {pc:x}')
        return regs[index]

    def putreg(index, value):
        regs[index] = value & 0xffffffff

    def readmem(address):
        if address & 3 or address not in memory:
            raise ValueError(f'unmodeled DMEM {address:x}')
        return memory[address]

    def push(value):
        nonlocal sp
        sp -= 4
        memory[sp] = value

    def pop():
        nonlocal sp
        value = readmem(sp)
        sp += 4
        return value

    for _ in range(500):
        if pc in STOPS:
            assert sp == 0xe000
            return {'stop_pc': hex(pc), 'stop_reason': STOPS[pc],
                    'raw_r1': regs[1], 'events': events, 'trace': trace}
        if not any(a <= pc < b for a, b in RANGES):
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
        elif op == 0xa0:
            size = 2
            address = readreg(arg >> 4)
            if address & 3 or not 0xdf00 <= address < 0xe000:
                raise ValueError('store outside synthetic stack')
            memory[address] = readreg(arg & 15)
        elif op == 0x90:
            size = 3
            putreg(arg & 15, readreg(arg >> 4) + image[pc+2])
        elif op == 0xb2:
            size = 2
            putreg(arg & 15, readreg(arg >> 4))
        elif op == 0xbd and arg & 15 == 4:
            size = 2
            putreg(arg >> 4, 0)
            zero = True
        elif op == 0xa6:
            size = 2
            zero = readreg(arg >> 4) == readreg(arg & 15)
        elif op in (0xff, 0xfd):
            size = 3
            sub = image[pc+2] & 15
            if sub != 4:raise ValueError('unsupported logical opcode')
            dst = image[pc+2] >> 4 if op == 0xff else arg >> 4
            value = readreg(arg >> 4) & readreg(arg & 15)
            putreg(dst, value)
            zero = value == 0
        elif op == 0xc4:
            size = 3
            value = readreg(arg >> 4) & image[pc+2]
            putreg(arg & 15, value)
            zero = value == 0
        elif op == 0xf0 and arg & 15 in (4, 5):
            size = 3
            dst = arg >> 4
            value = readreg(dst) & image[pc+2] if arg & 15 == 4 else readreg(dst) | image[pc+2]
            putreg(dst, value)
            zero = value == 0
        elif op == 0x3e:
            size = 4
            target = int.from_bytes(image[pc+1:pc+4], 'little')
        elif op in (0xf4, 0xf5) and arg in (0x0b, 0x1b):
            size = 3 if op == 0xf4 else 4
            if zero is None:raise ValueError('unmodeled flags')
            taken = zero if arg == 0x0b else not zero
            if taken:target = pc + int.from_bytes(image[pc+2:pc+size], 'little', signed=True)
        elif op == 0xb3 and arg & 15 in (0, 4, 9, 13, 14):
            mode = arg & 15
            imm_size, offset_size = (2, 1) if mode == 14 else (1, 2) if mode in (9, 13) else (1, 1)
            size = 2 + imm_size + offset_size
            immediate = int.from_bytes(image[pc+2:pc+2+imm_size], 'little')
            equal = readreg(arg >> 4) == immediate
            if equal == (mode in (0, 9)):
                target = pc + int.from_bytes(image[pc+2+imm_size:pc+size], 'little', signed=True)
        elif op == 0xf9 and arg & 15 == 2:
            size = 2
            for r in range((arg >> 4) + 1):push(readreg(r))
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
                    if address not in pri:raise ValueError(f'missing synthetic PRI value {address:x}')
                    value = pri[address]
                    putreg(10, value)
                    events.append({'kind': 'synthetic_read', 'address': hex(address), 'value': value})
                else:
                    value = readreg(11)
                    pri[address] = value
                    regs[10] = None
                    events.append({'kind': 'synthetic_write', 'address': hex(address), 'value': value})
                regs[9] = regs[15] = None  # Helpers clobber these; no invented return state.
                zero = None
            elif call in (0x45b, 0x3d1a, 0x3f1c):
                push(pc + size)
                target = call
            else:
                raise ValueError(f'unmodeled call {call:x}')
        else:
            raise ValueError(f'unsupported bytes at {pc:x}: {image[pc:pc+6].hex()}')
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

"""Bounded byte interpreter for copied FWSEC progress-update basic blocks.

This is NOT a Falcon hardware emulator. Calls to 0x1117 and 0x1171 are
synthetic read/write adapters. No other call or IO instruction is accepted.
The firmware image is input data; it is never executed by the host CPU.
"""
import hashlib
import sys
import json
from pathlib import Path

IMAGE_SHA256 = 'dee558dc5bbe329bd7ff4d20bc7d7bd0d47d91c1c8d301e759dc6d66348d7ecb'
REGISTER = 0x118234
BLOCKS = [
    ('clear_low_byte', 0x1338, 0x134e, 0),
    ('set_low_byte_1', 0x4e87, 0x4ea0, 1),
    ('set_low_byte_2', 0x577a, 0x5793, 2),
    ('set_low_byte_3', 0x4bdc, 0x4bf5, 3),
    ('set_low_byte_9', 0x5899, 0x58b2, 9),
    ('set_low_byte_ff', 0x592e, 0x5941, 255),
]


def replay(image, start, end, initial):
    regs = [None] * 16
    pc, value = start, initial
    events, trace = [], []

    def reg(n):
        if regs[n] is None:
            raise ValueError(f'uninitialized r{n} at {pc:x}')
        return regs[n]

    for _ in range(32):
        if pc == end:
            return value, events, trace
        if not start <= pc < end:
            raise ValueError('basic-block bound exceeded')
        op, operand = image[pc:pc+2]
        length = None
        if 0x80 <= op <= 0x8f:  # mov register, signed 24-bit immediate
            length = 4
            imm = int.from_bytes(image[pc+1:pc+4], 'little', signed=True)
            regs[op & 15] = imm & 0xffffffff
        elif 0x40 <= op <= 0x4f:  # mov register, signed 16-bit immediate
            length = 3
            imm = int.from_bytes(image[pc+1:pc+3], 'little', signed=True)
            regs[op & 15] = imm & 0xffffffff
        elif op == 0xff:  # 3-register logical AND: src1 high, src2 low, dst high
            if image[pc+2] & 15 != 4:
                raise ValueError('unsupported 3-register opcode')
            length = 3
            regs[image[pc+2] >> 4] = reg(operand >> 4) & reg(operand & 15)
        elif op == 0xf0 and operand & 15 == 5:  # OR register, u8
            length = 3
            dst = operand >> 4
            regs[dst] = reg(dst) | image[pc+2]
        elif op == 0xc5:  # OR dst, source, u8
            length = 3
            regs[operand & 15] = reg(operand >> 4) | image[pc+2]
        elif op == 0x7e:  # long call, bounded synthetic service adapters
            length = 4
            target = int.from_bytes(image[pc+1:pc+4], 'little')
            if reg(10) != REGISTER:
                raise ValueError('unexpected register-address operand')
            if target == 0x1117:
                events.append({'service': 'synthetic_read', 'register_domain': 'GPU PRI address operand', 'address': hex(reg(10)), 'value': value})
                regs[10] = value
            elif target == 0x1171:
                value = reg(11)
                events.append({'service': 'synthetic_write', 'address': hex(reg(10)), 'value': value})
                # Concrete helper clobbers r10; do not invent its returned value.
                regs[10] = None
            else:
                raise ValueError('unmodeled call')
        else:
            raise ValueError(f'unsupported opcode {op:x} at {pc:x}')
        if pc + length > end:
            raise ValueError('instruction exceeds block')
        trace.append({'firmware_imem_va': hex(pc), 'raw': image[pc:pc+length].hex()})
        pc += length
    raise ValueError('instruction limit')


def main():
    image = Path(sys.argv[1]).read_bytes()
    if hashlib.sha256(image).hexdigest() != IMAGE_SHA256:
        raise ValueError('artifact hash mismatch')
    cases = []
    for name, start, end, low in BLOCKS:
        for initial in [0, 1, 0xff, 0x123456ab, 0xffffffff]:
            value, events, trace = replay(image, start, end, initial)
            expected = (initial & 0xffffff00) | low
            assert value == expected, (name, initial, value, expected)
            assert len(events) == 2
            cases.append({'name': name, 'start_firmware_imem_va': hex(start), 'end_exclusive': hex(end), 'initial_synthetic_value': initial, 'result': value, 'events': events, 'instructions': trace})
    mutated = bytearray(image)
    mutated[0x4e87] = 0xfe
    rejected = False
    try:
        replay(mutated, 0x4e87, 0x4ea0, 0)
    except ValueError:
        rejected = True
    assert rejected
    print(json.dumps({'artifact_sha256': IMAGE_SHA256, 'address_domains': 'PCs are copied debug FWSEC Falcon IMEM VAs (base zero); 0x118234 is the PRI address argument to copied helpers; all read values/writes are synthetic only.', 'limits': 'Only six straight-line blocks. Helper calls are modeled; their instruction bodies and physical hardware are not executed. No production-code equivalence or runtime branch attribution.', 'cases_passed': len(cases), 'unknown_opcode_rejected': rejected, 'cases': cases}, indent=2))


if __name__ == '__main__':
    main()

# The 556-byte array is a control-command argument — 2026-10-22

Kernel 10 walks thirty-two records of 556 bytes when it handles command
`0x2080f308`. The block is the handler's second argument. Its length is
`0x4584` (17,796), which is `32 * 556 + 4`.

## Input

Copied RM ELF `firmware-store/gsp-kernels/615-kernel-10.elf`, 17,305,752
bytes, SHA-256
`4ac95cbbe55b5e61572053d0c8a410b4de7693eaa2881d1878c76b6405426f2a`.
Addresses are firmware ELF virtual addresses. The record below is file
offset `0xc628f8`.

Pinned headers are commit `61dcc93722ecb418bb5f2e00923f05b4b8051dd1`.
Category `0xf3` is `NV2080_CTRL_RIST_LEGACY_PRIVILEGED` in
[ctrl2080base.h](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/61dcc93722ecb418bb5f2e00923f05b4b8051dd1/src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080base.h).
That commit's `ctrl2080/` directory has no RIST message header, so message
`0x08` has no public name here.

## Export record

The 32-byte slot matches the layout already used for `0x20802068`: function
at `+0`, flags at `+8`, command at `+0x10`, parameter size at `+0x14`, class
at `+0x18`.

| Field | Value |
|---|---|
| Function | `0x1623824` |
| Flags | `0x44` |
| Command | `0x2080f308` |
| Parameter size | `0x4584` |
| Class | `0x1c64e70` |

Raw bytes: `2438620100000000440000000000000008f3802084450000704ec60100000000`.

The command word occurs once in this ELF, in that slot. Nothing else in the
file assembles a second copy of `0x2080f308`.

## What the handler does with the block

`0x1623824` keeps `a1` as the block. The word at its start is a 32-bit mask.
The cursor starts on `a1` and advances by `0x22c` (556). The loop runs while
the index is below `0x20` (32).

For a set bit it requires the byte at cursor `+4` to equal 2, reads the word
at cursor `+8`, and passes cursor `+0xc` to `0x1620de8`. On that call's
success it stores zero at cursor `+0x228` and cursor `+0x22c`. The last of
those stores lands on the final four bytes of the `0x4584` block.

While the cursor is live, the handler also reads bytes at `+0xe`, `+0x90`,
`+0x98`, and `+0xa0`. It does not compare a per-record byte 0 with 8. The
tag-8 parser from 2026-10-21 is a separate consumer of a 556-byte stride.
This note does not join the two buffers.

## The block is built in libnvidia-ml

In kernel 10 the command and the size each occur once, both in the export
record, and the dispatcher forwards the pointer it was given. The bytes are
built in the host library.

The public archive was downloaded to an isolated temp directory, hash
checked, and deleted after this note. It was not executed.

| Item | Size | SHA-256 |
|---|---:|---|
| `NVIDIA-Linux-x86_64-615.71.09.run` | 529,618,784 | `cdceed22bbeb61248d1a6deabc2596673e3a6501698ee71ac8d2fdc28f3b70fe` |
| `libnvidia-ml.so.615.71.09` | 2,958,776 | `283793c0c30dc32f87c0e9fc9b5326fe764bad156e61afa3e997684c47b29a95` |

Addresses below are host ELF virtual addresses in that library. In its
executable LOAD, virtual address equals file offset. They are not firmware
addresses.

`cDeviceRistSetOperatingPoints_v1` begins at `0x12a4c0`. The library's own
log records that name and the source file `dmal/common/common_rist.c`. A
wrapper at `0x12dba0` tail-jumps to it after requiring the third argument's
first dword to be `0x1007488`. That dword occurs only in the wrapper's
compare. Neither function has another direct call or jump.

The function zeros a `0x4584`-byte stack buffer and stores `1` at its first
word. It then walks 32 slots. The destination stride is `0x22c`. The source
stride is `0x3a4`, starting at the third argument `+0x1c`. The shift test
at `0x12a55f` (`test al, 1` on `1 << index`) admits only index 0, and only
when bit 0 of the third argument `+4` is set.

For that slot, source word `+0xc` selects the copy. Value 2 stores byte
`2` at record `+4` and then copies the following source fields into the
record. Value 0 or 1 stores a different byte at record `+4` and returns
status `2` without sending the command. On the value-2 path the function
calls `0xa5880` with `ecx = 0x2080f308`, `r8` the buffer, and `r9d = 0x4584`.
That call target is the host control transport already traced in the
2026-10-21 dispatch note.

The same command integer also appears in `kernel/nvidia/nv-kernel.o_binary`
as a method record whose following size field is `0x4584`, and once in
`firmware/gsp_tu10x.bin`. Those are registration records. The 32-bit
`libnvidia-ml.so.615.71.09` also contains the command immediate. Neither
was disassembled.

## The third argument and the only pointer to the wrapper

The library was extracted again from the same archive into an isolated
temp directory, hash checked, and removed. The hash is unchanged.

The first dword `0x1007488` occurs only in the wrapper's compare. Its low
24 bits are `0x7488` (29,832), and `8 + 32 * 0x3a4` equals that size. The
high byte is 1. The third argument is a version-1 block of 32 source
records, each 932 bytes, with an 8-byte header. The filler starts its
cursor at `+0x1c`, twenty bytes into the first record, and advances by 932.

The wrapper's address is stored at one place: host VA `0x2d2328`, file
offset `0x2d1328`. That qword is entry 89 of the function block whose base
is host VA `0x2d2060`. The older entry `0x111d30` sits at offset `0x120`
in the same block, which makes this entry historical slot 53. The sysfs
initializer at `0x36f50` copies the first `0x4c` qwords and stops at
offset `0x260`, before entry 89. No other instruction takes the address
of the block, and no call or jump targets `0x12dba0`.

## Next offline step

Entry 89 is not copied into the sysfs table, and this library does not
build the 932-byte source records. The tag-8 parser remains a separate
consumer. Do not resume `0x4194810`, and do not treat either block as a
measurement.

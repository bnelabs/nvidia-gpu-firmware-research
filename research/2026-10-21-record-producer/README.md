# Where the firmware's tagged P-state record comes from

The tag-8 record used by the [entry constructor](../2026-10-21-object-origin/README.md)
is a view into a serialized table buffer. The copied setup specifies a 20-byte
header, 556-byte records and source selector `6`. A recovered callback locates a
present record and returns its address; it does not manufacture the P-state word.
The operation that obtains the original table bytes remains unresolved.

## Inputs and address domains

This analysis uses the retained RM ELF from `gsp_ga10x` 615.71.09:

- Path: `firmware-store/gsp-kernels/615-kernel-10.elf`
- Length: 17,305,752 bytes
- SHA-256: `4ac95cbbe55b5e61572053d0c8a410b4de7693eaa2881d1878c76b6405426f2a`
- ISA: RV64 with compressed instructions
- Address domain: firmware ELF virtual addresses, with explicit file offsets in
  each raw export; no live addresses or host-library addresses
- Exact NVIDIA source: `61dcc93722ecb418bb5f2e00923f05b4b8051dd1`

The ELF is not asserted to be GA102-exclusive. RTX 3090/GA102 is a previously
reported board identity; its historical OS/privilege is unknown here. Current
GPU identity, driver, GSP mode, workload and health were not queried.
The [manifest](source-manifest.json) records source commits and input hashes.

## Findings

| ID | Status | Finding |
|---|---|---|
| RP-01 | observed-bytes; CPU-reproduced | Copied constant setup and interface initialization establish header `20`, record stride `556`, selector `6`, acquisition function `0x176b2a8` and entry wrapper `0x1768dd4`. |
| RP-02 | observed-bytes; CPU-reproduced | Format byte `1` selects a 32-bit presence-mask branch. The parsed object keeps the raw buffer at `+8`, mask at `+0x30`, header size at `+0x38` and stride at `+0x3c`. Its `u16(+0x10)` is the highest set index plus one, including holes. |
| RP-03 | observed-bytes; CPU-reproduced | Store `0x1767cf0` assigns record getter `0x17615d4` at parsed object `+0x28`. A present record returns `buffer + header + zero_extend_32(stride * index)`; an absent in-range bit returns a null pointer with status zero. |
| RP-04 | observed-bytes; CPU-reproduced | The recovered wrapper forwards that record to `0x16870d4`. The copied constructor prefix checks tag `8` and copies its `+0x0c` word through temporary `+4` into entry `+0x34`. |
| RP-05 | source-decoded | Acquisition selects a source container through provider `+0x60`, maps selector `6` through a `u16` index table and checks slot bounds/presence before an indirect getter. Actual provider/container objects and selected function remain unknown. |
| RP-06 | source-correspondence | The callback path reaches code matching public `memdescCreateSubMem`: it validates a byte range and constructs a sub-descriptor. That operation does not itself prove acquisition or a CPU copy of the table bytes. |
| RP-07 | unresolved | Original table contents/storage, transfer implementation, runtime provider/selection and full upstream/later validation remain unknown. Neither a VBIOS table nor a physical measurement has been identified. |

## Schema setup and mask dispatch

The constant-building block at `0x1688876` passes the first layout record in
`a6`. Interface initialization `0x1767128` stores its three words into interface
`+0xc8`, `+0xcc` and `+0xd0`. Executing those copied instructions gives:

| Interface field | Raw value | Use in copied code |
|---|---|---|
| `+0xc8` | `0x14` / 20 | Bytes preceding records |
| `+0xcc` | `0x22c` / 556 | Record stride |
| `+0xd0` | `6` | Source-table selector |
| `+0x98` | `0x176b2a8` | Acquisition callback |
| `+0xa8` | `0x1768dd4` | Entry-construction wrapper |

The later assignment at `0x1688998` supplies wrapper target `0x16870d4` through
interface `+0xf0`. [parser-selection.json](parser-selection.json) retains the
instruction bytes and reference calculations. The emulator executes 226 copied
instructions for the setup through the first schema stores.

After acquisition, `0x17678c8` dispatches on the buffer's first byte. The raw
signed-offset jump table is at VA `0x1e13bb4`, file `0xe13bb4`; its seven entries
are retained in [layout.json](layout.json). Format `0` reaches an error branch.
Format `1` reaches `0x1767c28`, which imports the 32-bit mask from buffer `+8`.
The fixture uses format `1` because that dispatch is demonstrated by the bytes.
It is not assigned a public protocol name.

The chosen branch creates a 12-byte internal mask and a 64-byte parsed object.
It stores the raw buffer pointer, header/stride and callback `0x17615d4`. It also
allocates two eight-byte output/header objects. Their later initialization and
interpretation are not part of this experiment.

A mask of `0b101` produces span `3`, although only two indices are present. The
getter tests the requested bit before calculating its record pointer. This span
must not be confused with a population count or with the other table's logical
index fields from the earlier analysis.

## Record-to-entry transfer

For index `i` present in the mask, the copied getter performs the equivalent of:

```
record = buffer + u32(header_bytes) + zero_extend_32(record_stride * i)
```

The multiplication uses `MULW`, followed by zero extension. The getter contains
no independent comparison against the original raw-buffer length; the complete
acquisition/validation path is not modeled here, so this is not a reachability or
vulnerability finding.

The experiment supplies a synthetic 1,688-byte buffer with format `1`, presence
bits `0` and `2`, and two tag-8 records. Its complete bytes and hash are retained
in [emulation.json](emulation.json). Execution begins after the unexecuted data
transfer. All instance addresses beginning `0x700...` and allocator results are
fixtures.

| Requested index | Copied getter result | Word copied into entry `+0x34` |
|---|---|---|
| 0 | Buffer `+20` | `4` |
| 1 | Null, status `0` | No constructor call |
| 2 | Buffer `+1132` | `256` |

The parser branch executes 179 copied instructions. For present records, the
experiment executes `0x1768dd4 → 0x16870d4`, including the tag check, both heap
allocations, copied zero-fill/base-entry construction and the `+0x34` store.
It stops before component getter `0x1687358`. The constructor's eventual return
and later checks are not implied by this prefix. Heap allocation is the only
substituted service in these executed blocks.

## Acquisition boundary

Function `0x176b2a8` reads provider `+0x60` and selector at interface `+0xd0`.
For the checked selector range, it reads a mapped index at container
`+0x888 + 2*selector`, compares it with `u16(container+0x18)`, checks its pointer
array slot, then calls container `+0x38`. The actual instance and that indirect
target have not been recovered.

Its callback path is:

```
0x176b4b8 → 0x1b0a0ec → 0x1839700 → 0x1839598 → 0x140b7ac
```

The first helper checks the requested offset and length against source-entry
`+0x2c`, adds the base offset at `+0x28` and selects another object. The final
call's arguments and checks correspond to public `memdescCreateSubMem`: an
output pointer, parent descriptor, GPU argument, byte offset and byte size;
offset below size, nonzero length, and overflow/end bounds checks. Field-copy
behavior also matches the source. This is source correspondence rather than an
extracted function symbol or complete private/public layout equivalence.

The surrounding transfer function `0x17776c4` builds a request context and reaches
worker `0x176b564`. It is not executed in this analysis. The earlier static lead
described the callback chain as a read; following the sub-descriptor creation
shows why that description alone was insufficient. Raw acquisition leads are
preserved under `leads/` and are not promoted beyond the claims above.

## Source comparisons

- NVIDIA's exact-release
  [mem_desc.c:2518 onward](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/61dcc93722ecb418bb5f2e00923f05b4b8051dd1/src/nvidia/src/kernel/gpu/mem_mgr/mem_desc.c)
  supplies the sub-descriptor comparison. Constructing a view into memory does
  not establish how a later transfer accesses that memory.
- The public
  [BoardObjGrp E32 mask](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/61dcc93722ecb418bb5f2e00923f05b4b8051dd1/src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080boardobj.h)
  consists of a 32-bit data element. The copied internal mask is 12 bytes, with
  metadata before its bits. Their layouts and selector namespaces are not
  interchangeable.
- Pinned [nouveau's performance-table parser](https://github.com/torvalds/linux/blob/7d0a66e4bb9081d75c82ec4957c50034cb0ea449/drivers/gpu/drm/nouveau/nvkm/subdev/bios/perf.c)
  and [envytools' power-table parser](https://github.com/envytools/envytools/blob/f102b82381f3f11cee113d16374c87091db039d9/nvbios/power.c)
  retain their own versioned vBIOS formats. Neither identifies this internal
  20/556-byte schema. Nouveau's retained r535 control transport and the pinned
  Nova GSP file also do not supply this private r615 parser.

## Reproduction and next question

```sh
bash research/2026-10-21-record-producer/reproduce.sh /tmp/record-producer-replay
```

The destination must be new. Parsing, disassembly, emulation and tests run through
the CPU-only namespace wrapper, with no device passthrough, network or host
service sockets. The original files are read-only. All seven JSON products
replay byte-for-byte. The repository gate passes 41 Python tests plus the C/CLI
and 29 offline-record checks; see [check.log](check.log). [SHA256SUMS](SHA256SUMS)
seals the results, programs and raw leads.

Next, trace worker `0x176b564` and the function assigned at the source-selector
descriptor's `+8`. Determine the actual transfer implementation and source
storage before calling the serialized bytes VBIOS, RPC data or physical state.
Continue with static code and bounded CPU models; do not obtain instance pointers
or source contents from the running driver/GPU.

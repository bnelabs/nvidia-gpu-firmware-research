# Next offline research task

Read AGENTS.md, CONSTITUTION.md, CORRECTIONS.md and EVIDENCE.md first. Preserve
uncommitted work. Research uses copied files and CPU-only execution; no private
calls, device reads, tracing, configuration changes or firmware operations.

## Current priority: the remaining recovery dependency

The owner's subsequent request prioritizes the Xid79 outage. Last retained
recovery restored PCI access but startup reported GFW progress `0x1` and
`NV_ERR_NOT_READY`. This state was not freshly checked during offline research.

The [boot packet](research/2026-10-21-gfw-boot/README.md) now covers restart
checks, step selectors, a conservative main-function graph, digest-matched ROM
record `0x41` and its consumer, plus vendor reset/boot ordering. Counter cleanup
comes later than boot readiness; do not promote it into a cause or a live fix.
Debug FWSEC is not proven equivalent to production.

Follow-up proved `0x5be3` selects a table, `0x5c9a` constructs addresses and
`0x5ab2` saves runtime register values. Consumer `0x59fe` restores those saved
values and traps on readback mismatch. These are not fixed boot defaults.
Copied constructor/restore fragments execute with explicit synthetic state;
the missing saved-value case is rejected.

Follow-up traced `0x4653` into loader `0x43a8` with selector 1, raw mode `0xaa`,
and the HALTED wait at `0x669d -> 0x663a`. Exact GA102 headers identify the core
selector and both Falcon/RISC-V HALTED fields. The timed raw-`0xbc` poll belongs
to another loader branch. Step bits 25:24 can become 2 even when an opaque loader
result is an error, so that marker alone does not certify success.

Record `0x2f` and the BIT PRE_OS/PMU entry resolve to the same copied component.
Four GA102 variants have identical 32,004-byte IMEM but 16 differing DMEM bytes.
Copied prefixes read those differences; physical meanings remain unknown.
PRE_OS sets bit 9 at D[0x140205e4], matching the alternate wait's low PRI operand
and bit. Its physical aperture mapping is unproved here; do not equate domains.

Follow-up resolves interface ID `0x0e` to copied PRE_OS D[`0x1c`], twelve bytes.
Selector 1 clears record `+6` bit 0 and separately writes `0x40` at `+8`.
Writer `0x6b04` checks alignment/capacity/span and emits three DMEM words;
its PRI/IO services are synthetic, including stalled/error cases. The cleared
flag selects exit callbacks. Word `+8` bit 6 selects work in last init callback
`0x5d51`: call `0x1484`, then `0x5c8f` only after a zero service return.
Cleanup `0x7a14` contains `exit` at `0x7a85` before its `ret`; do not assume
it returns to entry `0xc`. Crypto/IO operations and full callbacks remain unknown.

Follow-up traces `0x1484 -> 0x724a` input-field extraction and the selected
`0x70e9 -> 0x6f11` 128-byte header copy, with explicit synthetic large-D data.
It locates factory method assignment `+0x94 -> 0x4a76`; allocator/full factory
and method remain unexecuted. The input guard D[`0x5be`] is local BSS, not
reset-persistent proof. Type 8 selects schema tag `RRL`, format
`3s2bwb2w512r2b3d`, and parser output argument D[`0x2714`]. Consumer `0x5c8f`
checks capacity/count/index, skips masked/empty cases and polls a command bit
without a local timer. Exact register purposes and physical aliases are unknown.

Next: trace PRE_OS parser `0x10a8` through assigned reader `0x485e` into the
type-8 output at D[`0x2714`]. Keep actual acquired bytes, method `0x4a76`,
allocator and hardware status unknown unless copied evidence resolves them.
Entry still waits on D[0x14001724] bit 29 before unexecuted callbacks. No whole
loader/callback success or actual card state is supplied by these replays.
Keep GPU PRI, Falcon IO/data space, ROM offsets and PCI configuration separate.
Decoded debug IMEM SHA-256:
`dee558dc5bbe329bd7ff4d20bc7d7bd0d47d91c1c8d301e759dc6d66348d7ecb`.
PRE_OS IMEM SHA-256:
`45ed86ec62e8ceba8fb402e472f5a3ceea206c37c22772e2ef922e78bf89c6fc`.

Acceptance: demonstrate one more required callee's input/wait/failure boundary,
or its exact unresolved input/service boundary. Reproduce the boot packet and
run `tests/check.sh` through `scripts/run_cpu_only.sh` before publishing.

## Earlier telemetry result and next question

The owner also supplied GeForge, GDDRHammer and GPUBreach. Selected sources,
CPU-only utility checks and a 580-versus-615 queue-format comparison are in the
[memory-research review](research/2026-10-22-memory-research/README.md).
Their runtime memory attacks are not a GFW_BOOT recovery method. Reuse file
formats/analysis only; preserve ambiguous addresses and missing metadata.
Later protocol work can trace the 615 MCTP/NVDM receiver with synthetic frames.
The PRE_OS callees above remain the immediate recovery research priority.

The 615.71.09 P-state path is traced through the host shared-data reader, firmware
writer, internal RM dispatch, Perf table getter and one entry constructor.
The latest [record-producer analysis](research/2026-10-21-record-producer/README.md)
locates its tag-8 input record in a serialized buffer with a 20-byte header and
556-byte records. Its source selector is 6. Copied setup/parser/getter/constructor
blocks execute with synthetic inputs; the actual acquisition service does not.
Original table bytes, runtime objects/selection and physical provenance are unknown.

Artifact: `firmware-store/gsp-kernels/615-kernel-10.elf`, SHA-256
`4ac95cbbe55b5e61572053d0c8a410b4de7693eaa2881d1878c76b6405426f2a`.
All addresses below are firmware ELF VA, not live pointers.

## Next question

Trace the acquisition worker `0x176b564` reached from `0x17776c4`, and resolve the
function assigned at source-selector descriptor `+8`. The callback chain
`0x176b4b8 → 0x1b0a0ec → 0x1839700 → 0x1839598 → 0x140b7ac` constructs a bounded
memory sub-descriptor; that alone does not prove a data copy or storage identity.
Find the actual transfer implementation before naming the bytes VBIOS, RPC data
or physical state. Use raw instructions, pointer assignments and exact-source
comparison. Do not fill missing runtime pointers with plausible values or names.

Acceptance: a retained source/transfer implementation with a bounded CPU model,
or its exact unresolved service boundary and the next useful offline discriminator.
After two unproductive approaches, reassess and continue another offline question.

Later questions are current-index selection at table `+0x194`, availability-gate
clearing at Perf `+0x2d7`, and alternate constructors/overrides/writers. One store
at `0x1667506` copies table `+0x1a4` into `+0x194`; it is a lead for the selection
trace, not proof of every update.

Retain hashes, raw bytes, file/VA domains, source commits and fixture boundaries.
Run `tests/check.sh` inside the CPU-only wrapper before promoting a result. The
technical map is [docs/control-plane.md](docs/control-plane.md). Earlier handoff
checkpoints are preserved under `archive/2026-10-21-workflow-notes/`.

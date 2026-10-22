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

Next: trace mandatory debug IMEM call `0x4653`, just after restoration and before
progress `0x2`. It checks step-word bits 25:24 and can reach `0x279a`, `0x37b0`,
`0x43a8` and `0x2f6b`. Recover actual inputs, waits and failure branches without
assuming those calls succeed. Keep GPU PRI,
Falcon IO/data space, ROM file offsets and PCI configuration offsets separate.
Decoded debug IMEM SHA-256:
`dee558dc5bbe329bd7ff4d20bc7d7bd0d47d91c1c8d301e759dc6d66348d7ecb`.

Acceptance: demonstrate one more required callee's input/wait/failure boundary,
or its exact unresolved input/service boundary. Reproduce the boot packet and
run `tests/check.sh` through `scripts/run_cpu_only.sh` before publishing.

## Earlier telemetry result and next question

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

# Next offline research task

Read AGENTS.md, CONSTITUTION.md, CORRECTIONS.md and EVIDENCE.md first. Preserve
uncommitted work. Research uses copied files and CPU-only execution; no private
calls, device reads, tracing, configuration changes or firmware operations.

## Current result

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

# Next offline research task

Read AGENTS.md, CONSTITUTION.md, CORRECTIONS.md and EVIDENCE.md first. Preserve
uncommitted work. Research uses copied files and CPU-only execution; no private
calls, device reads, tracing, configuration changes or firmware operations.

## Current result

The wrapper `0x12dba0` is function-table entry 89 at host VA `0x2d2328`
(historical slot 53). Its third argument must begin with `0x1007488`, which
is version 1 and size `0x7488`: 8 bytes plus 32 records of 932 bytes. The
library never stores that dword, and no instruction calls the wrapper. The
sysfs copy at `0x36f50` takes only the first 76 table entries and stops
before this one.

Library SHA-256 `283793c0c30dc32f87c0e9fc9b5326fe764bad156e61afa3e997684c47b29a95`.
Host ELF VA. Detail is in the
[RIST-table note](research/2026-10-22-rist-table/README.md).

## Next question

This library does not build the 932-byte source records, and the tag-8
parser is still a separate consumer. The next offline question is whether
any retained path feeds that parser from this operating-point block.

Acceptance: one demonstrated field that both sides use, or a stop. Do not
resume `0x4194810`. Do not treat either block as a measurement.

Retain hashes, raw bytes, file/VA domains, and fixture boundaries. Run
`tests/check.sh` inside the CPU-only wrapper before promoting a result. The
technical map is [docs/control-plane.md](docs/control-plane.md).

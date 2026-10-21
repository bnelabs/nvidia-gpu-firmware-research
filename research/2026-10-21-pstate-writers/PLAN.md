# Firmware P-state writer provenance

Question: where do the retained RM firmware's RUSD P-state record and direct
getter obtain their values? Competing explanations include a common perf object,
independent cached values, direct register reads and architecture-specific paths.

Use exact copied ELF, bounded disassembly, raw call arithmetic, source comparisons
and synthetic CPU execution. Trace RUSD poll handler 0x1447ac8 into scheduler
callbacks and shared record +0x8e8. Separately resolve table getter +0x38 reached
from 0x167de40, then compare field provenance. Stop at unresolved indirect targets;
never call a driver, boot firmware or inspect live GPU memory.

Before edits, preserved all non-Git workspace files and Git diff/ref records in
`../nvidia-value-provenance-preserve-20261021-pjjaQu/`. workspace.tar.gz:
234738414 bytes; SHA-256
`8d2da7c6c93a383333cb47afc95357098575364ca7c1978995e53d4f25b6131b`.
Prior packets remain unchanged. Starting HEAD/origin/main: d42161f2d6c0531eab3ed0b8c9c539ed52051e7d.

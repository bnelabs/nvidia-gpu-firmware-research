# RM tooling status — offline only
The historical live RM client has been retired under [CONSTITUTION.md](../CONSTITUTION.md).
Its original source remains in Git history at 2d66900ccae6e55a7f458d5bd58081c27d39fcf9
for decompilation/source comparison, not execution on hardware.

## Current tools
- rmctl.c: --offline-pstate MASK or --offline-raw REGULAR_CAPTURE_FILE.
- sniffer2.c/.h: explicit little-endian NVOS54 header/payload buffer decoder.
  Historical pointer fields are metadata; they are never dereferenced. Syscall return,
  errno and RM status remain separate. Failed syscalls have no valid returned RM status.
  Capture size is bounded at 65536 bytes; export writes the actual retained count.
- fake_rm.c/.h: deterministic synthetic payload bytes. No descriptors, interposition,
  ioctl forwarding, driver loading, environment knobs or hardware-fidelity claim.
- nvml_pstate_probe.c: retired stub that exits with status 64 without loading NVML.
- build.sh: builds the offline rmctl into build/. No vendor headers or GPU are needed.

The old fake backend and multi-call transport test have been replaced, not certified.
The old sniffer.c and tracked prebuilt binaries are removed. Never load old preload
libraries or execute old probes from another checkout.

## Corrected interpretation
RM mask 4=P2 and 256=P8. NVML's public P-state is ordinal. 0x2080014a's old +4
P-state attribution is retracted. 0x2080a61d bytes do not establish power semantics.
The production collector uses documented nvidia-smi presentation only.

Run tests/check.sh on a CPU-only host. This validates software behavior and retirement,
not live safety or fidelity of the historical captures.

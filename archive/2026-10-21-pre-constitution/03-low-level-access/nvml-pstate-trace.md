> HISTORICAL / SUPERSEDED. Not an authorized runbook. Claims may be retracted. Read current CONSTITUTION.md and CORRECTIONS.md at the repository root.

# NVML P-state retrieval path — packet B trace report

Statuses follow RESEARCH-DIRECTION.md: observed-bytes / source-decoded / cross-validated /
hypothesis / retracted.

## Provenance
- Device: NVIDIA GeForce RTX 3090, UUID `GPU-8a9c05b3-fea1-4d89-5113-b56acbb1eba9`,
  PCI `0000:06:00.0` (idle, P8 at capture time — natural state variation only, nothing forced).
- Driver: 615.71.09 open KMD; libnvidia-ml.so.1 (closed) via dlopen; probe:
  `07-prototype/nvml_pstate_probe.c` (markers INIT/GETTER/SHUTDOWN, 5 repeated getters,
  same process). Tracer: `07-prototype/sniffer2` (hardened, packet A) capturing every
  'F'-magic ioctl with pre/post diffs.
- Raw evidence (immutable, hashed in `06-ground-truth/nvml-pstate-trace/SHA256SUMS`):
  interleaved stdout+stderr log + stderr-only sniff log.

## Findings

1. **observed-bytes**: `nvmlDeviceGetPerformanceState` returns **0x8** (P8) — stable across
   5 same-process getters; matches `nvidia-smi --query-gpu=pstate` (P8). NVML reports the
   human ordinal, and the RM one-hot enum (P8 = 0x100) is *not* what NVML returns.
2. **observed-bytes**: the 5 getters produced **exactly one** RM control — client-level
   `0x00000d01` (12-byte in/out, object `0xc1d0088d` = a client handle, not the subdevice);
   plus one `0x00de0001` (8-byte, object `0xa55a0040`). Getter calls 2–5 issued **no ioctls**:
   NVML caches the value in-process. → cross-validated with nvidia-smi traces (same two
   controls during its pstate query).
3. **hypothesis (open)**: `0x00000d01`'s 12-byte payload (`40 00 5a a5 | 01 00 00 00 |
   01 00 00 00` pre; RM writes at +8) is the retrieval path, but its response encoding is not
   yet decoded (a P8-vs-1 mismatch at +8 is unresolved). Candidate next step: offline analysis
   of `libnvidia-ml.so.1` (closed) with the REA/IDA toolchain to decode the conversion and the
   0x00000d01 request/response structs — no GPU needed.
4. **retracted**: the earlier "0x2080014a returns pstate" claim (selector coincidence) and the
   "P4 divergence" (one-hot decoder error). See LOG waves 2e–2f and REVIEW.md.

## rmctl implication
The open-SDK control `0x20802068` returns the RM one-hot enum (P2=0x4 busy, P8=0x100 idle —
BOTH correct readings once decoded). rmctl should print the one-hot **decoded ordinal**, not
the raw value; NVML-matching behavior is a separate (closed) path.

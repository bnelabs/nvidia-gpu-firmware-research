> REFERENCE / HISTORICAL REPORT — not a hardware runbook. Current [CONSTITUTION](CONSTITUTION.md) and [CORRECTIONS](CORRECTIONS.md) override this material. Offline decompilation and RE remain authorized. Hardware recipes, bench exceptions and blanket complete/safe claims below are superseded; other literature claims have not all been independently revalidated.

# Lead review — 2026-10-16

Reviewed base: `c7691c4cac9e2a72f3413b9946bf5d98a457813b`.
Follow-up correction: `currPstate` uses a one-hot enum. The recorded `0x4` means P2,
so the earlier P4/P2 discrepancy in this review is superseded. See
[RESEARCH-DIRECTION.md](RESEARCH-DIRECTION.md). NVML's internal path remains unproven.

Scope: repository code, research consistency, existing offline ROM corpus, and next-step
experimental design. This is not an exhaustive validation of all literature claims.

## Findings and changes

1. **Incorrect P-state output survived the correction commit.** `rmctl.c` still treated
   +4 in 0x2080014a as P-state, using an embedded machine UUID. Removed this probe;
   corrected roadmap and the empirical map. The earlier log remains historical evidence,
   superseded by its correction. Five repeated P4/P2 observations establish a discrepancy,
   but cannot exclude a systematic sampling, encoding or ABI mistake.
2. **Parser results disagreed with the documented method.** `adj_ptr()` was unused and
   PERF targets skipped UEFI adjustment. PCIR was found by substring, header checksum
   ignored, and truncated inputs could throw struct errors. Fixed traversal/validation,
   shared pointer adjustment and CLI handling. Token fields were already decoded LE;
   corrected the misleading BE description. Source: NVIDIA's
   [BIT specification](https://download.nvidia.com/open-gpu-doc/BIOS-Information-Table/1/BIOS-Information-Table.html).
3. **Tracing needs hardening before further field attribution.** `sniffer.c` decodes
   escape 0x2a without requiring the expected 32-byte NVOS54 size, ignores the embedded RM
   status, leaks `pre` on failed ioctl, and logging can alter errno. Its variadic wrapper
   assumes a third argument and directly dereferences caller pointers. A generic preload
   library needs explicit ABI/platform scope and invalid-buffer handling. It also forwards
   every operation: loading it does not make an arbitrary workload read-only. This patch
   does not claim to fix these tracer issues; they are the next code task.
4. **Correlation is being promoted to semantics too quickly.** Query-specific control IDs
   identify candidates, not individual field meanings. A 370000 value alongside a 420 W
   NVML limit leaves the selector, units and meaning unproven. A null legacy vBIOS table
   cannot prove migration into GSP. Retain raw values and alternative explanations.
5. **Capture/acquisition provenance needs work.** `capture_state.sh` records only the first
   GPU and labels `lspci -xxx` as 4 KiB (it is the conventional 256-byte dump). Do not
   automatically expand live config reads. Historical fetches should reject HTML/error
   bodies before recording hashes. Pin source commits and record URLs per binary.
6. **Firmware architecture tags are limited evidence.** A gr10x signature section proves
   that a named section exists in that artifact. It does not establish a consumer SKU,
   launch date, functioning support or a verified per-architecture embedded-kernel mapping.

## Work packets for the active worker

### A. Make tracing trustworthy

Work in a separate branch. Test with a fake ioctl backend; no GPU needed. Require exact
NVOS54 request shape before decoding, log syscall and RM status separately, preserve errno,
free buffers on every path, document 64-bit Linux limitations, and bound captures. Record
sequence, fd, handles, command, full size, captured size, truncation and input/output direction.
Acceptance: malformed sizes, failed syscall, RM rejection, unchanged inputs and truncated
captures all have tests. Rebuild artifacts from source rather than trusting tracked binaries.

### B. Resolve the actual NVML P-state getter

After A, use an isolated direct `nvmlDeviceGetPerformanceState` caller with separate markers
for initialization and each getter; compare repeated calls in the same process. Trace file
and mmap activity as well as ioctls. Check whether the SDK P-state value is an ordinal,
mask or other encoding using the pinned header and implementation. Inspect user-library
call paths offline if ioctl output does not explain the result. Do not infer a field merely
because a byte equals P2. Accept only repeatable output-field evidence or a documented
client-side calculation. Avoid forcing load/power changes on the inference host.

### C. Reproduce firmware structure before functional reverse engineering

Create an offline JSON inventory containing artifact SHA-256, section offsets/sizes,
embedded ELF candidates, bounds checks, and loader-source commit/paths. Validate candidate
ELFs structurally and resolve architecture mapping from loader metadata. Compare the same
architecture across driver versions; whole-file hash churn alone does not establish a
functional change. Keep unresolved mappings explicitly hypothetical.

### D. Decode power tables with corrected offsets

Repeat corpus comparisons, record raw/adjusted/file offsets, and map fields using matching
versioned table definitions or their driver consumers. Validate units, counts and strides.
Cross-AIB samples are useful only after format compatibility is established. Export an
inspectable report with hashes; do not edit or flash production firmware.

## Validation performed

- `python3 -m unittest discover -s tests -v`: seven synthetic tests pass.
- `parse_vbios_bit.py <existing ROM> --perf`: all four existing local EVGA corpus samples
  succeed, including wrapped images and adjusted high PERF pointers.
- Compile rmctl against existing local vendor headers; compilation only, no execution.

Limitations: no runtime tracing validation, no complete PERF subtable decoding, no claim of
exhaustive hostile-input parser support, and no validation of every external citation.
Production GPU restrictions in README remain binding. Review branch changes can be adopted
independently; no active worker checkout or main-branch history needs to be rewritten.

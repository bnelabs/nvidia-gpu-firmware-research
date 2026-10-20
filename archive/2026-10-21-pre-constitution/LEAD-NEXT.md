> HISTORICAL / SUPERSEDED. Not an authorized runbook. Claims may be retracted. Read current CONSTITUTION.md and CORRECTIONS.md at the repository root.

# Lead direction — 2026-10-16

Read this before choosing the next task. This supplements RESEARCH-DIRECTION.md with
review of local HEAD `3f225bb` and the in-progress fake-RM files. Remote HEAD at review
was `1a961e8`. Uncommitted files are work in progress, not completed deliverables.

## One objective

Deliver a reproducible, source-pinned, offline-tested GA102 telemetry toolchain.
Finish one trustworthy vertical slice before widening the command surface. The next
commit should close fixture correctness; the following commit should close tracer
correctness. Do not start a new survey, control family, disassembler project, or emulator.

## Review findings that determine the next assignment

1. **Fixture ABI bug:** `07-prototype/fake_rm.c:63` writes NVOS64 status at +44.
   A compiled `offsetof(NVOS64_PARAMETERS, status)` against pinned vendor headers
   returns **40**, with sizeof=48. +44 is tail padding. Use the vendor types and
   compile-time size/offset assertions instead of a second handwritten ABI.
2. **Fixture bounds bug:** PMUMON accepts paramsSize>=16 but writes at +16 and +6020.
   Reject undersized buffers before any access. Verify every emulated command's
   required extent, not just its first field. Include canary or sanitizer checks.
3. **Offline suite currently fails to compile:** `tests/fake_rm_multi.c` uses NVOS64
   and NVOS54 while its shim defines NVOS64_PARAMETERS and NVOS54_PARAMETERS.
   Reproduced with gcc, without opening a GPU device.
4. **Harness can hide build failures:** `gcc ... | head -3` lacks pipefail and uses
   a reusable `/tmp/fake_multi`. A failed build can run an older binary. Use a unique
   temporary build directory, fail on compilation, check process statuses, and clean up.
   Its P-state expected text also disagrees with rmctl's `(P8)` output, and its
   identity-probe assertion targets a probe that has been removed.
5. **Offline is not isolated yet:** rmctl still opens `/dev/nvidiactl` and `/dev/nvidia0`;
   the fake backend intercepts ioctl but not open, and forwards unrecognized requests
   (including FREE) to the real ioctl. Make test runs use fake descriptors or an injected
   transport and fail closed for unexpected operations. Acceptance: run with no NVIDIA
   devices and fail if any NVIDIA device access is attempted. Do not run the current
   full shell suite on the production GPU to establish this property.
6. **Audit is ahead of implementation:** semantic-audit.md describes sniffer2 safeguards,
   but the available source is the old sniffer.c, without exact NVOS54 size validation,
   RM-status logging or errno preservation. decode_telemetry.py is also absent from the
   tracked script inventory. Label proposed contracts as proposed until source and
   fixtures exist. The audit omits rmctl's power candidate and incorrectly says BIT
   token u16 values are BE; the parser uses LE. Remove blanket completion claims.
7. **Client output validation remains incomplete:** rmctl indexes samples[numSamples-1]
   without checking the returned count against array capacity; it prints the invalid
   clock sentinel as a frequency. Later PMUMON/P-state/power failures still permit rc=0.
   Specify partial-result behavior and test it before treating exit status as success.

These findings are about the observed snapshot. Recheck each against concurrent edits
before changing it. Preserve the existing worker's changes; do not overwrite its branch.

## Execution order and acceptance

**Packet 1 — finish the fixture, then stop for review.** Prefer vendor struct definitions.
Support only the existing probe sequence, cleanup, and explicit failure injection.
Test syscall failure, RM failure, wrong payload size, zero/max/oversized sample count,
invalid clock sentinel, changing samples, and malformed P-state. Make the suite run on
a CPU-only host with deterministic output. Do not expand this into general RM emulation.
Completion: a clean temporary build and passing tests, exact command/output recorded,
no real NVIDIA device access, and no unsupported claim of hardware fidelity.

**Packet 2 — harden the tracer against that fixture.** Require the exact supported ABI;
bound captures; distinguish syscall failure from RM failure; preserve errno; release
buffers on every path; record sequence, process/thread, fd, handles, command, input/output,
full/captured sizes and truncation. Document unsupported pointer/variadic cases rather
than claiming a universally transparent ioctl wrapper. Exercise mismatched request sizes,
failed calls and capped payloads offline. Completion: the audit describes the actual source.

**Packet 3 — resolve one telemetry meaning.** Choose the existing 0x2080a61d power
candidate. First inspect retained captures and public source. If fresh observations
remain necessary, use one direct NVML getter at a time, mark init/getter/repeat boundaries,
identify the same BDF/UUID, and retain timestamps, statuses, selectors and full payloads.
Compare requested/default/enforced limit and measured draw as separate hypotheses.
Do not fabricate fixture values as corroboration of a physical interpretation.
Completion can be either a supported contract or a precise unresolved result with the
single missing observation identified. Both are valid progress.

**Then return to firmware.** The first GSP task is one hash-keyed loader/container map
and one telemetry command traced to its proven handoff boundary. If firmware-side dispatch
cannot be located, name that missing link; do not call a host forwarding stub the firmware
implementation. Broader function matching starts only after this small artifact is reviewed.

## Rules that preserve momentum

- Keep one packet active. Park unrelated leads in a short backlog.
- Before investigating, write the question, competing explanations, cheapest distinguishing
  observation, expected result, and stopping rule in a few lines.
- After 45 minutes or two failed approaches without a new distinguishing observation,
  stop that approach. Record what failed and choose a cheaper discriminator or report
  the missing prerequisite. This is a reassessment trigger, not permission to abandon hard work.
- Every progress update contains: artifact/commit, evidence gained, remaining uncertainty,
  and one next action. A tool installation or another page of notes is not a validated result.
- Read the relevant pinned header/handler before guessing from byte magnitudes. Use fixture
  fault injection and metamorphic checks to challenge decoders; these check software behavior,
  not undocumented hardware semantics.
- The P4/P2 discrepancy is already explained by one-hot decoding. Do not reopen physical
  versus virtual P-state theories without contradictory evidence. NVML path discovery is secondary.
- No new generations, firmware branches, SKU claims, full emulation, setters, register sweeps,
  resets, unbinds or flashing in these packets. Bench-dependent tasks stay blocked while offline
  tasks proceed. Respect the repository's production-inference rule.

## Review evidence

Seven existing Python parser tests passed in the separate review checkout. The C P-state
test compiled and passed against the active checkout. A vendor-header layout probe confirmed
NVOS64 size=48/status offset=40. The new multi-call fixture compilation failed as described.
The full fake-RM shell suite was not executed because its device opens and ioctl forwarding
do not yet meet its claimed offline isolation. No GPU operations were performed for this review.

This file is a worker handoff, not evidence that the external worker has read or accepted it.

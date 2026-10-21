# Validation record — 2026-10-21

Scope: constitutional safety correction and offline tooling. No GPU, driver, firmware,
settings, production workload or running external worker was accessed or changed.
No nvidia-smi/NVML call, trace, custom ioctl or hardware experiment was performed.

## Local CPU-only verification

Host: macOS / Darwin arm64. tests/check.sh passes:
- 30 Python tests: default/legacy dry runs without collection; fixed UUID/command contract;
  root/unknown-flag refusal; unsupported/failure/identity/timeout handling without retries;
  cooldown and concurrent-attempt refusal; offline pseudo-file/symlink rejection;
  ELF segment/entry checks; RISC-V source-register/alignment/sign-extension cases;
  clock sentinel/count behavior; original vBIOS and telemetry decoder cases.
- 29 C offline-record checks, including an intentionally invalid historical pointer,
  exact ABI shape, failed syscall/stale RM status, 65536-byte cap and actual export length.
- Synthetic payload bounds/canary checks and the C P-state enum test.
- Offline rmctl build/run, refusal of live mode/device input, retired probe exit behavior,
  and shell syntax checks.

The record decoder and synthetic payload tests also pass clang AddressSanitizer and
UndefinedBehaviorSanitizer. No driver/vendor dependency is linked. A source regression
guard checks that the offline C modules have no device-open, ioctl, mapping or dynamic
interposition path. This guard is not an OS sandbox or proof about arbitrary future code.

The collector's subprocess responses are injected synthetic fixtures. The live branch is
deliberately not executed to establish its behavior. Documented telemetry still invokes a
driver; nothing here certifies live zero risk, hardware health or negligible overhead.

## Linux CI

.github/workflows/offline-checks.yml runs the same gate on a CPU-only Ubuntu runner and
refuses a runner exposing NVIDIA device nodes. Checkout is pinned to an inspected action
commit. Consult the check/run associated with the published commit for its exact outcome;
the local record above does not stand in for a Linux or production-hardware test.

## Evidence and document limits

The old raw captures and firmware inventory JSON remain unchanged. Current summaries
correct named contradictions; detailed replaced notes are archived and other reference
notes carry explicit supersession warnings. Every historical literature claim has not
been independently reverified. Hardware-dependent unknowns remain unresolved.

This change preserves the concurrent 10-monitor work through upstream commit
12301b3c4857331d154258c695fc8fb97e93e75a, while retiring its ctypes poller and correcting
its dry-run, failed-reading and capability claims. A repository update cannot stop or
reconfigure an external worker that has not adopted the new instructions.

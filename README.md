# NVIDIA GPU firmware and driver research
Deep offline reverse engineering, evidence comparison and non-intrusive monitoring.
Owner rule: **never risk the GPU or disrupt its running workload.**

Read [CONSTITUTION.md](CONSTITUTION.md), [CORRECTIONS.md](CORRECTIONS.md),
[EVIDENCE.md](EVIDENCE.md) and [LEAD-NEXT.md](LEAD-NEXT.md) first.
The rule applies to all workers. It has no bench, waiver or unsafe-flag exception.

## Research scope
Decompile and disassemble firmware, bootloaders, kernel drivers, NVML and related
libraries from existing copies; recover structures, call graphs, protocol boundaries,
units and policies; compare source, binaries, versions and architectures. CPU-only
emulation and synthetic fixtures are welcome. Do not connect that environment to a
physical GPU, hardware service, PCI resource or remote device.

Live activity is limited to the existing configuration's ordinary documented telemetry.
No custom RM/GSP calls, undocumented getters, raw PCI/BAR/MMIO/ROM/fuse access,
injection/tracing, resets, firmware/driver changes, settings changes or stress tests.
A GET label is not a safety argument. Keep missing knowledge explicitly unresolved.

## Tools and validation
- scripts/capture_state.sh: default is an offline plan, with no hardware contact.
- scripts/capture_state.py: an explicit live request performs one fixed, documented
  nvidia-smi query for a known UUID, unprivileged, with a bounded wait and no retries.
  It refuses arbitrary fields/commands, preserves N/A and stops on identity mismatch.
  A local lock refuses concurrent requests and attempts less than 10 seconds apart.
- 07-prototype/rmctl.c: offline enum decoding and retained regular-file byte display.
- 07-prototype/sniffer2.c: offline NVOS54 record decoding; no process attachment,
  pointer dereference, ioctl forwarding, NVML loading or interposition.
- 07-prototype/fake_rm.c: synthetic byte fixtures, not a driver or hardware emulator.
- scripts/parse_vbios_bit.py, inventory_firmware.py, riscv_xref.py: offline analysis.
- tests/check.sh: the CPU-only gate. Run it without any GPU access.

The live RM client, preload tracers and direct ABI probe have been retired, and tracked
prebuilt binaries removed. Earlier implementations remain in Git history for static RE.
Do not restore their execution paths. Tests do not establish live hardware safety.

## Reading order and status
[CONTROL-PLANE.md](CONTROL-PLANE.md) separates host code from firmware.
[ROADMAP.md](ROADMAP.md) is the current plan; completion claims in old logs are superseded.
[DOCUMENT-STATUS.md](DOCUMENT-STATUS.md) identifies current, historical and reference notes.
[WORKER-PROMPT.md](WORKER-PROMPT.md) is the handoff to the active worker.

Historical captures are retained unchanged in 06-ground-truth. They do not establish
present GPU health, that inference was uninterrupted, or that another worker is contained.
Replaced narrative documents are preserved under archive/2026-10-21-pre-constitution;
hardware recipes there are not authorized runbooks. Firmware binaries stay out of Git.

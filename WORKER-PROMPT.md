# Prompt for the AI worker
Read AGENTS.md, CONSTITUTION.md, CORRECTIONS.md, EVIDENCE.md and LEAD-NEXT.md from the
current branch before continuing. Adopt the safety change without overwriting concurrent
work; do not restore retired binaries or live probe paths.

The constitutional rule is: never risk my GPU or disrupt its workload. No intrusive
interventions. You may deeply decompile and reverse engineer copied firmware, bootloaders,
drivers, NVML and related code; parse containers; recover schemas/call graphs; compare
versions/architectures and other primary sources; and use CPU-only emulation and fixtures.
Keep all low-level detail you can establish, including unknowns and contradictory evidence.

Do not run custom RM/GSP calls, undocumented getters, selector/command sweeps, raw
PCI/BAR/MMIO/ROM/fuse access, live debugger/tracing/injection, guessed ctypes calls,
settings or driver/firmware changes, resets/suspend/GC6, fault injection, stress or physical
tests. No bench, waiver or VM-passthrough exception. Ordinary monitoring uses only the fixed,
documented collector, unprivileged and low-rate; its default is offline. On error, stop and
report without retries, escalation or remediation. Do not call new APIs to fill gaps.

First reconcile the retracted GPU-discovery/BoardObj and host/firmware attributions.
Then trace one telemetry path to its proven boundary and reproduce one hash-keyed firmware
container mapping plus one same-architecture version comparison. Record source commits,
artifact hashes, exact address domains, units/selectors/statuses, corroborating and conflicting
sources, uncertainty and next offline step. Strings and plausible values are leads, not proof.
No unsupported complete/verified/safe claim. Run tests/check.sh only on CPU-only infrastructure.
Preserve existing work and continue useful offline research when hardware-dependent answers
remain unknown. Report artifact/commit, evidence gained, remaining uncertainty and next action.

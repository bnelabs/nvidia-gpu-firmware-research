# Active worker direction — 2026-10-21
Read [CONSTITUTION.md](CONSTITUTION.md) and [CORRECTIONS.md](CORRECTIONS.md) first.
The owner's rule supersedes every historical bench exception. Deep offline RE is authorized.

## Packet 1: reconcile the map from existing evidence
1. Re-export the relevant pinned host-library disassembly and record hash/address domains.
2. Remove any remaining dependency on the retracted 0x214/0x21b BoardObj interpretation.
3. Trace one real telemetry path through host code and public driver dispatch to the last
   demonstrated boundary. A callback or string name is not the kernel/GSP consumer.
4. Deliver one small call graph and claim table with exact offsets/source commits and gaps.
Acceptance: reproducible offline evidence; no host VA called firmware code; no GPU contact.

## Packet 2: firmware structure and version comparison
Use existing GSP/FMC/vBIOS copies and public loader source. Recover archive directories,
section bounds, ELF segments, architecture mappings and trust-chain fields. Decompile or
emulate isolated code on CPU-only infrastructure where useful. Compare the same architecture
across nearby releases before making cross-generation claims.
Acceptance: hash-keyed structural report and one carefully matched routine/table, with
compiler/relocation/packing differences separated from behavior. Unknown keys or encrypted
regions stay unknown; do not attempt fuse reads or live loaders.

## Packet 3: monitoring contracts, offline
Audit exact installed header/library files and documented APIs. Correct the NVML ordinal
versus RM one-hot distinction, public clock-offset capability, sampling API comparison,
fan percent versus RPM, and overbroad GeForce/ECC assumptions. Reproduce contract handling
with fixtures, including unsupported, malformed, partial and timeout responses.
Acceptance: a capability matrix separating documented API, symbol availability, historical
reported result and actually retained evidence. No guessed ctypes calls or new live probe.

## Ongoing work
Maintain the finding ledger and source comparisons. Read existing logs and captures without
instrumenting the running workload. Document undocumented controls and SET paths as deeply
as possible from static code; do not invoke them. Unsupported live access is not a blocker
to offline progress. There is no automatic escalation to a bench, VM with passthrough,
debugger, privileged account, stress load or configuration change.

Run tests/check.sh on CPU only before publishing. Preserve concurrent worker commits;
fetch and compare current heads before adopting this change. Old binaries already present
in another checkout are not disabled by this commit: do not run them.

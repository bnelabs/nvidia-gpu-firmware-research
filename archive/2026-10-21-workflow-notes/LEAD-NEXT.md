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

## Offline packet checkpoint — 2026-10-21

Results and reproducible exports: [research/2026-10-21-offline](research/2026-10-21-offline/README.md).
PR #4 was fast-forwarded after a full workspace preservation archive. The map now
distinguishes file offset 0x2d1180 from host ELF VA 0x2d1180 and the two separate
55-qword tables. The public P-state wrapper reaches an indirect callback; its
conditional template path and retained-log disagreement are recorded separately.
CPU emulation checks only the pure conversion. GA102 PROD boot image/descriptor
are byte-identical in 615.71.09 and 615.78.08 after validated decompression.

Those next steps are now advanced by the
[P-state dispatch packet](research/2026-10-21-pstate-dispatch/README.md): constructor
device base `+0xa0` reconciles `+0x285e0` with device `+0x28540`; default host
dispatch reaches the NVOS54 envelope and raw ioctl PLT route. The getter can read
RUSD before falling back to `0x20802068`; historical use is consistent but unproven.
Copied RISC-V RM metadata maps 1,183 Subdevice methods and locates the direct
P-state implementation and internal shared-data setup/poll handlers. IDA works
for the copied host artifact; current REA RISC-V provider limits are retained,
with Capstone and bounded Unicorn used locally instead.

## Firmware value provenance packet direction (checkpoint before writer recovery)

1. Trace scheduler creation/callbacks reachable from firmware VA `0x1447ac8` in
   RM ELF SHA-256 `4ac95cbbe55b5e61572053d0c8a410b4de7693eaa2881d1878c76b6405426f2a`.
   Locate the actual stores to shared `perfCurrentPstate`, record offset `0x8e8`.
2. Independently resolve the concrete object getter through `+0x38` reached by
   firmware lookup `0x167de40`, and writers of returned entry `+0x34` used by
   direct handler `0x16be978`. Do not call this a physical register or assume it
   supplies RUSD until proven. Export each target calculation and raw bytes.
3. Compare the two origins; retain unknown indirect targets and scheduler effects.
   Prefer exact-release source, then applicable nouveau/nova and independent
   source. A generic protocol match is not a matching physical measurement.

Acceptance: reproducible bounded code/data evidence and one proven writer/callee
boundary, or an exact unresolved target with the cheapest next offline discriminator.
Do not boot copied firmware, invoke subscriptions/controls, poll hardware, change
provider ABI flags or escalate privileges. Tagged boot pointer meanings, other
classes, policy/security coverage and exhaustive low-level access remain open.

## Writer recovery checkpoint and active next action

[Writer packet](research/2026-10-21-pstate-writers/README.md): setup passes callback
`0x143d998`, which passes worker `0x143d878`; worker reaches refresh `0x143c6ec`.
Refresh passes shared `+0x8e8` to `0x143bde0`, which requests internal RM control
`0x20802068`, four bytes, and publishes through `0x1434cdc`. Invalidated timestamps
and retained payload semantics now have copied-instruction and cross-ISA synthetic
evidence. Actual runtime scheduling and dispatch are still not observed.

Next: recover the assignment/constructor chain for internal RM API callback at
GPU object `+0x41c0` and the concrete entry getter at table object `+0x38` reached
from firmware `0x167de40`. Then trace entry `+0x34` writers. Do not treat any of
the 210 raw `SD +0x320` encoding candidates as that constructor without full
pointer/dataflow proof. Recover an exact indirect target from copied code or
record its missing initialization; do not use live pointer reads or source-type
resemblance to fill the gap. Keep timestamp units/source unknown until decoded.

## Callback assignment checkpoint and active next action

[Callback packet](research/2026-10-21-callback-origins/README.md) resolves an
initialization block assigning `0x14078cc` at GPU-object `+0x41c0`. Exact-source
RM_API layout matches Control `+0x38`, private context `+0xe8`, size 240. The
copied initialized callback walks actual class/export metadata and reaches
`0x16be978 → 0x167de40` from the writer. One context-swap service and object graph
remain synthetic; execution stops before the unknown entry getter. No runtime
callback snapshot or proof of every later override exists.

Next: reconstruct the object loaded from GPU `+0x2000`, then the pointer at its
`+0x320` and table entry callback `+0x38`. Follow object-factory arguments,
out-parameters and initializer copies with RTTI/allocation evidence. The two
displacement-only angles (210 prior SD +0x320 candidates; 147 ADDI +0x320
candidates now) have not established that chain; do not keep broadening opcode
scans without a new discriminator. Once an exact getter target is proven, trace
entry `+0x34` writers and compare policy/cache updates with physical-read claims.
Keep timestamp implementation/units unknown. Continue offline; never fill a
pointer or object identity gap by reading the running GPU/driver.

## Object/getter checkpoint and active next action

The [object-origin packet](research/2026-10-21-object-origin/README.md) resolves
one construction branch: class ID `0xed0b65` (`Perf`) is created into GPU
`+0x2000`; table constructor callback `0x1688714` reaches base initialization
assigning table `+0x38 = 0x1757ea0`. That getter reads the remapped pointer-array
slot. Entry constructor `0x16870d4` copies a tag-8 input record's `+0x0c` word
through temporary `+4` into entry `+0x34`. Copied bounded constructor/insertion/
lookup/handler execution reproduces the transfer, with explicit fixtures and
stops before opaque component initialization. Other construction branches and
later overrides/writers are not all mapped.

Next: trace the producer of that tag-8 input record. Start with the record
pointer returned by the parsed-table callback at `0x176591c`, its interface
assignment, and wrapper `0x1768dd4 → interface+0xf0 → 0x16870d4`. Recover raw
format/validation before attributing it to VBIOS, policy or wire input. Then
trace table current-index `+0x194` selection (one store at `0x1667506` copies
`+0x1a4`) and Perf availability-gate `+0x2d7` clearing. Preserve alternate paths,
schema differences and unknown runtime inputs. Do not substitute a live pointer
read, private control, raw register query or guessed physical name for evidence.

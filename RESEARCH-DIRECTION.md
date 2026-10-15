# Research direction — reduce uncertainty before increasing scope

## Immediate finding: the P-state discrepancy was a decoder error

Pinned vendor commit `ca2d03e6fafd4d4b56b383497d931c25b283bfcf`,
`src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080perf.h`, defines
`NV2080_CTRL_PERF_PSTATES_P2 = 0x00000004U` and says currPstate uses these constants.
The recorded raw 4 therefore agrees with NVML P2. Earlier P4 interpretations and their
physical/virtual-state explanations are superseded. This is source-level interpretation
of an existing observation, not a fresh live validation. NVML's actual retrieval path is
still unknown, but identifying it is no longer needed to explain these two readings.

## Choose a bounded objective

The repo's ambition spans boot firmware, runtime firmware, telemetry, control, generations,
recovery and security. These require different evidence and cannot share one completion flag.
Default next milestone: **a reproducible, source-pinned, read-only GA102 telemetry decoder
with offline fixtures**. GSP structural analysis is a separate concurrent work packet only
when the existing worker has capacity. Mutating work waits for the bench.

## Highest-value paths

| Path | Why it helps | First deliverable | Acceptance / stop condition |
|---|---|---|---|
| Semantic decoder audit | Prevents correct bytes producing false findings | Table of command, field type, units, encoding, selector, sentinel, source commit | Every printed metric has a contract; unknown fields stay raw |
| Fake RM backend | Tests tools without risking production or requiring a GPU | Small deterministic ioctl fixture backend | Exercises syscall failures, RM failures, bad sizes, changing outputs and stale inputs; does not claim hardware fidelity |
| Direct isolated NVML getters | Separates setup traffic from requested telemetry | Marked init/getter/repeat trace with matching BDF/UUID | Full provenance and status; no field inferred solely from a plausible magnitude |
| Public driver as executable schema | Avoids guessing layouts already described in source | Trace selected control from header through handler/serialization/RPC consumer | Distinguish public host handler, forwarding and firmware handler; absent header does not prove absent implementation |
| Loader-driven GSP extraction | Establishes where code actually lives | Hash-keyed section/archive/ELF inventory | Metadata maps a name to an offset with bounds; strings proximity is not a mapping |
| Same-architecture functional diff | Avoids architecture/compiler noise | One matched routine across nearby releases | Compare normalized blocks, calls and data references; account for relocations, compression and rebuilt metadata |
| Constraint-source analysis | Distinguishes requested, default, enforced and measured power | Provenance graph for one limit and its selectors | Same GPU, timestamps, API units, statuses and policy context; no per-rail inference from one value |

## Experimental discipline

For each question record: competing explanations, cheapest distinguishing observation,
expected results under each explanation, artifacts to retain, and when to stop.

Example: a power getter returns 370000 while another report says 420 W. Alternatives include
units/encoding error, default versus enforced limit, different selector/device, stale sample,
and policy change. Start with the documented API definitions and paired existing captures.
Use natural state variation only; temporal correlation does not establish that P-state
caused a limit change. If captures are unpaired, report the relationship as unresolved.

Keep raw observations immutable. Derived reports should contain SHA-256 references, source
commit, parser version, device identity, driver version, timestamp and capture boundaries.
Use statuses: observed bytes / source-decoded / cross-validated / hypothesis / retracted.
An open API getter may initialize objects or wake hardware; read-only is not zero impact.

## GSP reverse-engineering strategy

1. Pin firmware and the loader source independently; inspect compatibility rather than
   assuming a nearby driver branch is ABI-identical.
2. Parse the documented container and archive directory before scanning for instruction
   patterns. Validate ELF machine, segments, sizes and entry-point mappings.
3. Select one question, such as the route for an already identified telemetry command.
   Start at known structures, dispatch tables and string cross-references. Separate the
   microkernel from RM application payloads; a kernel ELF may not contain power policy.
4. Recover function boundaries/call graphs for that path. Treat decompiler output as a
   hypothesis and check the instructions and calling convention.
5. Compare nearby versions for the same architecture. Preserve a reproducible script and
   an annotated small example before scaling to broad automated matching.

Full emulation is not the first step: privileged RISC-V behavior, MMIO, interrupts, DMA,
scheduling and signed boot dependencies make fidelity expensive. Start with offline parser
fixtures and, only where useful, isolated pure-function emulation. A VFIO VM still operates
real hardware and does not contain firmware damage or guarantee recovery.

## Scope and capability limits

GA102 evidence does not establish Ada/Blackwell behavior. Keep a capability matrix keyed by
chip, board, driver, firmware, OS, privilege and GSP mode, using unknown rather than inferred
support. Signature labels do not establish consumer SKU support. Public controls do not
imply every closed NVML control or policy is published. Tracing overhead must be measured,
not assumed negligible. Never run setters, broad kernel probes, MMIO reads or experiments
against production simply because an observational tool is attached.

## Worker handoff

Read this document before the older historical log. Next: finish semantic audit and tracer
fixtures; then a single isolated telemetry question with retained evidence. Bring back the
smallest reproducible artifact, not another broad survey. Hardware mutations and recovery
experiments remain gated by spare hardware and a tested recovery plan.

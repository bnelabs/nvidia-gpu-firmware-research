# Packet 3 — 0x2080a61d power candidate: investigation record

Per LEAD-NEXT.md packet 3 discipline.

## Question
What does closed control `0x2080a61d`'s 12-byte response mean?
Observed (retained capture, sniff-005239 + probe-005239, t≈2026-10-15T21:33+03:00):
`01 fe 00 00 | 50 a5 05 00 | 00 00 00 00` — u32 @+4 = 370,000 (mW hypothesis).

## Competing explanations
(a) per-rail enforced limit (NVVDD-class rail, distinct from the 420 W total limit NVML reported at that moment)
(b) state-dependent enforced limit (370 W = the limit NVML reported later at P8 idle)
(c) min limit (min_limit field NVML reported 250 W-era boards — unverified for this board)
(d) units/encoding coincidence (not mW)
(e) a different scalar entirely (sensor scale, budget…)

## Cheapest distinguishing observation
Re-run the SAME read-only NVML power query under sniffer2 now, while NVML simultaneously
reports power.limit (the invariant-check): if the @+4 u32 still reads 370,000 while NVML's
enforced limit differs from the earlier capture, (b) weakens; if it now tracks NVML's limit,
(b) strengthens. Full payloads retained this time (sniffer2 pre/post diffs).

## Expected results
- (a)/(c)/(e): @+4 invariant across states
- (b): @+4 tracks the limit changes
- units error: no plausible mW/W correspondence pattern across captures

## Stopping rule
One fresh observation + retained-capture comparison. If still unresolved: record as
"precise unresolved result" naming the single missing observation (per LEAD-NEXT.md,
"Completion can be either a supported contract or a precise unresolved result").
No setters, no forced state changes.


## PACKET B EXTENSION - NVML pstate internals decoded via REA/IDA (2026-10-16)

Tooling now LIVE: REA server v6.5.0 + IDA 9.4 container (ida94, ports 8744-8745); target
open_binary /build/libnvidia-ml-615.71.09.so (docker cp into ida94; sha256 283793c0...).

Decoded call chain for nvmlDeviceGetPerformanceState (0x99a20):
- wrapper: init-check (sub_230C0) -> sub_995F0(dev, pState) -> lock (sub_23140)
- sub_995F0 (the real impl, api.c:3563 "tsapiDeviceGetPerformanceState"):
  1. primary: dispatch-table fn-ptr at *(*(dev+165184)+368)+72 -> fills *pState
  2. gate: sub_99530(dev) != 0 AND *pState == 0 (P0)
  3. **fallback: sub_3C480(dev, pState) OVERWRITES the P0 result**

Interpretation (hypothesis until sub_3C480 decoded): NVML has a TWO-SOURCE pstate:
the primary returns P0 in states where a secondary derivation applies (e.g., effective
vs hardware state). This validates the packet-B observation structure (a P0/secondary
path exists) and explains why the open-SDK 0x20802068 control and NVML can disagree in
P0-adjacent states.

QUEUED: sub_3C480 (0x3c480) decode = the fallback source; sub_99530 (0x99530) = the gate.

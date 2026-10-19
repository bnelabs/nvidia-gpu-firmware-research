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


## PACKET B COMPLETE - fallback decoded: deviceGetClockRemappedFakePerformanceState (2026-10-16)

sub_3C480 = **"deviceGetClockRemappedFakePerformanceState"** (name from error strings
api.c:3521/3525/3544). Decoded behavior:
1. dispatch fn@+40: type-2 clock query -> v22 (current clock) + v23 (domain)  [OBSERVED]
2. dispatch fn@+320: fetch remap table -> v25=count, entries {u32 domain; u64 array}  [OBSERVED]
3. walk table: find the domain matching v23, then the P-state index whose range contains v22
4. *pState = that index; **no match -> *pState = 32 (0x20 sentinel)**  [source-decoded]

**CONCLUSION (packet B complete)**: NVML's reported P-state is a TWO-SOURCE value:
- primary = RM one-hot state (open-SDK 0x20802068 family, Pn=2^n)
- when primary == P0, NVML SYNTHESIZES a state from the CURRENT CLOCK via the
  clock-remap table ("Fake Performance State") - sentinel 32 = derivation failed.
This fully explains the historical readings: rmctl (open-SDK) and NVML agree except where
the clock-derived fallback applies. The "divergence" was two different definitions of
P-state, now both decoded. No further decode needed for this question.


## OBSERVATION 3 (2026-10-19): full a618/a612 payloads captured (sniffer bound raised to 64 KiB)

- 0x2080a618 = 20,512 B complete: sparse per-domain PMGR structure (mostly zeros;
  u16s 2832/20,000 at +0xd0; candidate 0x004C4F28 = ~5,000,000 at +0xd8 repeated)
- 0x2080a612 = 54,352 B complete (starts 0x01, large table)
- No plain u32 mW limit values (370,000/420,000/450,000/100,000) in either buffer
- STATUS: a618 = the PMGR power-info structure; field decode requires the TSAPI
  power-table definition (closed driver/GSP side) OR a bench-side differential:
  change one limit via NVML on the BENCH and diff the buffers - that single
  experiment pins the field offsets. Named as the follow-up observation.
- sniffer2 capture bound now 64 KiB (SNIF_CAP_MAX); full dumps enabled for
  0x2080a618/a612/0x214 via SNIF_DUMP_DIR.


## PACKET F COMPLETE - gate decoded (2026-10-19, REA/IDA)

sub_99530 (0xb2 B, api.c:225): the clock-remap fallback gate =
```
if (global_2D2DD4 == 0) return 0;          // global feature-enable flag
if (sub_98310(dev, &cls) != 0) return 0;   // per-device classification
return (cls - 2) <= 3;                     // TRUE iff class in {2,3,4,5}
```
The pstate two-source chain is now END-TO-END source-decoded:
1. primary = RM one-hot (Pn=2^n) via TSAPI
2. gate = global flag + device class in {2..5}
3. fallback = clock-remap lookup (sentinel 32 on failure)
Remaining sub-decode: sub_98310's classification semantics (what class 2..5 means) -
named as the next step if this thread continues; the chain structure itself is complete.

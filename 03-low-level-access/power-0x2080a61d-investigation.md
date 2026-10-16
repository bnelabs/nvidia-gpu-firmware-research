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

> HISTORICAL / SUPERSEDED. Not an authorized runbook. Claims may be retracted. Read current CONSTITUTION.md and CORRECTIONS.md at the repository root.

# Fault triage map - fault class to diagnostic signals, in priority order

For each fault class: the signals (from signal-inventory.md) a technician checks,
in the order they would check them, and the decision logic. Signal IDs reference
the inventory sections (e.g. P1 = power instant draw, E3 = remapped rows).

## Thermal throttle

Priority order:
1. N-throttle bitmask: is the thermal bit set?
2. N4: die temp vs slowdown threshold (how close?)
3. S4: memory temp (VRAM-side thermal)
4. G4: per-sensor temps (die vs VRM vs board zone - is one zone hot?)
5. N2: clock per domain (confirms the throttle is clock-visible)
6. N5: fan RPM (cooler response)

Decision logic:
- Bitmask thermal + die temp at threshold + fan at max -> cooler fault (dust,
  dead fan, dried paste). Physical inspection.
- Bitmask thermal + die temp BELOW threshold + G4 shows a VRM-zone sensor hot ->
  board-level hotspot (VRM component) -> physical inspection, thermal camera.
- Bitmask thermal + all temps fine -> sensor drift; compare multiple sensors; recalibrate expectations.
- No thermal bit but clocks low -> not thermal; check power and limiters.

## Power throttle

1. N-throttle bitmask: which power bit (power brake, SW power cap, HW power brake)?
2. P1/P2: instant vs average draw - is the card hitting the rail limit transiently?
3. P3/P4: limit vs default - is the limit owner-configured low?
4. G1: per-rail power - which rail saturates first (GPU core vs VRAM)?
5. G6: rated TDP vs configured - was the card shipped with a reduced envelope?

Decision logic:
- Draw = limit exactly and steady -> normal power-limit operation (not a fault).
- Draw = limit with big oscillation + G1 shows one rail spiking -> rail-level
  transient -> check PSU delivery (physical) and VRM health (G3 rail voltage if available).
- Limit below default -> configuration, not hardware: owner query.
- Throttle without hitting limit -> another limiter is engaged; re-check bitmask.

## VRM / power-delivery fault

1. G1: per-rail power (anomalous rail draw)
2. G3: rail voltage (VOLT class 0x12 READINGS) - droop or out-of-spec
3. G4: VRM-zone temperature sensors
4. E-series: ECC error burst correlated with load spikes (VRM-induced corruption)
5. K: XID 48 (double-bit ECC) under load = classic VRM-induced corruption signature

Decision logic:
- Rail voltage sag correlated with load spikes + ECC double-bit under load ->
  VRM degradation -> RMA / physical (no software repair).
- One rail reads zero or constant -> sensor or rail dead -> RMA.
- Voltage in spec, no ECC -> VRM is fine; re-check power source (PSU side).

## Memory ECC / row-remap

1. E1/E2: volatile + aggregate ECC counts (rate of growth)
2. K: XID 48/62/63 in the log with addresses
3. E3/E4/E5: remapped rows + histogram + banks (how much spare capacity used?)
4. E6: unrepairable flag (end of life?)
5. E9: repair status (last remap succeeded?)
6. E10: calibration lock failed (training instability)

Decision logic:
- Few correctable, no uncorrectable, remap capacity available -> monitor (healthy aging).
- Remap rate accelerating or banks exhausted -> plan replacement.
- Unrepairable flag set -> card is data-integrity-unsafe -> replace.
- Calibration failures on power-up -> PCB/solder or VRM for VRAM rails -> physical.

## PCIe link degradation

1. N8: negotiated gen/width vs expected (x16 gen4 -> x4 gen1 = severe)
2. R8: PEX counters (replay/rollover growth under load)
3. K/OS: AER correctable error rate
4. N8: throughput counters (is bandwidth actually reduced?)

Decision logic:
- Width/gen degraded permanently -> slot/riser/biostable issue -> physical.
- Normal width but growing PEX retries + AER correctables -> signal integrity
  (riser cable, slot contact) -> physical inspection, reseat.
- AER fatal or DPC -> immediate link failure -> physical/PSU.

## GSP / engine hang

1. K: XID 79/74 (GSP/NVLink fault) or XID 109 (scheduler timeout)
2. R10: GSP heartbeat liveness + RPC timeout logs
3. N2: clocks/P-state frozen?
4. K: driver-load-timeout messages at boot
5. R10: engine utilisation (is one engine stuck at 100%?)

Decision logic:
- Heartbeat dead + no RPC completion -> GSP-RM hang -> driver reload; if recurring
  across versions -> firmware/board issue -> collect logs, RMA.
- One engine stuck + contained errors (XID 94) -> engine-local fault; app-level
  recovery possible; recurring on same engine -> RMA.
- XID 109 without other errors -> almost always application bug (not hardware).

## Summary triage matrix

| Fault class | First signal | Decisive signal | Physical needed? |
|---|---|---|---|
| Thermal throttle | N-bitmask | G4 zone sensors | only to fix the cooler |
| Power throttle | N-bitmask | G1 per-rail | PSU-side check |
| VRM fault | G1 rail power | G3 rail voltage + E-series | yes (RMA) |
| Memory ECC | E1 counts | E6 unrepairable flag | yes (RMA if terminal) |
| Row remap | E3 rows | E5 banks | yes when exhausted |
| PCIe degradation | N8 link | R8 PEX counters | yes (reseat/replace) |
| GSP hang | K XID 79 | R10 heartbeat | logs; RMA if persistent |
| Engine hang | K XID 94/95 | R10 per-engine util | if same engine repeats |

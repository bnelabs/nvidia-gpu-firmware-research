# Public vs reverse-engineered vs physical - the honest gap analysis

A diagnostics company must know, for every fault class, which layer of access the
diagnosis actually requires. Three categories:

1. **Supported APIs alone** - documented NVML / nvidia-smi / kernel log. Safe,
   vendor-supported, zero liability exposure.
2. **Undocumented read paths** - our differentiation. RMCTRL GETs from the SDK
   headers, BoardObj READINGS on GSP-era classes, and the named function surface
   from our 628-tag inventory. Works on stock drivers; no vendor support if it
   breaks; legally fine on your own/customer hardware (reading is not a license
   violation), but unsupported.
3. **Physical inspection only** - no software signal exists at all. A diagnostics
   service that cannot say this will misdiagnose.

## Fully diagnosable from supported APIs alone

- Thermal throttling (bitmask + temps + clocks)
- Power-limit throttling (draw vs limit vs envelope)
- Fan failure (RPM where tachs exist)
- ECC counters (volatile + lifetime), row-remap status, unrepairable flag
- PCIe link state and AER (with OS facilities)
- XID fault classification (kernel log)
- P-state, clock envelopes, memory info, utilisation
- GPU identity, firmware versions (nvmlDeviceGet*; our fixture decode cross-checks)

**Service consequence:** a tier-1 diagnostics product needs nothing proprietary
for these. Your differentiation is not here.

## Requires undocumented read paths (our differentiation)

- **Per-rail power breakdown** (which rail saturates: core/VRAM/SoC) - PMGR power
  channels, GSP-era class 0x26-0x2D. NVML exposes only board-level watts.
- **Per-zone temperature beyond die** (VRM zone, board zone) - THERM class family
  0x22-0x25 via BoardObj READINGS. NVML exposes 1-3 named sensors only.
- **Rail voltage / VF-offset drift** - class 0xC1 GETs (GpcClk/MClk VfOffset) and
  VOLT rail READINGS. Detects factory-OC drift and VRM aging before failures.
- **Detailed throttle root cause** beyond the public bitmask - PERF_LIMIT class
  0x1D STATUS and PERF_CF controllers.
- **PMU-grade telemetry** - cDevicePerfMetricsGetSampleV1 / PmuSamples /
  ObservedRailMetricsFull (slots 41-43): high-frequency power/clock samples with
  rail attribution - the data that distinguishes transient vs sustained issues.
- **MMA stall percent** - tensor-pipe stall detection for compute health.
- **Clock margin / VF curve integrity** - headroom to limits, V/F curve health.

**Service consequence:** this is the billable tier. These reads are read-only,
work on stock drivers via RMCONTROL on the client object, and map directly to
fault classes that NVML cannot see (VRM aging, rail imbalance, V/F degradation).

## Physical inspection only - no software signal exists

Be honest about these:
- **Board-level hotspots below sensor granularity** (a specific MOSFET or choke
  running hot): a thermal camera sees what the sensors do not - GPUs have 1-5
  sensors, boards have dozens of hot components.
- **Capacitor aging / bulging** - no electrical signal until failure.
- **Solder-joint / BGA microcracks** - intermittent by nature; may show as ECC
  or PCIe errors only under thermal cycling; localization is physical.
- **Fan bearing wear** (RPM still nominal, noise/vibration present) - acoustic.
- **PSU delivery under transient load** (ripple, droop at the wall side) -
  oscilloscope at the 12V input; software sees only the consequence.
- **Visual inspection: burn marks, corrosion, cracked PCB, missing components.**
- **Cooler contact quality** (paste pump-out, mounting pressure) - die temp may
  look normal while hotspot-to-sensor delta is physical.

**Service consequence:** software diagnosis produces a *triage*, not a *verdict*.
The physical tier is a partner-lab capability, not a software feature.

## Summary matrix

| Diagnostic tier | Faults covered | Tooling | Margin profile |
|---|---|---|---|
| Supported APIs | thermal, power, fan, ECC, PCIe, XID | NVML/nvidia-smi | commodity (everyone can) |
| Undocumented reads (ours) | rail-level, VRM aging, V/F drift, PMU telemetry | our rmctl + decode stack on stock drivers | differentiated |
| Physical | hotspots, caps, solder, acoustic, PSU | partner lab | service network, not software |

## The one-line positioning

NVML tells you THAT something is wrong for ~60% of fault classes; our decoded
read paths tell you WHERE and WHY for most of the rest; physics tells you WHICH
COMPONENT. A complete service sells all three tiers in that order.

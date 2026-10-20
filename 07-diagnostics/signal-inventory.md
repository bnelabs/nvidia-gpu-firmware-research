# Signal inventory - every read-only diagnostic observable on a GA102-class GPU

Scope: read-only signals only. If a signal requires a write to observe, it is excluded.
Layer codes: N = documented NVML (driver 615 public API), S = nvidia-smi presentation
of N, R = RMCTRL GET from the r615 SDK headers (vendor-documented control IDs),
B = BoardObj READINGS method (r615 ctrl2080boardobj.h), G = GSP-era class from the
BoardObj taxonomy (agent-verified, no public name), P = BAR0/physical (own-hardware
only), K = kernel log (XID, documented).

## 1. Power

| Signal | Layer | Measures | Diagnostic meaning | Status |
|---|---|---|---|---|
| Power draw (instant) | N | board watts | overload, PSU issue | documented (nvmlDeviceGetPowerUsage) |
| Power draw (average) | N | 1 s window board watts | transient vs sustained overload | documented |
| Power limit | N | enforced limit (W) | is the card capped below spec | documented |
| Power min/default/max limit | N | limit envelope | misconfigured or locked card | documented |
| Per-rail power (HW rail breakdown) | G | per-rail W via PMGR power channels (class 0x26-0x2D, PWR_CHANNEL=0x28) | which rail (GPU/VRAM/SoC) drives the load | reverse-engineered (PMGR class verified in GSP strings) |
| Power policy state | G | PMGR PWR_POLICY object (0x29) | which policy constrains the card | reverse-engineered |
| Rated TDP control | R | NV2080_CTRL_CMD_PERF_RATED_TDP_GET_CONTROL (ctrl2080perf.h) | nameplate vs configured TDP | vendor-documented |
| Energy counter | S | cumulative board energy | long-term efficiency tracking | documented |

## 2. Clocks

| Signal | Layer | Measures | Diagnostic meaning | Status |
|---|---|---|---|---|
| P-state | N | performance state (one-hot, P0-P15) | throttled vs intended | documented (synthesis chain decoded - see power-provenance.md) |
| Clock per domain (graphics, SM, mem, video, DSP) | N | MHz per NVML clock type | per-domain capability loss | documented (nvmlDeviceGetClockInfo) |
| Max/app clocks | N | clock envelope | locked clocks, silent-profile caps | documented |
| PMUMON clock-domain samples | R | NV2080_CTRL_CMD_CLK_PMUMON_CLK_DOMAINS_GET_SAMPLES (ctrl2080clk.h; the 0x20801037 path our tools decode) | high-frequency clock behaviour (bounces, dips) | vendor-documented ID, semantics from our decode |
| Clock margin | G | cDeviceGetClockMarginMHz (slots 25-26) | headroom to limit | reverse-engineered (rmfunctions-slot-map.json) |
| VF curve point | G | cDeviceGetInstructionAwareVFCurve (slots 30/31 family) | voltage-frequency health | reverse-engineered |

## 3. Voltage

| Signal | Layer | Measures | Diagnostic meaning | Status |
|---|---|---|---|---|
| VF offset (current) | G | cDeviceGetGpcClkVfOffset / GetMClkVfOffset (slots 20-24, class 0xC1) | undocumented offset drift (factory OC or degradation) | reverse-engineered |
| Rail voltage (V) | G | VOLT_VOLT_RAIL class 0x12 via BoardObj READINGS | VRM output health | reverse-engineered (public class ID; no public per-device read path) |
| VF point voltage | G | CLK_CLK_VF_POINT (0x05) VOLT point | V/F curve integrity | reverse-engineered |

## 4. Temperature

| Signal | Layer | Measures | Diagnostic meaning | Status |
|---|---|---|---|---|
| GPU die temp | N | current (C) | overheat, cooler fault | documented |
| Shutdown/slowdown temps | N | thresholds | proximity to protection | documented |
| Memory temp | S | HBM/GDDR junction (where exposed) | VRAM thermal fault | documented (architecture-dependent) |
| Per-sensor temps | G | THERM family: THERM_DEVICE=0x22, CHANNEL=0x23, MONITOR=0x25 via BoardObj READINGS | per-zone sensors (die, VRM, board) | reverse-engineered (class IDs verified in GSP strings) |
| Thermal limit reasons | N | bitmask | which threshold engaged | documented |

## 5. Fan / cooling

| Signal | Layer | Measures | Diagnostic meaning | Status |
|---|---|---|---|---|
| Fan speed (RPM) | N | current RPM per tach | fan failure, obstruction | documented (where tachs exist) |
| Fan control mode | G | FAN_COOLER=0x16, FAN_POLICY=0x17 via cDeviceFanCoolerGetControl | who drives the fan | reverse-engineered |
| Cooler status | G | cDeviceFanCoolerGetStatus | stall detection at policy level | reverse-engineered |

## 6. ECC / memory health

| Signal | Layer | Measures | Diagnostic meaning | Status |
|---|---|---|---|---|
| ECC volatile counts | N/R | correctable + uncorrectable | failing VRAM cell | documented + NV2080_CTRL_CMD_ECC_GET_VOLATILE_COUNTS |
| ECC aggregate (lifetime) | N | total since reset-to-black | aging VRAM | documented |
| Remapped rows | R | NV2080_CTRL_CMD_FB_GET_REMAPPED_ROWS | pending remaps = future hard fault | vendor-documented |
| Row remapper histogram | R | NV2080_CTRL_CMD_FB_GET_ROW_REMAPPER_HISTOGRAM | distribution of remap usage | vendor-documented |
| Remapped banks | R | NV2080_CTRL_CMD_FB_GET_REMAPPED_BANKS | which banks are degraded | vendor-documented |
| Unrepairable memory flag | R | NV2080_CTRL_CMD_ECC_GET_UNREPAIRABLE_MEMORY_FLAG | card beyond software repair | vendor-documented |
| ECC client exposed counters | R | NV2080_CTRL_CMD_ECC_GET_CLIENT_EXPOSED_COUNTERS | which IP block throws errors | vendor-documented |
| SRAM unique uncorrectable | R | NV2080_CTRL_CMD_ECC_GET_SRAM_UNIQUE_UNCORR_COUNTS | L2/ROP damage | vendor-documented |
| ECC repair status | R | NV2080_CTRL_CMD_ECC_GET_REPAIR_STATUS | last remap result | vendor-documented |
| Calibration lock failed | R | NV2080_CTRL_CMD_FB_GET_CALIBRATION_LOCK_FAILED | memory-training instability | vendor-documented |

## 7. Performance-limit (throttle) bitmask

| Signal | Layer | Measures | Diagnostic meaning | Status |
|---|---|---|---|---|
| Active perf limiter reasons | N | bitmask (thermal, power, SW cap, HW slowdown, sync boost, idle) | exact throttle cause | documented |
| Limiter detail (GSP-era) | G | PERF_LIMIT class 0x1D via BoardObj STATUS | root-cause beyond the public bitmask | reverse-engineered |

## 8. PCIe / bus

| Signal | Layer | Measures | Diagnostic meaning | Status |
|---|---|---|---|---|
| Link gen/width | N | negotiated PCIe state | degraded slot/riser | documented |
| PEX counters | R | NV2080_CTRL_CMD_BUS_GET_PEX_COUNTERS | retry/replay rates = signal integrity | vendor-documented |
| PCIe AER (correctable/fatal) | K + OS | kernel AER log | link-level errors | documented (OS facility) |
| Throughput counters | N | rx/tx per direction | bandwidth saturation | documented |

## 9. XID error families (kernel log)

| Signal | Layer | Measures | Diagnostic meaning | Status |
|---|---|---|---|---|
| XID 13 (MMU fault) | K | address decode of bad access | app bug or corrupted page tables | documented |
| XID 31 (GPU page fault) | K | faulted VA + client | same, with VA detail | documented |
| XID 43/45 (robust channel) | K | user channel preemption | app recovery | documented |
| XID 48 (double-bit ECC) | K | uncorrected ECC death | VRM/VRAM hardware | documented |
| XID 62/63 (row remap) | K | remap events | VRAM degradation | documented |
| XID 74/79 (NVLINK/GSP fault) | K | GSP/NVLink errors | GSP-side fault | documented |
| XID 94/95 (contained/uncontained) | K | engine error containment | which engine faulted | documented |
| XID 109 (context switch timeout) | K | scheduler hang | app or driver hang | documented |

## 10. GSP / engine health

| Signal | Layer | Measures | Diagnostic meaning | Status |
|---|---|---|---|---|
| GSP heartbeat | R | periodic GSP-RM liveness | GSP-RM hang | vendor-documented (kernel source) |
| GSP RPC timeouts | K | RPC completion logs | firmware responsiveness | documented |
| Engine utilisation samples | R | NV2080_CTRL_CMD_PERF_GET_GPUMON_PERFMON_UTIL_SAMPLES_V2 | per-engine activity | vendor-documented |
| Observed rail metrics (full) | G | cDevicePerfMetricsGetObservedRailMetricsFull (slot 42) | per-rail telemetry beyond NVML | reverse-engineered |
| PMU samples | G | cDevicePerfMetricsGetPmuSamples / GetSampleV1 (slots 41/43) | high-frequency power/clk samples | reverse-engineered |
| MMA stall percent | R | cDeviceGetMmaStallPercent (slots 4/40) | tensor-pipe stall | reverse-engineered |
| Memory-controller status | R | NV2080_CTRL_CMD_FB_GET_INFO_V2 + ECC family | training state | vendor-documented |

## Read-only confirmation

Every entry above is observed with GET-class paths only. No SET, no register writes,
no mode changes. The RMFunctions inventory marks the complementary SET paths
(SetPerfLimitersClocks etc.) which are excluded from diagnostics use by policy
(see operating-envelope.md).

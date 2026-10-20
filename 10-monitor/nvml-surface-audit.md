# NVML surface audit - the installed 615.71.09 driver, ground truth

Method: `readelf -Ws` on the loaded `libnvidia-ml.so.615.71.09` (431 exported
nvml* symbols, 302 nvmlDevice*), then call-level probes via ctypes on the host's
own GPU (normal NVML polling only). Classification: RETURNS_DATA (rc=0),
NOT_SUPPORTED (rc=3), INVALID_ARG (rc=2, my signature wrong), ABSENT (no symbol),
STRUCT (present, struct-based signature - usable by the collector via headers
compiled from the published nvml.h, but not probed in this pass).

## Audit result (call-level, live GPU)

### Returns data on this host (the buildable surface)
| Function | Notes |
|---|---|
| nvmlDeviceGetPowerUsage | board watts |
| nvmlDeviceGetEnforcedPowerLimit | enforced W |
| nvmlDeviceGetTotalEnergyConsumption | cumulative mJ |
| nvmlDeviceGetTemperature (GPU sensor) | die temp C |
| nvmlDeviceGetTemperatureThreshold | per-threshold values |
| nvmlDeviceGetFanSpeed_v2 | fan % (v1 signature INVALID_ARG - deprecated variant) |
| nvmlDeviceGetMinMaxFanSpeed | fan range |
| nvmlDeviceGetTargetFanSpeed | target % |
| nvmlDeviceGetMaxClockInfo | max clock per domain |
| nvmlDeviceGetMinMaxClockOfPState | per-Pstate clock range |
| nvmlDeviceGetCurrentClocksThrottleReasons | throttle bitmask |
| nvmlDeviceGetSupportedClocksThrottleReasons | bitmask definition |
| nvmlDeviceGetCurrPcieLinkGeneration | PCIe gen |
| nvmlDeviceGetCurrPcieLinkWidth | PCIe width |
| nvmlDeviceGetGpcClkVfOffset | GPC VF offset (int) - **public** |
| nvmlDeviceGetMemClkVfOffset | MEM VF offset (int) - **public** |
| nvmlDeviceGetPerformanceState | one-hot P-state |
| nvmlDeviceGetNumFans | fan count |
| nvmlDeviceGetVbiosVersion | vBIOS string |
| nvmlDeviceGetGspFirmwareVersion | GSP fw string |
| nvmlSystemGetDriverVersion | driver string |

### Present but NOT_SUPPORTED on this GeForce card
| Function | Meaning |
|---|---|
| nvmlDeviceGetClockInfo | deprecated v1 path (this driver migrated; use GetMaxClockInfo/GetClock family) |
| nvmlDeviceGetApplicationsClock | datacenter-style app clocks |
| nvmlDeviceGetTotalEccErrors | aggregate ECC - GeForce gating |
| nvmlDeviceGetRemappedRows | row remap info - GeForce gating via this path |
| nvmlDeviceGetRowRemapperHistogram | same |

### Present, struct-based signatures (usable, not probed in this pass)
nvmlDeviceGetClockOffsets, nvmlDeviceGetCurrentClockFreqs, nvmlDeviceGetMarginTemperature,
nvmlDeviceGetSramEccErrorStatus, nvmlDeviceGetSramUniqueUncorrectedEccErrorCounts,
nvmlDeviceGetClkMonStatus, nvmlDeviceGetFieldValues, nvmlDeviceGetSamples

### ABSENT from this driver (published-API functions that do not exist here)
| Function | Consequence |
|---|---|
| nvmlDeviceGetPowerSamples | high-frequency power sampling NOT available via NVML |
| nvmlDeviceGetFanSpeedRPM | symbol exists in readelf list but dlsym-visible variant differs; v2 covers |
| nvmlDeviceGetApplicationsClocks (plural) | renamed to singular Clock in this driver |

## Key corrections vs the published NVML header

1. **The published header does not match this driver.** Plural/singular renames
   (GetApplicationsClocks -> GetApplicationsClock), v1->v2 fan signature migration,
   and outright absences (GetPowerSamples). The collector must be built against
   THIS audit, not the header.
2. **ECC aggregate/remap APIs are GeForce-gated** on this driver (NOT_SUPPORTED)
   even though the RTX 3090 has remappable GDDR6. Row-remap visibility on GeForce
   must come from a different surface (kernel log XID 62/63, or the Sram* struct
   functions) - not from these calls.
3. **VF offsets are PUBLIC**: nvmlDeviceGetGpcClkVfOffset and GetMemClkVfOffset
   both return data. This removes one of our claimed differentiators (VF drift
   reading is public on this driver).
4. **MarginTemperature symbol exists** - the clock-margin signal may also be
   public once its struct signature is wired. Second differentiator at risk.

## Ground-truth summary for the collector

Build against: power (3), temperature (2), fan (4), clocks (2 + struct family),
throttle reasons (2), PCIe (2), VF offsets (2), identity (3), P-state (1),
plus struct-based margin/ECC/SRAM functions where headers permit. XID parsing
from the kernel log, driver/BIOS identity from NVML. Everything else (remapped
rows on GeForce, PMU telemetry, rail power, zone temps) is NOT reachable via
NVML on this driver and stays out of the v1 collector.

> HISTORICAL / SUPERSEDED. Not an authorized runbook. Claims may be retracted. Read current CONSTITUTION.md and CORRECTIONS.md at the repository root.

# NVIDIA tooling gap - what the vendor's own tools already cover

Purpose: price honestly. If NVIDIA's free tooling already diagnoses a fault class,
your product does not get paid for it. This maps the public tool surface (from
public documentation only - no internal tools claimed) and states the plain
conclusion.

## The tools

### dcgmi diag (DCGM, data-center GPU management)
- Covers: memory/CPU/pipeline stress tiers (rampmed short/medium/long), NVLink
  tests, PCIe tests, target temperature, EUD (early unit diagnostics) on
  supported SKUs, field diagnostics with JSON output, integration hooks.
- Best at: systematic pass/fail on data-center SKUs, scheduled burn-ins,
  NVLink fabric faults, baseline-style stress.
- Misses: consumer (GeForce) SKUs largely unsupported; no per-rail attribution;
  no VRM/zone-level insight; requires DCGM stack install (not for customer
  gaming machines); deep diagnosis is data-center-oriented.

### nvidia-bug-report.sh
- Covers: full state collection - logs, registry dumps, driver state, module
  info - for vendor support escalation.
- Best at: packaging evidence for an RMA or NVIDIA support ticket.
- Misses: no analysis, no verdict, no trend history; reactive (needs a live
  system); does not interpret.

### nvidia-debugdump
- Covers: dumping internal GPU engine state (pState dumps) for support.
- Best at: capturing engine state after a crash for vendor analysis.
- Misses: no interpretation, no proactive monitoring, not a triage tool.

### NVAPI (Windows) diagnostics
- Covers: GPU/fan/thermal queries, D3D/NVAPI sensor surface on Windows.
- Best at: Windows-side parity with NVML.
- Misses: same NVML-level granularity; no rail-level data.

### MATS/MODS
- Vendor-internal field memory tests (partner distribution). Not publicly
  redistributable; on-datacenter and partner RMA flows. A service cannot
  legally ship them; approximations only (see pre-enumeration-workflow.md
  stage 5).

### nvidia-smi / NVML (the baseline)
- Covers: everything in signal-inventory.md tier 1 - temps, clocks, power,
  ECC, throttle bitmask, PCIe, P-state, XID correlation via logs.
- Best at: the ~60% of fault classes that need no proprietary access.
- Misses: per-rail power, zone-level thermal attribution, VF-offset drift,
  high-frequency power telemetry (nvmlDeviceGetPowerSamples absent in 615.71.09),
  VRM-health signals, GSP-era sensor granularity.

## Plain conclusion

**Already free (N = 8 fault classes):** thermal throttle, power-limit throttle,
fan failure, ECC counter trends, row-remap status, PCIe link/AER, XID family
triage, P-state/clock envelope anomalies. A service CANNOT charge for these
alone - nvidia-smi plus kernel logs does them.

**Not free (M = 5 fault classes, our gap):**
1. VRM / power-delivery degradation (rail-level power anomaly attribution)
2. V/F curve degradation and factory-OC drift detection (VF-offset reads)
3. High-frequency power transient analysis (PMU telemetry; the public samples
   API is missing in this driver generation)
4. Clock-margin / headroom trending (aging prediction)
5. Sensor-vs-board cross-verification beyond the 1-3 NVML sensors
   (GSP-era sensor granularity - pending the claim-(ii) wire capture)

The billable line: NVIDIA tells the customer THAT the card throttles; our tier
tells them WHICH rail and WHETHER it is aging - before failure. That delta is
the product.

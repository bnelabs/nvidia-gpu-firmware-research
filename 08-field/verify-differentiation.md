# Verify-differentiation: the six D1/D3 claims, proven or disproven against r615 source

This document decides whether the diagnostics business case survives contact with
the actual firmware/driver evidence. Each claim: source-pinned or inferred, the
file:line evidence, confidence, and what would confirm an inferred claim.

## Claim (i) - per-rail power via PMGR 0x26-0x2D

**Verdict: SOURCE-PINNED (verified).** Confidence: HIGH.

Evidence:
- Rail/channel structures exist in the shipped GSP-RM: firmware strings
  UNLOAD_DRIVER_VOLTAGE_RAIL_0, _1, _2, PWR_RAIL_MISMATCH,
  RMConvertSplitRailSingleStepToMultiStepWAR (gsp-kernels/615-kernel-10.elf, strings pass)
- Policy/channel types verified in GSP assert strings:
  NV2080_CTRL_PMGR_PWR_CHANNEL_OUTPUT_VOLTAGE_1X_VOLT_MODE_NUM,
  NV2080_CTRL_PMGR_PWR_POLICY_TYPE_WORKLOAD_DIE_2X,
  NV2080_CTRL_PMGR_PWR_POLICY_WORKLOAD_PHYSICAL_SINGLE_2X_MAX (same ELF)
- Class IDs 0x26-0x2D from the Tegra nvgpu public enumeration
  (boardobjgrp_classes.h), lineage verified in GSP strings (taxonomy agent)
- 0x2080a61d (our captured 12 B control) = PMGR_LEGACY_NON_PRIVILEGED msg 0x1D -
  the BoardObj-based power-rails subsystem control, confirmed in ctrl2080base.h

Origin: PMGR PWR_DEVICE objects (class 0x27) each carrying PWR_CHANNEL (0x28)
children per physical rail; readings flow through the BoardObj READINGS method
to the 0x2080a6xx RMCTRL surface.

Impact on D2: the VRM-fault first signal (G1 per-rail power) STANDS.

## Claim (ii) - zone-level temperatures including a VRM zone

**Verdict: PARTIALLY VERIFIED / INFERRED.** Confidence: MEDIUM for the class,
LOW for the specific VRM-zone-on-GA102 claim.

Evidence for the class: THERM_DEVICE=0x22, THERM_CHANNEL=0x23, THERM_POLICY=0x24,
THERM_MONITOR=0x25 in the public enumeration; identical NV2080_CTRL_THERM naming
in the GSP taxonomy (agent-verified lineage).

Evidence AGAINST over-claiming: ctrl2080therm.h does not exist in the r615 SDK
(no therm header at all) - the therm family is FINN-stubbed out of the public SDK.
No GSP string in our corpus names a VRM-zone sensor explicitly. The VRM zone is an
inference from board design (VRM thermistors exist on every AIB card) combined with
the existence of a multi-channel THERM class - not from a captured payload.

What would confirm: a sniffer2 wire capture of THERM channel READINGS payloads on
a GA102 under load, or an IDA pass on the THERM dispatcher channel-count logic.
Marked OPEN - not chased per instructions.

**Impact on D2 (not softened):** the thermal decision step "G4 shows a VRM-zone
sensor hot" is DOWNGRADED from confirmed to conditional. Per-zone VRM attribution
is NOT yet a proven software capability on GA102; thermal triage remains deliverable
via die-temp + power correlation, but zone attribution must not be promised until
the wire capture exists.

## Claim (iii) - VF offset drift observability

**Verdict: SOURCE-PINNED (verified).** Confidence: HIGH.

Evidence: RMFunctions slots 20-24 carry cDeviceGetGpcClkVfOffset /
cDeviceGetMClkVfOffset / cDeviceGetClkMinMaxVfOffset (rmfunctions-slot-map.json,
tag-anchored via the 628-tag inventory). GET path exists, class 0xC1. Offsets are
firmware state - reading them is a pure GET.

Impact on D2: V/F drift detection STANDS as a differentiator.

## Claim (iv) - rail voltage readback

**Verdict: INFERRED (not proven).** Confidence: LOW-MEDIUM.

Evidence for: VOLT_VOLT_RAIL class 0x12 exists in the public enumeration;
ctrl2080volt.h exists but is an empty FINN stub (38 lines, includes only) - no
public payload structure. The pstate chain proves voltage values exist in the V/F
system (CLK_VF_POINT VOLT type, ucode_clk_inf.h).

Evidence against: we have never captured a rail-voltage payload on the wire; the
host-side read path is unproven; the value may exist only inside the GSP policy
engine, surfaced indirectly (as clock margins) rather than raw volts.

What would confirm: wire capture of a VOLT-class READINGS payload, or a trace of
the clock-margin computation back to a voltage field. Marked OPEN.

**Impact on D2 (not softened):** the VRM-fault DECISIVE signal (G3 rail voltage)
is INFERRED. Read the VRM triage row as: first signal (rail power, G1) verified;
decisive signal (voltage) unproven - practical VRM-fault evidence today is
rail-power anomalies + ECC-under-load correlation, with voltage as a candidate
capability pending verification.

## Claim (v) - PMU-level telemetry

**Verdict: SOURCE-PINNED (verified).** Confidence: HIGH.

Evidence: slots 41-43 = cDevicePerfMetricsGetPmuSamples / GetSampleV1 /
ObservedRailMetricsFull (rmfunctions-slot-map.json); the RMCTRL ID
NV2080_CTRL_CMD_PERF_GET_GPUMON_PERFMON_UTIL_SAMPLES_V2 is vendor-documented
(ctrl2080perf.h); GPUMON sample types PWR_MONITOR_STATUS + PERFMON_UTIL are public
(ctrl2080gpumon.h:41-42).

Corroborating negative: nvmlDeviceGetPowerSamples is ABSENT from the installed
615.71.09 NVML (dlsym check) - the high-frequency power-sample capability is NOT
exposed by the public API, so our decoded path is genuinely differentiating here.

Impact on D2: PMU telemetry STANDS - the missing NVML symbol strengthens it.

## Claim (vi) - clock margin

**Verdict: SOURCE-PINNED (verified).** Confidence: HIGH.

Evidence: slots 25-26 = cDeviceGetClockMarginMHz /
cDeviceGetMinTargetSmClockMHzUncached (rmfunctions-slot-map.json). GET-only reads.

Impact on D2: clock headroom diagnostics STAND.

## Summary table

| Claim | Verdict | Confidence | Key evidence | Open item |
|---|---|---|---|---|
| (i) per-rail power | SOURCE-PINNED | HIGH | rail strings + PMGR classes in GSP ELF | none |
| (ii) VRM zone temp | INFERRED | LOW (VRM zone) | THERM classes exist; SDK header absent | wire capture of THERM READINGS |
| (iii) VF offset drift | SOURCE-PINNED | HIGH | slots 20-24 tag-anchored | none |
| (iv) rail voltage | INFERRED | LOW-MEDIUM | class exists; payload never captured | wire capture or margin-computation trace |
| (v) PMU telemetry | SOURCE-PINNED | HIGH | slots 41-43 + missing nvmlDeviceGetPowerSamples | none |
| (vi) clock margin | SOURCE-PINNED | HIGH | slots 25-26 tag-anchored | none |

## Business-case verdict

**Survives - with two honest corrections.** Four of six claims are source-pinned
HIGH. Two (VRM zone temperature, rail voltage) are inferred and must be verified
by wire capture before they are sold. The corrected differentiator set: per-rail
power (proven), VF drift (proven), PMU telemetry (proven - public API missing its
equivalent), clock margin (proven) - plus two candidate capabilities pending one
wire-capture session. Apply fault-triage-map.md with G3 marked "candidate,
unproven" until then.

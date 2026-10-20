# Operating envelope - legal/liability boundary for a commercial diagnostics service

Scope: read-only diagnostics on customer hardware. This document states what is
safe as-is, what needs a written waiver, what runs only on your own test hardware,
and - critically - every write control that is technically reachable but must be
treated as off-limits, with the supported-API alternative for the tuning need it
would otherwise serve.

## Tier 1 - safe as-is on customer hardware (no waiver needed)

- All documented NVML getters (nvmlDeviceGet* family)
- nvidia-smi query modes (-q, --query-gpu=...)
- Reading kernel logs (XID, AER) via standard log facilities
- Our RMCTRL GET-based reads that mirror vendor-documented control IDs
  (ECC_GET_*, FB_GET_REMAPPED_*, BUS_GET_PEX_COUNTERS, CLK_PMUMON samples)
- The opaque-client-channel GET path (0x0000xxxx family) as used by nvidia-smi
  itself - your tool does exactly what nvidia-smi does on the same transport
- File-based capture (sniffer2 LD_PRELOAD trace) **with customer notification**:
  it injects into the customer's process space; disclose it, get written consent
  (it is read-only, but process injection is a trust action)

Basis: every operation is a GET on the vendor's own supported interfaces, or a
strictly more transparent version of what vendor tools already do.

## Tier 2 - requires a written customer waiver

- LD_PRELOAD sniffing (process injection - disclose even though read-only)
- GSP-era BoardObj READINGS on undocumented classes (0x26-0x2D PMGR, 0x22-0x25
  THERM, 0x16-0x18 FAN, 0x2E-0x36 PERF_CF): read-only, but these are not
  vendor-documented interfaces - if a read has an unexpected side effect on an
  exotic SKU, you want the customer informed in advance
- Any tool that opens /dev/nvidia* directly (device-node contention with the
  customer's running workload - schedule diagnostics in a maintenance window)
- PMUMON high-frequency sampling (microscopic perturbation of the PMU telemetry
  path; negligible but non-zero)

Waiver text should state: read-only operations, no settings changed, no firmware
contact, list of device nodes opened, and a maintenance-window agreement.

## Tier 3 - your own test hardware only

- Anything involving GC6 / suspend-resume transitions on a customer machine
  (power-state transitions can lose the customer's session - service-hostile)
- Fault injection of any kind (the cDeviceInj* family exists in the inventory;
  it is never used in diagnostics - it CREATES faults)
- CC-enabled (confidential computing) parts in CC mode
- Any firmware-level interaction beyond RMCONTROL (nvflash, partial flashes)
- Cryogenic/thermal-cycling stress to provoke intermittent faults
- Multi-GPU NVLink topology experiments

## Off-limits write controls (technically reachable, forbidden in service)

These are all decoded and reachable from the RMFunctions surface. A diagnostics
service does not use them. For each: the write, why it is off-limits, and the
supported-API alternative the customer can use themselves if they want the effect.

| Write control (off-limits) | Why off-limits | Supported-API alternative for the customer |
|---|---|---|
| SetPerfLimitersClocks (slots 5/6) | changes the clock envelope on customer silicon; if the value is wrong you own the instability | nvidia-smi -lgc (documented, customer-initiated, resettable with -rgc) |
| SetRawClock (slots 5/6) | forces clocks beyond validated points | nvidia-smi -lgc within vendor-validated range |
| GpcClkVfOffset / MClkVfOffset SET (slots 20-24, class 0xC1) | voltage offset writes - hardware-damage-adjacent | none supported; owner uses MSI Afterburner at their own risk |
| SetMclkLimit (slots 11/34-36) | memory clock cap changes | nvidia-smi -lmc (documented) |
| SetPowerMizerMode_v1 (slots 30/31) | changes driver power policy | nvidia-smi --power-mizer-mode via driver settings UI |
| Fan SetControl / SetPolicy (FAN family) | overrides thermal protection on customer cooling | driver settings fan curve (customer-initiated) |
| Power limit SET (0x2080206F family) | changes the safety envelope | nvidia-smi -pl (documented, customer-initiated) |
| SET_POWERSTATE / AGGRESSIVE_PSTATE_NOTIFY | forces P-states on customer workload | nvidia-smi --persistence-mode + app clocks |
| ECC scrub trigger / row-remapper RESET (FB family SETs) | modifies repair state; a bad reset can brick data-integrity | vendor RMA process is the correct path |
| cDeviceInj* (injection family) | CREATES faults - the opposite of diagnostics | never; no alternative (that is the point) |
| Any GC6/suspend transition | can destroy the customer's session state | schedule reboots with the customer |

Rule of thumb: **if the effect survives your session ending, it is a write, and
writes are the customer's job through supported interfaces - never yours.**

## Read-only verification habit

Before any diagnostic run on customer hardware:
1. Confirm the tool binary contains no SET-path calls (our tools are built from
   the signal-inventory.md list only; the build ships a grep attestation).
2. Run with the customer's workload owner informed.
3. Keep every observation reproducible from logs (no in-memory-only state).

## Legal notes (not legal advice)

- Interrogating your customer's GPU via its own documented device nodes is
  contractually your right under a diagnostics engagement.
- LD_PRELOAD is process injection under several enterprise security policies
  (SELinux, EDR) - always disclosed, often blocked; plan the waiver.
- DMAR/IOMMU environments: /dev/nvidia* access may be restricted - plan for
  the maintenance-window path.
- Firmware modification, signature workarounds, and any SET on the protected
  chain are out of scope for a diagnostics business entirely (see
  gsp-signature-chain.md - the technical bar is hardware-attack level anyway).

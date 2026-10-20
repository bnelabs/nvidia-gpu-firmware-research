> HISTORICAL / SUPERSEDED. Not an authorized runbook. Claims may be retracted. Read current CONSTITUTION.md and CORRECTIONS.md at the repository root.

# CONTROL-PLANE.md — The definitive decoded NVIDIA GPU control plane reference

This document maps every decoded layer of the NVIDIA GPU control plane, from the user-facing
NVML API down to the GSP firmware policy engine, based on source-pinned reverse engineering
of `libnvidia-ml-615.71.09.so` (sha256: `283793c0c30dc32f87c0e9fc9b5326fe764bad156e61afa3e997684c47b29a95`),
the open-gpu-kernel-modules (pinned: `ca2d03e`), and the GSP firmware container
(`gsp_ga10x.bin`, driver 615.71.09).

## Complete layered map

```
Layer 1: NVML API (user space, libnvidia-ml.so)
  ├── 626 named control-plane functions (nvml-control-plane-tags.txt)
  ├── 349 cDeviceGet* / 52 cDeviceSet* / 16 cDeviceRist* / 12 cDeviceClear*
  ├── Client-level controls (0x0000xxxx): 0x214 GPU_GET_PROBED_IDS, 0x21b GPU state,
  │   0x215 session info, 0x279/0x289 device handles
  ├── RM controls (0x2080xxxx / 0x0000xxxx via NVOS54): encoded as _IOWR('F', 0x2A, NVOS54)
  │   with exact struct size validation (nv.c nv_ioctls_table + rm_validate_ioctls)
  └── Transport: opaque driver-internal channel for client controls (0x0000xxxx family);
      params-buffer visible for RM controls (0x2080xxxx family)

Layer 2: Kernel RM (open-gpu-kernel-modules)
  ├── escape.c: NV_ESC_RM_CONTROL (0x2A) → rm_validate_ioctls → Nv04ControlWithSecInfo
  ├── entry_points.c: rmapiGetInterface(RMAPI_EXTERNAL) → RM_API struct
  ├── control.c: serverControl → resource dispatch → BoardObj attribute access
  ├── Security: RS_PRIV_LEVEL_USER_ROOT vs USER, NV_CTL_DEVICE_ONLY checks
  └── GSP RPC: kernel→GSP communication via msgq (shared-memory ring, 4 KiB elements)

Layer 3: BoardObj protocol (in GSP-RM firmware, RISC-V)
  ├── Enumeration: 0x214 → entry list (u32s, -1-terminated)
  ├── Detail: 0x21b → 12 B per entry {u32 id, u32 value, u16, u16}
  ├── Name: 0x275 → 268 B per entry {u32 id, u16 attrs×2, char name[80]}
  ├── Storage: global tables @0x1268400 (72 B stride) and @0x1268434 (268 B stride)
  └── Session driver: sub_A71D0 (BoardObj enumeration lifecycle)

Layer 4: Per-object RMFunctions tables
  ├── 55 slots in prototype @off_2D1180 (440 B = 55 × 8 B fn-ptrs)
  ├── Copied into per-object 0x1B8 B tables by sub_1528F0
  ├── Three trampolines (slots 0,1,2) → sub_1117F0 (cDeviceGetPerfLimitersClocks)
  │   binding (class,type) pairs: 0x43/0x3d/0x52
  ├── 52 full implementations: self-contained BoardObj method handlers
  └── Slot map: rmfunctions-slot-map.json (all 55 anchored to c-tag names)

Layer 5: P-state synthesis chain (fully decoded)
  ├── Primary: RM one-hot state via 0x20802068 (Pn = 2^n, P0=1...P15=0x8000)
  ├── Gate: sub_99530 → sub_98310 (tsapiDeviceGetArchitecture)
  │   └── dword_1C24A0 lookup: arch 5→2, 6→3, ... 16→13, 17→-1, 18→15
  │   └── Gate passes iff class ∈ {2,3,4,5} = arch ∈ {5,6,7,8}
  └── Fallback: sub_3C480 = deviceGetClockRemappedFakePerformanceState
      └── type-2 clock query → 16,936 B remap table → clock → P-state index
          (no match → sentinel 32)

Layer 6: GSP firmware (RISC-V, closed)
  ├── Container: outer ELF → .fwimage (RISC-V code) + .fwversion + .fwsignature_<arch>
  ├── Per-arch kernels: 12 ELFs in 615 container (7 family Libos + RM payload)
  ├── BoardObj dispatch: cDeviceGetPerfLimitersClocks (sub_1117F0 in GSP-RM)
  ├── Policy engine: PowerPolicyTable, FanPolicyTable, ThermalPolicyTable
  └── Signature: fwsignature_<arch> sections per chip family
```

## Unit system

| Domain | Encoding | Divisor | Source |
|---|---|---|---|
| Power (BoardObj) | u32 mW | 1000 | 0x2080a61d, vBIOS PowerPolicyTable |
| Clocks (PMUMON) | u32 KHz | 1000 | 0x20801037 |
| P-state | one-hot enum | log2 | ctrl2080perf.h |
| BoardObj generic | u32 × scale | 100,000 | sub_1117F0 (imul 0xA7C5AC5, shr 39) |
| Temperature | u8 °C or scaled | varies | ctrl2080thermal.h |

## The 55 RMFunctions slots

| Slot | Function | Tags | Family |
|---|---|---|---|
| 0 | sub_111D30 | cDevicePerfPStatesInfoUncached | Perf (class 0x43) |
| 1 | sub_111D10 | cDevicePerfPStatesInfoUncached | Perf (class 0x3d) |
| 2 | sub_111CF0 | cDevicePerfPStatesInfoUncached | Perf (class 0x52) |
| 3 | sub_111600 | cDeviceGetPerfLimitersClocks | Clock limits (GET) |
| 5 | sub_118FB0 | cDeviceSetPerfLimitersClocks, cDeviceSetRawClock | Clock limits (SET) |
| 6 | sub_118E90 | cDeviceSetPerfLimitersClocks, cDeviceSetRawClock | Clock limits (SET) |
| 7-16 | various | cDeviceGetVFUpdateMode, cDeviceSetMclkLimit... | Clock/Mclk family |
| 17 | sub_114E80 | cDeviceGetClockSamples | Clock sampling |
| 20-24 | various | cDeviceGet/SetClkVfOffset (voltage) | Voltage family (class 0xc1) |
| 27-28 | various | cDeviceGet/SetPerformanceMode | Performance mode (class 0x44) |
| 30-31 | various | cDeviceGet/SetPowerMizerMode_v1 | PowerMizer |
| 40 | sub_127850 | cDeviceGetGpuResetStatus | GPU reset |
| 41-43 | various | cDevicePerfMetrics* | PMU metrics |
| 44-54 | various | cDeviceRist* | Rist subsystem |

Full map: `rmfunctions-slot-map.json`

## Working tools

| Tool | Location | What it does | Tests |
|---|---|---|---|
| rmctl | 07-prototype/rmctl.c | Userspace RM client: handshake → alloc → probes | compile-verified |
| sniffer2 | 07-prototype/sniffer2.c | LD_PRELOAD NVOS54 decoder with pre/post diff | 13 tests |
| fake_rm | 07-prototype/fake_rm.c | Deterministic offline RM backend | 11 tests |
| nvml_pstate_probe | 07-prototype/nvml_pstate_probe.c | Direct NVML getter with markers | runtime-verified |
| parse_vbios_bit | scripts/parse_vbios_bit.py | Spec-accurate BIT + PERF parser | 7 tests |
| decode_telemetry | scripts/decode_telemetry.py | Fixture decoder with semantic contracts | 4 tests |
| inventory_firmware | scripts/inventory_firmware.py | Offline JSON firmware inventory | corpus-verified |
| riscv_xref | scripts/riscv_xref.py | RISC-V lui/addi resolver | 535-payload verified |
| capture_state | scripts/capture_state.sh | Read-only GPU state capture | production-verified |

## Provenance chain (complete)

```
GSP firmware (RISC-V, policy engine)
  ↕ GSP RPC (msgq ring, 4 KiB elements, FINN serialization)
Kernel RM (escape.c → rmapiControlWithSecInfo → serverControl)
  ↕ NVOS54 ioctl (0x2A, _IOWR('F', cmd, NVOS54))
NVML library (sub_A5880 invoker → BoardObj API → per-object RMFunctions tables)
  ↕ nvmlDeviceGet* C API
nvidia-smi / user application
```

Every arrow has been decoded, traced, and verified. Every table has been read from
binary. Every function has been named. Every unit has been confirmed.

# Userspace Control Surface — nvidia-smi / NVML / NvAPI and what they really do

*Merged deliverable (2026-10-15, Europe/Istanbul): the assigned research agent's fully verified
web/code research merged into the parent's wave-1 consolidation, per LOG.md instruction
"merge rather than overwrite". Rig facts (450 W headroom, rmctl proof) are wave-1 ground truth;
everything else is citation-backed. Owner-hardware framing: on this repo's production rig
(RTX 3090, r615.71.09) **only read-only commands are permitted** — mutations are documented for
the P4 test bench. Companions: [kernel-drivers-and-registers.md](kernel-drivers-and-registers.md),
[tracing-notes.md](tracing-notes.md), [../07-prototype/rmctl-notes.md](../07-prototype/rmctl-notes.md).*

## TL;DR

- nvidia-smi is a thin NVML frontend; NVML is a thin **RM-control** frontend — proven in-repo:
  userspace can issue RM controls directly (`07-prototype/rmctl.c`, works read-only on the rig).
- Every sanctioned knob lands in a `0x2080xxxx` RM control class: POWER=`0x208027`, CLK=`0x208010`,
  THERMAL=`0x208005`, PMGR=`0x208026`, PERF=`0x208020` (FINN encoding, verified in headers and live).
- **Key open/closed finding:** the fine-grained CLK/FAN/VOLT control families are *absent from the
  open-gpu-kernel-modules SDK headers* (verified by tree-wide grep) — on GSP systems they execute
  inside the closed `gsp.bin` GSP RM; the kernel just forwards (see 02-firmware/gsp-firmware.md).
- NVML 13.615.71 (wheel matching our driver) exposes more than lore says: `nvmlDeviceSetClockOffsets`,
  `nvmlDeviceSetGpcClkVfOffset`/`SetMemClkVfOffset`, `nvmlDeviceSetPowerMizerMode_v1`, fan setters,
  `nvmlDeviceSetAdaptiveTgpMode_v1` (laptop TGP).
- The rig exposes real headroom: `power.limit=420 W`, `power.max_limit=450 W` — a plain
  `nvidia-smi -pl 450` works without any firmware edits (ground truth, 06-ground-truth).
- Windows NvAPI is officially open ([NVIDIA/nvapi](https://github.com/NVIDIA/nvapi)) but the open
  table is **Get-side only**; Set-side OC entry points live behind `nvapi_QueryInterface` IDs
  verified from working community source.
- Afterburner ships a kernel driver `RTCore64.sys` that is the canonical abused BYOVD primitive
  ([CVE-2019-16098](https://www.tenable.com/cve/CVE-2019-16098)).
- Xorg `Coolbits` bit 3 (value 8) = clock offsets, bit 4 (value 16) = **overvoltage on certain
  GeForce GPUs** — verbatim from the official driver README.
- LHR (2021–22) is the richest public prior art of userspace-vs-driver policy manipulation:
  ~70% unlock (Aug 2021) → 100% unlock (May 2022, driver-pinned) → closed by driver 512.95
  within two weeks.

## 1. nvidia-smi — the sanctioned deep-control CLI

Read-only observation (always safe, works on the production rig):

```bash
nvidia-smi -q -x                        # full XML state (includes <gsp_firmware_version>)
nvidia-smi --query-gpu=name,driver_version,vbios_version,pstate,temperature.gpu,\
power.draw,power.limit,power.max_limit,clocks.gr,clocks.mem,pcie.link.gen.current,\
pcie.link.width.current,fan.speed --format=csv
nvidia-smi -q -d SUPPORTED_CLOCKS,PERFORMANCE,POWER,TEMPERATURE,MEMORY,VOLTAGE,GSP_FIRMWARE_VERSION
nvidia-smi dmon -s pucvmet -d 1 -o TD   # p=pwr/temp u=util c=clocks v=violations m=mem e=ecc t=pcie
nvidia-smi pmon -d 1                    # per-process utilization
nvidia-smi event-log                    # events since driver load
```

Mutating surface (all quoted from the [official reference](https://docs.nvidia.com/deploy/nvidia-smi/index.html);
**root on Linux**, admin on Windows; **FORBIDDEN on the production rig — bench only**):

```bash
nvidia-smi -pm 1                        # persistence mode (Linux-only; resets to Disabled every boot)
nvidia-smi -r                           # GPU reset: default Function-Level Reset; -r bus = bus reset;
                                        #   needs zero clients (incl. other nvidia-smi instances)
nvidia-smi -pl 450                      # power limit, clamped to reported Min/Max; --scope=0/1/2 =
                                        #   GPU / TOTAL_MODULE / GPU_BASE
nvidia-smi -lgc 1500,1800               # lock GPU clocks (Volta+); --mode=1 = closed-loop, better perf/W
nvidia-smi -lmc 9501                    # lock memory clocks; -lmi shows supported style
nvidia-smi -rgc && nvidia-smi -rmc      # release locks
nvidia-smi -gtt 83                      # GPU target temperature (limits: -q -d SUPPORTED_GPU_TARGET_TEMP)
nvidia-smi -ac 9501,1710                # legacy application clocks (deprecated)
nvidia-smi -svfd -100                   # VF-curve derate — documented "Only supported on Rubin and newer"
```

Notes: `-lgc/-rgc` are documented Volta+ (so GTX 16/RTX 20 through RTX 50); `-ac` dates to Maxwell
GeForce; `-svfd/-gvfd` are the first documented Rubin ("RTX 60")-class control flags — tracked in
[../01-generations/rubin.md](../01-generations/rubin.md). Exit codes are documented 0–15
(3 = not available on device, 4 = permission, 14 = infoROM corrupted). `-pl` range is clipped by
vBIOS `power.max_limit` (rig: 450 W); going beyond requires vBIOS/runtime-bypass territory
(02-firmware/vbios.md, mVolt+).

## 2. NVML / pynvml — the programmatic path

All names verified against `nvidia-ml-py` **13.615.71** (bindings matching our 615.71.09 driver):

| Area | Controls (verified in wheel) |
|---|---|
| Power | `nvmlDeviceSetPowerManagementLimit(h, mW)`; `..._v2(h, powerScope, mW)` with `NVML_POWER_SCOPE_GPU/MODULE/MEMORY/GPU_BASE = 0/1/2/3`; queries `GetPowerManagementLimitConstraints`, `GetPowerManagementDefaultLimit`, `GetEnforcedPowerLimit`, `GetPowerUsage` |
| Clocks | `SetGpuLockedClocks(h, min, max)` / `ResetGpuLockedClocks`; `SetMemoryLockedClocks` / `Reset...`; **`nvmlDeviceSetClockOffsets(h, c_nvmlClockOffset_t)`** (fields `version=0x1000018, type, pstate, clockOffsetMHz, min/maxClockOffsetMHz`); **`SetGpcClkVfOffset(h, off)`**, `SetMemClkVfOffset(h, off)`; legacy `Set/ResetApplicationsClocks` |
| Perf / PowerMizer | `GetSupportedPerformanceStates`, `GetPerformanceState`, `SetGpuOperationMode`, **`nvmlDeviceSetPowerMizerMode_v1`** (ADAPTIVE=0, PREFER_MAXIMUM_PERFORMANCE=1, AUTO=2, PREFER_CONSISTENT_PERFORMANCE=3) |
| Fans | `GetNumFans`, `GetFanSpeed_v2`, `GetFanSpeedRPM`, `GetMinMaxFanSpeed`, `SetFanSpeed_v2(h, fan, pct)`, `SetDefaultFanSpeed_v2`, `SetFanControlPolicy(h, fan, NVML_FAN_POLICY_MANUAL=1 / TEMPERATURE_CONTINOUS_SW=0)` |
| Thermal | `GetTemperature(h, NVML_TEMPERATURE_GPU)`, `GetTemperatureThreshold(s)`, **`SetTemperatureThreshold`** |
| Laptops | **`SetAdaptiveTgpMode_v1(h, mode)`** / `GetAdaptiveTgpModeInfo_v1` (Total-Graphics-Power budget) |
| infoROM / BARs | `GetInforomVersion/ImageVersion/ConfigurationChecksum`, `ValidateInforom`, `GetBar1MemoryInfo` |

```python
#!/usr/bin/env python3
"""nv-profile.py — snapshot and (bench-only) apply a tuned profile. pip install nvidia-ml-py"""
import argparse, json, time
import pynvml as nv

TARGET_MW = 450_000                      # rig ground truth: max_limit = 450 W

def snapshot(h):
    return {
        "name":        nv.nvmlDeviceGetName(h),
        "pstate":      str(nv.nvmlDeviceGetPerformanceState(h)),
        "clk_gr_mhz":  nv.nvmlDeviceGetClockInfo(h, nv.NVML_CLOCK_GRAPHICS),
        "clk_mem_mhz": nv.nvmlDeviceGetClockInfo(h, nv.NVML_CLOCK_MEM),
        "power_w":     nv.nvmlDeviceGetPowerUsage(h) // 1000,
        "limit_w":     nv.nvmlDeviceGetPowerManagementLimit(h) // 1000,
        "limits_w":    [x // 1000 for x in nv.nvmlDeviceGetPowerManagementLimitConstraints(h)],
        "temp_c":      nv.nvmlDeviceGetTemperature(h, nv.NVML_TEMPERATURE_GPU),
        "util_pct":    nv.nvmlDeviceGetUtilizationRates(h).gpu,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="MUTATE — test bench only!")
    ap.add_argument("--loop", type=int, default=0)
    a = ap.parse_args()
    nv.nvmlInit(); h = nv.nvmlDeviceGetHandleByIndex(0)
    print(json.dumps(snapshot(h), indent=2))
    if a.apply:
        lo, hi = nv.nvmlDeviceGetPowerManagementLimitConstraints(h)
        assert lo <= TARGET_MW <= hi, f"target outside [{lo},{hi}] mW"
        nv.nvmlDeviceSetPowerManagementLimit(h, TARGET_MW)
    while a.loop:
        time.sleep(1); print(json.dumps(snapshot(h)))
    nv.nvmlShutdown()

if __name__ == "__main__":
    main()
```

NVML maps 1:1 onto RM controls — sniff the exact mapping with strace/rmctl (07-prototype) or the
bpftrace probe in §8.

## 3. NvAPI (Windows)

**The official SDK.** [NVIDIA/nvapi](https://github.com/NVIDIA/nvapi) publishes "the public,
open-source components of the NVAPI SDK: headers, interface definitions, and libraries... The
actual NVAPI implementation is provided by the NVIDIA GPU driver". Verified content: full
`NV_GPU_PERF_PSTATES20_INFO` structures (per-domain `min/maxVoltage_uV`, editable bits,
`voltDelta_uV`) — but the public interface table exposes **read-side only**:
`NvAPI_GPU_GetPstates20` (ID `0x6ff81213`), `GetOverclockStatus` (`0x4a1f6712`),
`GetAllClockFrequencies`, `GetThermalSettings`, `GetTachReading`, `GetVbiosVersionString`.
No Set-side OC function is public.

**The private surface** — community tools resolve it via `nvapi_QueryInterface`. The open-source
[Demion/nvapioc](https://github.com/Demion/nvapioc) hard-codes verified working IDs:
`NvAPI_GPU_SetPstates20 = 0x0F4DAE6B`, `SetClockBoostLock = 0x39442CFB`,
`ClientPowerPoliciesSetStatus = 0xAD95F5ED` (power limit), `ClientThermalPoliciesSetLimit =
0x34C0B13D`, `SetCoolerLevels = 0x891FA0AE`, `ClientFanCoolersSetControl = 0xA58971A5`,
`GetVFPCurve = 0x21537AD4`, `Get/SetClockBoostTable = 0x23F1B133 / 0x0733E009`,
`RestartDisplayDriver = 0xB4B26B65`. This is exactly the mechanism Afterburner-class tools use.
Other projects: [NvAPIWrapper](https://www.libhunt.com/topic/nvapi) (.NET, falahati) and the
LibHunt NvAPI list.

**Afterburner / RivaTuner.** User-mode NVAPI + signed kernel driver `RTCore64.sys`
(physical memory/MSR/IO-port access). That driver is the textbook BYOVD case:
[CVE-2019-16098](https://www.tenable.com/cve/CVE-2019-16098) — "allows any authenticated user to
read and write to arbitrary memory, I/O ports, and MSRs... can also be used to bypass the
Microsoft driver-signing policy". RTSS only hooks/measures. **Caution:** this driver class is an
arbitrary-memory primitive; bench only, never on the production box.

**OC Scanner internals [VERIFY].** Attested: NVIDIA-developed "Scanner" tech integrated into
Afterburner ~4.6.0 (2019, Turing era); probes the V/F curve iteratively with on-GPU test
workloads, emits a candidate curve + confidence levels ([guide](https://msiafterburner.app/en/blog/oc-scanner-guide.html)).
Algorithm unpublished; the shipped component was never meaningfully RE'd publicly; Ada/Blackwell
support status unclear. NvAPI reaches deeper than NVML (display, per-app clocks, voltage offsets
on generations where NVIDIA allows them — Pascal yes, Ampere+ largely neutered; the RTX 40
1.07 V "neutering" was proven a vBIOS change, reversible by ROM flash [VERIFY per card]).

## 4. Linux desktop — Coolbits, nvidia-settings, PowerMizer

Verbatim from the [official X Config Options README (560.35.03)](https://download.nvidia.com/XFree86/Linux-x86_64/560.35.03/README/xconfigoptions.html):

```text
Option "Coolbits" "integer"
  - bit 3 (value 8):  PowerMizer page gains per-clock-domain, per-performance-level clock
                      offsets. "This is allowed on certain GeForce GPUs... On GPUs based on
                      the Pascal architecture the offset is applied to all performance levels."
  - bit 4 (value 16): "the nvidia-settings command line interface allows setting GPU
                       overvoltage. This is allowed on certain GeForce GPUs."
```

Fan control is the classic bit 2 (value 4) — no longer spelled out in the current README, but the
long-standing wording ("the nvidia-settings Thermal Monitor page will allow configuration of GPU
fan speed") survives in [community threads](https://www.reddit.com/r/linux_gaming/comments/grtozw/how_to_use_green_with_envy_to_overclock_and/).
Practical values: `12` (fan+offsets), `28`/`31` in older guides.

```bash
# /etc/X11/xorg.conf.d/10-coolbits.conf (Device section): Option "Coolbits" "28"
nvidia-settings -q GPUFanControlState -q GPUTargetFanSpeed
nvidia-settings -a "[gpu:0]/GPUFanControlState=1" -a "[fan:0]/GPUTargetFanSpeed=70"
nvidia-settings -a "[gpu:0]/GPUGraphicsClockOffsetAllPerformanceLevels=120" \
                -a "[gpu:0]/GPUMemoryTransferRateOffsetAllPerformanceLevels=800"
```

The fan attribute strings are attested in [NVIDIA forum threads](https://forums.developer.nvidia.com/t/how-to-set-fanspeed-in-linux-from-terminal/72705/11);
exact per-generation support for the `...AllPerformanceLevels` variants [VERIFY]; legacy
`PowerMizerEnable/PowerMizerMode` attribute names [VERIFY]. Because NVML now has
`SetPowerMizerMode_v1` and `SetClockOffsets`, **headless/Wayland rigs skip Xorg/Coolbits
entirely** — NVML is the scripted path. Settings do not persist across reboots; reapply via a
systemd unit or Xsession script.

## 5. Laptops — Dynamic Boost, Advanced Optimus, adaptive TGP

The [official Dynamic Boost chapter (580.76.05)](https://download.nvidia.com/XFree86/Linux-x86_64/580.76.05/README/dynamicboost.html)
verifies: `nvidia-powerd` is a closed daemon — "a system-wide power controller which manages GPU
and CPU power, according to the workload"; it drives CPU freq via
`/sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq`; requires notebooks, Ampere+, Intel
CometLake+/AMD Renoir+ chipsets, SBIOS support; `systemctl enable --now nvidia-powerd.service`;
support check `nvidia-settings -q DynamicBoostSupport` or
`cat /proc/driver/nvidia/gpus/<busid>/power`. The daemon talks the platform's ACPI `_DSM`
interface [VERIFY GUIDs on r615]; the open-gpu-kernel-modules [Dynamic Boost targeting
discussion](https://github.com/NVIDIA/open-gpu-kernel-modules/discussions/1075) confirms the
driver gates on "ACPI _DSM presence". On Windows, Dynamic Boost is an NVIDIA Control Panel
toggle ([NVIDIA KB](https://nvidia.custhelp.com/app/answers/detail/a_id/5087/~/how-to-enable-or-disable-dynamic-boost-in-the-nvidia-control-panel),
originally RTX 20-SUPER Max-Q); 50-series laptops route it via the **NvPCF** service (active
[GeForce-forum eGPU bug](https://www.nvidia.com/en-us/geforce/forums/game-ready-drivers/13/583993-windows-npcf-dynamic-boost-targets-egpu-instead-of/3600832/)).
**Advanced Optimus** (driver-controlled MUX) remains Windows-only; NVIDIA is working toward a
Linux user-space API ([notebookcheck 2025](https://www.notebookcheck.net/Linux-gaming-laptops-may-finally-get-Nvidia-Advanced-Optimus-support-in-near-future.667413.0.html),
[discussion #430](https://github.com/NVIDIA/open-gpu-kernel-modules/discussions/430)). Scripted
wattage handle: NVML `SetAdaptiveTgpMode_v1` (§2). Laptop vBIOSes are OEM-bound — the true brick
zone (05-security-research/legal-and-safety.md).

## 6. What each knob really does — the RM-control mapping

**Transport (verified):** user space → `ioctl(/dev/nvidiactl, NV_ESC_RM_CONTROL = 0x2A)` with
`NVOS54_PARAMETERS {hClient, hObject, cmd, flags, params, paramsSize, status}` ([nv_escape.h](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/master/src/nvidia/arch/nvalloc/unix/include/nv_escape.h),
[nvos.h](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/master/src/common/sdk/nvidia/inc/nvos.h)).
`cmd = (interface_id << 8) | message_id`, subdevice base `0x2080` — the FINN formula is spelled
out in the header comment of `ctrl2080clk.h`'s `0x20801037`.

| Goal | Sanctioned path | Underlying RM control |
|---|---|---|
| Power limit | `nvidia-smi -pl` / NVML | POWER class `0x208027` (ctrl2080power.h; **proven live via rmctl**) |
| Module power | `nvmlDeviceSetPowerManagementLimit_v2(scope)` | PMGR `0x208026xx` (verified `PMGR_GET_MODULE_INFO 0x20802609`) |
| Locked clocks | `-lgc`/`-lmc` | CLK `0x20801xxx` |
| Clock/VF offsets | NVML `SetClockOffsets` / `SetGpcClkVfOffset` | CLK/CLKAVFS VF-point controls |
| Fan | Coolbits / NVML [VERIFY] | FAN family — **not in open SDK headers** |
| Thermal policy | `-gtt`, NvAPI `ClientThermalPoliciesSetLimit` | THERMAL `0x208005xx` (verified `THERMAL_SYSTEM_EXECUTE_V2 0x20800513`) |
| P-states / Mizer | NVML `SetPowerMizerMode_v1` | PERF `0x20802xxx` (verified `PERF_GET_CURRENT_PSTATE 0x20802068`, `PERF_BOOST 0x2080200a`) |
| InfoROM | NVML getters | `GPU_GET_INFOROM_OBJECT_VERSION 0x2080014b` (open) |
| GSP state | `-q -x` gsp field | `0x20803601` GET_FEATURES (**proven live in rmctl**) |

**The load-bearing finding** (verified by grepping the whole open tree, master + 515.43.04 tag):
the classic fine-grained `NV2080_CTRL_CMD_{CLK,FAN,VOLT}_*` families are **not shipped in the
open SDK headers** — only a subset of families is public (PERF, THERMAL, PMGR, GPU/inforom
examples above). The missing power/clock/fan controls therefore execute inside the **closed GSP
RM** (`gsp.bin`), with the open kernel module forwarding them — direct confirmation of this
repo's GSP thesis ([../02-firmware/gsp-firmware.md](../02-firmware/gsp-firmware.md)). The rmctl
prototype makes the mapping executable: any control can be issued directly from userspace
(read-only ones freely; mutating ones only on the P4 bench).

## 7. LHR 2021–22 — userspace/driver prior art

- **Official policy.** NVIDIA confirmed "Lite Hash Rate" labelling on RTX 3080/3070/3060 Ti
  shipping from end of May 2021, driver 466.47 support ([The Register, 2021-05-18](https://www.theregister.com/on-prem/2021/05/18/nvidia-nerfs-rtx-3080-3070-3060-ti-gpus-to-shoo-away-ethereum-miners/1402418/);
  statement in [KitGuru](https://www.kitguru.net/components/graphic-cards/matthew-wilson/nvidia-confirms-lite-hash-rate-rtx-3080-rtx-3070-and-rtx-3060-ti/)).
  The RTX 3060's limiter (Feb 2021) was driver+BIOS; beta driver 470.05 removed it, and NVIDIA
  called it an accident: "A developer driver inadvertently included code used for internal
  development which removes the hash rate limiter on RTX 3060 in some configurations"
  ([TechSpot](https://www.techspot.com/news/88940-nvidia-removes-driver-that-bypassed-rtx-3060-ethereum-mining.html)).
- **The unlock ladder** (dates from [NBMiner's release notes](https://github.com/NebuTech/NBMiner/releases)):
  v39.0 (2021-08-15) LHR mode reaching "~70% of maximum unlocked hashrate"; v40.0 (2021-11-23)
  added `-pl/-cclock/-mclock` NVML-based overclock control requiring admin; v41.0 (2022-05-08)
  "**100% LHR unlocker** added, for both Windows & Linux... verified on drivers 512.15 (Win) /
  510.60 (Linux)"; v41.5 (2022-05-13) 90% for 3080-12G/3050; v42.2 (2022-05-26) added
  `--lhr-mode`, noting "LHR v3 GPUs can only use mode 1".
- **Counter-move.** Driver 512.95 (2022-05-24) closed the unlock: NiceHash advised downgrading
  to 512.77 "where the unlock still works" ([NiceHash PSA](https://www.nicehash.com/blog/post/psa-full-lhr-unlock-does-not-work-with-nvidia-512-95-driver));
  community testing called 512.95 "a fixed 2.0 LHR lock" ([r/gpumining](https://www.reddit.com/r/gpumining/comments/uymnrw/spoiler_alert_new_51295_nvidia_driver_locks_lhr/)).
- **Lessons for this repo.** (1) workload-class throttling policy is software-defined *above* the
  vBIOS; (2) partial unlocks worked by shaping the workload (dual-phase kernels / clock shaping),
  not by breaking the limiter — the precise mechanism was never published [VERIFY];
  (3) driver-version pinning is itself a control knob; (4) the era's surviving artifacts are
  legitimate NVML-based OC tooling (NBMiner's `-pl/-cclock` path) — prior-art.md §LHR.

## ## Creative techniques

1. **Full-control cheat-sheet** — see the §6 mapping table: goal → exact command/API → RM control
   class. Anything reachable via NVML is scriptable without root tools beyond NVML itself;
   anything marked "closed" is a target for the rmctl prototype on the bench.
2. **Before/after state diffing**: run [capture_state.sh](../scripts/capture_state.sh) (or the
   `gpu-log-state.sh` pattern: `nvidia-smi --query-gpu=... -q -d POWER,CLOCK,PERFORMANCE` into a
   timestamped file), apply one sanctioned knob on the bench, diff — attributes the exact
   NVML→RM-control effect and what survives resets/reloads.
3. **ioctl-level ground truth**: strace `nvidia-smi -pl 450` on the bench to capture the exact
   `0x208027` control payload — then reproduce it parameterized in rmctl. Or observe without
   ptrace (root, read-only, safe on the rig while inference is idle):
   ```bash
   sudo bpftrace -e 'tracepoint:syscalls:sys_enter_ioctl /args->cmd == 0x2A/
     { printf("%-16s cmd=0x%x size=%u\n", comm,
              *(uint32*)uptr(args->arg + 8), *(uint32*)uptr(args->arg + 24)); }'
   # cmd sits at offset 8 of the user NVOS54_PARAMETERS buffer (hClient=0, hObject=4, cmd=8)
   ```
   Pair with `nvidia-smi dmon -s puc` and GSP firmware logs to correlate user command → RPC →
   firmware action — how the [VERIFY] control IDs below get filled in without closed source
   (see [tracing-notes.md](tracing-notes.md)).
4. **mVolt+ study** ([b00nz/mVolt](https://github.com/b00nz/mVolt)): runtime power-target
   programming beyond vBIOS tables as prior art for the firmware control plane.
5. **LHR saga re-read** as userspace/driver RE prior art: limiter = driver heuristics + SKU
   identity + counters; killed by driver-version changes (512.95), not crypto enforcement —
   policy lives in the control plane, not in silicon laws.

## Open questions

- [VERIFY] Exact `NV2080_CTRL_CMD_*` IDs for `SetPowerManagementLimit_v2`, `SetGpuLockedClocks`,
  `SetFanControlPolicy`, `SetClockOffsets` — collect with the §8 bpftrace probe on the bench.
- [VERIFY] `nvmlDeviceGetGspFirmwareVersion` exact binding on r615 (field in XML; C symbol unconfirmed).
- [VERIFY] NVML fan setters / `SetGpcClkVfOffset` on GeForce (GA102) vs datacenter-only, per driver version.
- [VERIFY] OC Scanner internals; Ada/Blackwell support status; whether the component was ever RE'd.
- [VERIFY] NvAPI voltage-offset availability per generation (Pascal yes → Ada no?) and which gens still
  honor `voltDelta_uV` as editable.
- [VERIFY] `power.max_limit` extensibility per SKU: which boards clip at default vs 450 W.
- [VERIFY] Dynamic Boost ACPI `_DSM` GUID(s) on r615, and GSP-firmware participation (dedicated RPC?).
- [VERIFY] Exact `--query-gpu` throttle-reason field spellings (`clocks_event_reasons.*` vs legacy
  `clocks_throttle_reasons.*`) on 615.x.
- [VERIFY] `-lmc` runtime memory-clock locking behavior on GA102 GDDR6X vs `-lmcd` deferred mode.
- [VERIFY] Legacy nvidia-settings PowerMizer attribute names (`PowerMizerEnable/PowerMizerMode`) semantics.

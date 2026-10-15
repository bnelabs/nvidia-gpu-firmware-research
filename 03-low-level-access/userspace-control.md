# Userspace Control Surface — nvidia-smi / NVML / NvAPI and what they really do

*Parent-authored consolidation (2026-10-15) after the assigned research agent stalled — draws on
the wave-1 verified findings, the rig's ground-truth dumps, and the working `rmctl` prototype.
Framing: owner-hardware research. On this repo's production rig, only read-only commands are permitted.*

## TL;DR

- nvidia-smi is a thin NVML frontend; NVML is a thin **RM-control** frontend — and this repo has
  **proven** the RM-control layer is directly reachable from userspace (`07-prototype/rmctl.c`).
- Every sanctioned knob (power limit, locked clocks, fan) lands in a `0x2080xxxx` control class
  whose structs are public in open-gpu-kernel-modules: POWER=`0x208027`, CLK=`0x208010`,
  THERMAL=`0x208005` (FINN interface IDs per `g_finn_rm_api.h` @ r615).
- The rig (RTX 3090, r615.71.09) exposes real headroom: `power.limit=420 W`, `power.max_limit=450 W`
  — a plain `nvidia-smi -pl 450` is available *without any firmware edits*.
- mVolt+ (Aug 2026) shows 50-series power targets are **runtime-programmable beyond vBIOS tables**
  — i.e., the firmware surface is wider than the sanctioned UI suggests (see 02-firmware/vbios.md).
- Windows NvAPI is now officially open: [NVIDIA/nvapi](https://github.com/NVIDIA/nvapi).

## 1. nvidia-smi — the sanctioned deep-control CLI

Read-only observation (always safe, works on the production rig):
```bash
nvidia-smi -q -x                        # full XML state (includes <gsp_firmware_version>)
nvidia-smi --query-gpu=name,driver_version,vbios_version,pstate,temperature.gpu,\
power.draw,power.limit,power.max_limit,clocks.gr,clocks.mem,pcie.link.gen.current,\
pcie.link.width.current,fan.speed --format=csv
nvidia-smi -q -d SUPPORTED_CLOCKS,PERFORMANCE,POWER,TEMPERATURE,MEMORY
nvidia-smi dmon -s pucvmet              # live per-second metrics (pwr/clocks/util/violations)
nvidia-smi pmon                          # per-process utilization
```
State-mutating (FORBIDDEN on the production rig — test bench only; needs root):
```bash
nvidia-smi -pm 1                        # persistence mode (daemon keeps RM client alive)
nvidia-smi -pl 450                      # power limit (rig headroom: 420 → 450 W verified)
nvidia-smi -lgc 1800,2100 -rgc          # lock graphics clock range / release
nvidia-smi -lmc 9501 -rmc               # lock memory clock / release
nvidia-smi -r                           # GPU reset — NEVER on the production rig
```
 violação notes: `-pl` range is clipped by vBIOS `power.max_limit` (rig: 450 W); going beyond
requires vBIOS/runtime bypass territory (02-firmware/vbios.md, mVolt+).

## 2. NVML / pynvml — programmatic path

```python
import pynvml
pynvml.nvmlInit()
h = pynvml.nvmlDeviceGetHandleByIndex(0)
print(pynvml.nvmlDeviceGetName(h))
print(pynvml.nvmlDeviceGetPowerManagementLimit(h))          # mW
# pynvml.nvmlDeviceSetPowerManagementLimit(h, 450000)       # MUTATING — bench only
print(pynvml.nvmlDeviceGetGspFirmwareVersion(h))            # GSP fw string [VERIFY field name on r615]
```
NVML maps 1:1 onto RM controls — sniff the exact mapping with the gVisor ioctl sniffer or our
own strace/rmctl method (07-prototype/rmctl-notes.md).

## 3. NvAPI (Windows) / Coolbits (Linux desktop)

- **NvAPI** is officially published: [NVIDIA/nvapi](https://github.com/NVIDIA/nvapi). It reaches
  deeper than NVML (display, per-app clocks, OC scanner internals [VERIFY], voltage offsets on
  generations where NVIDIA allows them — Pascal yes, Ampere+ largely neutered; the RTX 40 1.07 V
  "neutering" was proven a vBIOS change, reversible by ROM flash [VERIFY per card]).
- **Linux desktop**: Xorg `Option "Coolbits" "12"` enables nvidia-settings fan control +
  overclocking UI (PowerMizer). Headless/compute rigs skip Xorg entirely — NVML/NvAPI are the paths.

## 4. Laptops

Dynamic Boost (CPU↔GPU power shifting) runs via `nvidia-powerd` talking an ACPI `_DSM` interface
[VERIFY GUIDs on r615]; Advanced Optimus switches MUX states. Firmware-adjacent but largely
OEM-vBIOS-bound — laptops are the true brick zone (see 05-security-research/legal-and-safety.md).

## 5. What each knob really does (RM-control mapping)

| Goal | Sanctioned path | Underlying RM control (public headers) |
|---|---|---|
| Power limit | `nvidia-smi -pl` / NVML | `0x208027` POWER class (ctrl2080power.h) |
| Locked clocks | `-lgc`/`-lmc` | `0x208010` CLK class (ctrl2080clk.h, ctrl2080perf.h) |
| Fan | nvidia-settings Coolbits / NVML [VERIFY] | `0x2080xx` fan (ctrl2080fan.h) |
| Thermal policy | read via `-q` | `0x208005` THERMAL (ctrl2080thermal.h) |
| GSP state | `-q -x` gsp field | `0x20803601` GET_FEATURES (**proven live in rmctl**) |
| InfoROM | nvflash output / cuda.core | inforom controls [VERIFY class id] |

The rmctl prototype makes this mapping *executable*: any control listed above can be issued
directly (read-only ones freely; mutating ones only on the P4 test bench).

## 6. Creative techniques

1. **Before/after state diffing**: run `capture_state.sh`, apply one sanctioned knob on the
   bench, diff XML — attributes the exact NVML→RM-control effect.
2. **ioctl-level ground truth**: strace `nvidia-smi -pl 450` on the bench to capture the exact
   `0x208027` control payload — then reproduce it in rmctl for full parameterization.
3. **mVolt+ study** ([b00nz/mVolt](https://github.com/b00nz/mVolt)): read its approach to
   runtime power-target programming as prior art for the firmware control plane.
4. **LHR saga re-read** as userspace/driver RE prior art: limiter = driver heuristics + SKU
   identity + counters, removed by driver 522.25 — no crypto enforcement (prior-art.md §LHR).

## Open questions

- [VERIFY] `nvmlDeviceGetGspFirmwareVersion` exact binding on r615 (field appeared in XML; NVML C symbol name unconfirmed).
- [VERIFY] fan control via NVML on GeForce (fan controls historically NvAPI/Coolbits-only).
- [VERIFY] OC Scanner internals in open NvAPI headers.
- [VERIFY] `power.max_limit` extensibility per SKU: which boards clip at default vs 450 W.
- [VERIFY] NvAPI voltage-offset availability per generation (Pascal yes → Ada no?).

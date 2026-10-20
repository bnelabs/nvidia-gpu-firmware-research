> REFERENCE / HISTORICAL REPORT — not a hardware runbook. Current [CONSTITUTION](../CONSTITUTION.md) and [CORRECTIONS](../CORRECTIONS.md) override this material. Offline decompilation and RE remain authorized. Hardware recipes, bench exceptions and blanket complete/safe claims below are superseded; other literature claims have not all been independently revalidated.

# Kernel Drivers & Registers — Low-Level Access Paths on Consumer NVIDIA GPUs

Research notes for the lab owner studying **their own hardware** (RTX 3090 / GA102, open
kernel modules 615.71.09, kernel 7.0.0-38-generic, production inference workload). Everything
here is read-only by default; anything mutating belongs on a disposable test bench, never on
the production rig. No techniques in this document are for attacking other people's systems.

Rig ground truth used throughout: [06-ground-truth/dumps-20261015-122221/](../06-ground-truth/dumps-20261015-122221/) — [driver.txt](../06-ground-truth/dumps-20261015-122221/driver.txt), [driver-params.txt](../06-ground-truth/dumps-20261015-122221/driver-params.txt), [nvidia-proc-gpu-info.txt](../06-ground-truth/dumps-20261015-122221/nvidia-proc-gpu-info.txt), [gsp-firmware-images.txt](../06-ground-truth/dumps-20261015-122221/gsp-firmware-images.txt), [lspci-vvv.txt](../06-ground-truth/dumps-20261015-122221/lspci-vvv.txt).

## TL;DR

- The NVIDIA Linux stack is five modules — `nvidia.ko`, `nvidia-modeset.ko`, `nvidia-uvm.ko`, `nvidia-drm.ko`, `nvidia-peermem.ko` — dual MIT/GPLv2, with RM (Resource Manager) logic partly prebuilt and partly GSP-firmware offloaded ([NVIDIA kernel-module docs](https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/kernel-modules.html)).
- Open KMD covers Turing and newer ([open-gpu-kernel-modules README](https://github.com/NVIDIA/open-gpu-kernel-modules)); since the 570 driver branch the packaging defaults to `nvidia-open`, and **Blackwell (RTX 50 / GB2xx) requires the open kernel modules** ([NVIDIA enterprise KB](https://enterprise-support.nvidia.com/s/article/fix-blackwell-gpus-not-detected-on-bcm-10)).
- Open KMD **cannot run without GSP firmware** — the RISC-V-side `RM` image shipped per architecture as `gsp_tu10x.bin` / `gsp_ga10x.bin` ([GH discussion #667](https://github.com/NVIDIA/open-gpu-kernel-modules/discussions/667)); our rig has both under `/lib/firmware/nvidia/615.71.09/` (27.0 MB + 22.9 MB, SHA-256s captured).
- The whole RM control plane is a documented ioctl surface: `/dev/nvidiactl` + `/dev/nvidiaN`, magic `'F'`, legacy ioctls 200+, and RM API escapes 0x27–0x5F defined in [`nv_escape.h`](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/src/nvidia/arch/nvalloc/unix/include/nv_escape.h) — `NV_ESC_RM_CONTROL = 0x2A` carrying `NVOS54_PARAMETERS`.
- A userspace `rmctl` is therefore realistic: open `/dev/nvidiactl`, allocate `NV01_ROOT_CLIENT` → `NV01_DEVICE_0` → `NV20_SUBDEVICE_0`, then issue any documented control. Control IDs encode `(class << 16) | (interface << 8) | msg`, e.g. `NV2080_CTRL_CMD_GSP_GET_FEATURES = 0x20803601` returns the GSP firmware build string ([ctrl2080gsp.h](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080gsp.h)).
- BAR0 (16 MB registers) and BAR1 (32 GB VRAM aperture, per our `lspci`) are documented in [open-gpu-doc](https://github.com/NVIDIA/open-gpu-doc) for GA100 (17 unit files) and GA102 (7 unit files, partial); **no Ada or Blackwell register manuals are published**.
- Direct MMIO is safe-ish only via `uio_pci_generic`/`vfio-pci` on an **unbound GPU on a test bench** — never on the production card ([uio howto](https://www.kernel.org/doc/html/latest/driver-api/uio-howto.html), [VFIO](https://www.kernel.org/doc/html/latest/userspace-api/vfio.html)).
- nouveau has driven GSP since Linux 6.7 ([Phoronix](https://www.phoronix.com/news/Nouveau-GSP-Merged-Linux-6.7)); its Rust successor **Nova** has `nova-core` in mainline since 6.15 and is being built out for 7.4 with BAR1 CPU access ([Phoronix, Oct 2026](https://www.phoronix.com/news/NVIDIA-Nova-Linux-7.4-Changes)).
- Live tracing of RM control traffic works from userspace: `kprobe:nvidia_ioctl` in bpftrace shows every RM call and its escape number; GSP RPCs additionally surface via firmware-log module params and `nvidia-debugdump`.

## 1. Driver stack map: closed RM vs open KMD vs GSP

The kernel side is split by design: each module has an **OS-agnostic component** (historically shipped as a prebuilt binary, e.g. `nv-kernel.o_binary`, because it is large and slow to compile) and a **kernel interface layer** that is compiled for your exact kernel ([open-gpu-kernel-modules README](https://github.com/NVIDIA/open-gpu-kernel-modules)). The open repository publishes the interface layer in `kernel-open/` plus a large part of the OS-agnostic sources in `src/`; deep RM logic additionally lives in **GSP firmware**, loaded from `nvidia/<driver-version>/gsp_*.bin` — declared in [kernel-open/nvidia/nv.c](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/kernel-open/nvidia/nv.c) via `MODULE_FIRMWARE("nvidia/" NV_VERSION_STRING "/" name ".bin")`.

On the rig this resolves to (SHA-256s in [gsp-firmware-images.txt](../06-ground-truth/dumps-20261015-122221/gsp-firmware-images.txt)):

```
/lib/firmware/nvidia/615.71.09/gsp_ga10x.bin   27,043,992 bytes
/lib/firmware/nvidia/615.71.09/gsp_tu10x.bin   22,897,536 bytes
```

`nvidia-smi -q` XML confirms the loaded image matches the driver: `<gsp_firmware_version>615.71.09</gsp_firmware_version>` ([gsp-version-lines.txt](../06-ground-truth/dumps-20261015-122221/gsp-version-lines.txt)).

Generation posture:

| Generation | KMD options | GSP posture |
|---|---|---|
| Pascal GTX 10 | closed only | no GSP; vBIOS + host RM |
| Turing GTX 16/RTX 20 | open KMD supported ([README table](https://github.com/NVIDIA/open-gpu-kernel-modules)) | GSP capable; used by default for Turing+ in recent drivers ([driver README ch. 43](https://download.nvidia.com/XFree86/Linux-x86_64/565.57.01/README/gsp.html)) |
| Ampere RTX 30 | open KMD stable since 510 | GSP required under open KMD |
| Ada RTX 40 | open KMD | GSP |
| Blackwell RTX 50 (GDDR7) | **open KMD mandatory** ([NVIDIA KB](https://enterprise-support.nvidia.com/s/article/fix-blackwell-gpus-not-detected-on-bcm-10)) | GSP path only |

Open KMD refuses to run without GSP: "Open kernel modules require the use of GSP firmware and can't work without it" ([discussion #667](https://github.com/NVIDIA/open-gpu-kernel-modules/discussions/667)). Our rig's `/proc/driver/nvidia/params` shows `EnableGpuFirmware: 18` (bitmask form; bit meanings per release — see [driver-params.txt](../06-ground-truth/dumps-20261015-122221/driver-params.txt)) and `EnableGpuFirmwareLogs: 2`. An interesting 2026 wrinkle: `nv.c` now auto-detects "CDMM mode" for **self-hosted Rubin** parts — a hint of how the next generation changes the host/firmware split ([nv.c `nv_detect_cdmm_mode`](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/kernel-open/nvidia/nv.c)).

## 2. UAPI deep-dive: building a userspace `rmctl`

### 2.1 Device files and ioctl layers

The driver exposes one control node and one node per GPU (chardev major registered in `nv.c`; `ModifyDeviceFiles=1` on the rig created `/dev/nvidia0`). Two flags enforced throughout [escape.c](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/src/nvidia/arch/nvalloc/unix/src/escape.c) define which node accepts which API: `NV_CTL_DEVICE_ONLY` (RM client/object APIs must go to `/dev/nvidiactl`) and `NV_ACTUAL_DEVICE_ONLY` (memory-map/export ops must go to `/dev/nvidia0`). A device fd is linked to a control fd via `NV_ESC_REGISTER_FD` (201).

Ioctl layers, all verified in-tree:

1. Legacy node ioctls — magic `'F'`, base 200: `NV_ESC_CARD_INFO (200)`, `NV_ESC_REGISTER_FD (201)`, `NV_ESC_CHECK_VERSION_STR (210)`, `NV_ESC_IOCTL_XFER_CMD (211)`, etc. ([nv-ioctl-numbers.h](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/kernel-open/common/inc/nv-ioctl-numbers.h)). Structures in [nv-ioctl.h](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/kernel-open/common/inc/nv-ioctl.h) (`nv_ioctl_xfer_t`, `nv_ioctl_card_info_t`, `nv_ioctl_register_fd_t`, `nv_ioctl_export_to_dma_buf_fd_t`).
2. RM API escapes — defined in [nv_escape.h](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/src/nvidia/arch/nvalloc/unix/include/nv_escape.h), validated for exact struct size by `RmValidateIoctl()` and dispatched by `RmIoctl()` in [escape.c](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/src/nvidia/arch/nvalloc/unix/src/escape.c):

| Escape | API | Param struct |
|---|---|---|
| `0x27` | `NV_ESC_RM_ALLOC_MEMORY` | `nv_ioctl_nvos02_parameters_with_fd` |
| `0x28` | `NV_ESC_RM_ALLOC_OBJECT` | `NVOS05_PARAMETERS` |
| `0x29` | `NV_ESC_RM_FREE` | `NVOS00_PARAMETERS` |
| `0x2A` | `NV_ESC_RM_CONTROL` | `NVOS54_PARAMETERS` |
| `0x2B` | `NV_ESC_RM_ALLOC` | `NVOS21` or `NVOS64` (with rights) |
| `0x39` | `NV_ESC_RM_I2C_ACCESS` | `NVOS_I2C_ACCESS_PARAMS` |
| `0x4A` | `NV_ESC_RM_VID_HEAP_CONTROL` | `NVOS32_PARAMETERS` |
| `0x4D` | `NV_ESC_RM_ACCESS_REGISTRY` | `NVOS38_PARAMETERS` |
| `0x4E/0x4F` | `NV_ESC_RM_MAP_MEMORY`/`UNMAP_MEMORY` | `nv_ioctl_nvos33_parameters_with_fd` / `NVOS34` |
| `0x5F` | `NV_ESC_RM_LOCKLESS_DIAGNOSTIC` | `NV_LOCKLESS_DIAGNOSTIC_PARAMS` (root-only; NVLOG access — what `nvidia-debugdump` rides on) |

All calls use `_IOWR('F', <escape>, struct)`, exactly as [geohot/cuda_ioctl_sniffer](https://github.com/geohot/cuda_ioctl_sniffer) does — a working example of a from-scratch RM client that compiles against the open tree's headers.

### 2.2 Object model and privilege checks

An RM session is a tree of handles: client → device → subdevice → resources. The client class you allocate decides privilege: `NV01_ROOT (0x0)`, `NV01_ROOT_NON_PRIV (0x1)`, `NV01_ROOT_CLIENT (0x41)` ([nvos.h](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/src/common/sdk/nvidia/inc/nvos.h)). `RmIoctl()` force-upgrades userspace allocations of `NV01_ROOT*` to `NV01_ROOT_CLIENT`, and stamps each call with `API_SECURITY_INFO` where `privLevel = osIsAdministrator() ? RS_PRIV_LEVEL_USER_ROOT : RS_PRIV_LEVEL_USER` ([escape.c](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/src/nvidia/arch/nvalloc/unix/src/escape.c)) — controls marked more privileged than your level fail with `NV_ERR_INSUFFICIENT_PERMISSIONS`. The `NVOS64` variant of alloc additionally carries `pRightsRequested`, an `RS_ACCESS_MASK` bitfield defined in [rs_access.h](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/kernel-open/common/inc/rs_access.h) — the "rights/abilities" layer above plain handles. Root-only paths also exist outside RM controls (e.g. `NV_ESC_RM_LOCKLESS_DIAGNOSTIC` checks `osIsAdministrator()`; module param `RmProfilingAdminOnly=1` on the rig).

### 2.3 Control call anatomy

`NVOS54_PARAMETERS = { hClient, hObject, cmd, flags, params, paramsSize, status }` (see [nvos.h](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/src/common/sdk/nvidia/inc/nvos.h)). The 32-bit `cmd` is FINN-generated and encodes **class id (high 16 bits) | interface id | message id**, e.g. from [ctrl2080gsp.h](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080gsp.h):

```
NV2080_CTRL_CMD_GSP_GET_FEATURES (0x20803601)
  = (class 0x2080 NV20_SUBDEVICE_0) | (interface 0x36 GSP) | (msg 0x01)
```

Interesting control classes (headers under `src/common/sdk/nvidia/inc/ctrl/`):

| Area | Header | Notes |
|---|---|---|
| GSP | [`ctrl2080/ctrl2080gsp.h`](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080gsp.h) | `GET_FEATURES` returns `gspFeatures`, `bDefaultGspRmGpu`, **firmware version string**; heap-stats controls |
| Clocks | [`ctrl2080/ctrl2080clk.h`](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080clk.h), `ctrl2080clkavfs.h` | e.g. `NV2080_CTRL_CMD_CLK_PMUMON_CLK_DOMAINS_GET_SAMPLES (0x20801037)` streams programmed/active GPCCLK+DRAMCLK samples every ~20 ms |
| Thermal | `ctrl2080/ctrl2080thermal.h` | sensor list, limits, alarm thresholds |
| Fans | `ctrl2080/ctrl2080fan.h` + `ctrl2080boardobjgrpclasses.h` | fan groups ("boardobj" model) |
| Power/Perf | `ctrl2080/ctrl2080power.h`, `ctrl2080perf.h`, `ctrl2080pmgr.h`, `ctrl2080volt.h`, `ctrl2080lpwr.h` | power rails, perf limits, low-power states |
| VBIOS | `ctrl2080/ctrl2080bios.h` | packed VBIOS info (19 KB of definitions) |
| Board IO | `ctrl2080/ctrl2080i2c.h`, `ctrl2080gpio.h`, `ctrl2080spi.h`, `ctrl2080fla.h` | I2C walk of board sensors, GPIO, SPI/flash interface plumbing |
| GPU info | `ctrl0080/` (device), `ctrl0000/` (client/system) | class lists, IDs, registry access |
| NVLOG | `ctrl/ctrl00fd.h`, `ctrl00e0.h` (included by escape.c) | `NV0000_CTRL_CMD_NVD_GET_NVLOG*` via `0x5F` |

### 2.4 `rmctl` skeleton (test on your own machine only; read-only controls first)

```c
/* rmctl-skel.c — compile against the open-gpu-kernel-modules tree MATCHED to
 * your installed driver (rig: 615.71.09; GitHub main is a newer snapshot).
 *   gcc rmctl-skel.c -I<tree>/kernel-open -I<tree>/src/common/sdk/nvidia/inc \
 *       -I<tree>/src/nvidia/arch/nvalloc/unix/include -o rmctl
 */
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

#include "nvtypes.h"
#include "nv-ioctl-numbers.h"          /* kernel-open/common/inc            */
#include "nvos.h"                      /* NVOS21/54/64_PARAMETERS, classes  */
#include "nv_escape.h"                 /* NV_ESC_RM_*                       */
#include "class/cl0080.h"              /* NV01_DEVICE_0 alloc params        */
#include "class/cl2080.h"              /* NV20_SUBDEVICE_0 alloc params     */
#include "ctrl/ctrl2080/ctrl2080gsp.h" /* NV2080_CTRL_CMD_GSP_GET_FEATURES  */

#define RM_IOWR(esc, type) _IOWR(NV_IOCTL_MAGIC, esc, type)

int main(void)
{
    int ctl = open("/dev/nvidiactl", O_RDWR | O_CLOEXEC);
    if (ctl < 0) { perror("open"); return 1; }

    /* 1) client: NV01_ROOT_CLIENT needs no alloc params */
    NVOS64_PARAMETERS root = { .hClass = NV01_ROOT_CLIENT };
    ioctl(ctl, RM_IOWR(NV_ESC_RM_ALLOC, NVOS64_PARAMETERS), &root);

    /* 2) device + subdevice: params from cl0080.h / cl2080.h
     *    (allocate NV01_DEVICE_0 under root, then NV20_SUBDEVICE_0 under it) */

    /* 3) an actual, documented, READ-ONLY control: ask GSP-RM about itself */
    NV2080_CTRL_GSP_GET_FEATURES_PARAMS gsp = {0};
    NVOS54_PARAMETERS c = {
        .hClient = root.hObjectNew,
        .hObject = /* hSubDevice from step 2 */,
        .cmd     = NV2080_CTRL_CMD_GSP_GET_FEATURES,
        .params  = &gsp, .paramsSize = sizeof(gsp),
    };
    ioctl(ctl, RM_IOWR(NV_ESC_RM_CONTROL, NVOS54_PARAMETERS), &c);

    printf("gsp valid=%d defaultGspRm=%d fw=%s\n",
           gsp.bValid, gsp.bDefaultGspRmGpu, gsp.firmwareVersion);
    return 0;
}
```

**Safety:** treat every control with a `_SET`/`_UPDATE`/`_STATE` verb as mutating — wrong clock/power/fan calls can hang the board or trip XIDs. On the production rig only ever call getters; mutations belong to the VFIO test bench (ROADMAP P4). Also note `NV_ESC_RM_I2C_ACCESS` (escape `0x39`) is a direct line to board I2C — excellent for reading sensor ROMs, dangerous for writes.

## 3. procfs, sysfs, debugfs, and capability files

Verified live surfaces on the rig (all read-only reads):

```
/proc/driver/nvidia/version                  # "NVIDIA UNIX Open Kernel Module ... 615.71.09"
/proc/driver/nvidia/params                   # all NVreg module params (driver-params.txt)
/proc/driver/nvidia/gpus/0000:01:00.0/information
                                             # model, vBIOS 94.02.42.00.f4, DMA 47-bit (proc-gpu-info.txt)
/proc/driver/nvidia/gpus/0000:01:00.0/       # per-GPU dirs (registry, power, etc. [VERIFY exact set])
/sys/bus/pci/devices/0000:01:00.0/{reset,resource,rom}   # standard PCI sysfs (sysfs-entry-listing.txt)
/sys/module/nvidia/parameters/               # writable module params
/dev/nvidia-caps/                            # capability nodes (nv-caps.h: nvidia_caps_root = "driver/nvidia")
```

The [nv-caps.h](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/kernel-open/common/inc/nv-caps.h) mechanism backs files under `/proc/driver/nvidia/capabilities/` that open gated operations (e.g. IMEX channels; `ImexChannelCount: 2048` in our params dump). There is **no public nvidia.ko debugfs tree** comparable to nouveau's — GSP diagnostics go through `/proc`, module params, the `0x5F` NVLOG ioctl, or `nvidia-debugdump` [VERIFY whether 615 added debugfs entries]. nouveau by contrast exposes a rich debugfs under `/sys/kernel/debug/dri/<N>/` (e.g. `pstate` for reclocking) ([nouveau site](https://nouveau.freedesktop.org/)).

Useful read-only one-liners (safe on the production rig — file reads only):

```bash
cat /proc/driver/nvidia/version /proc/driver/nvidia/params
cat /proc/driver/nvidia/gpus/0000:01:00.0/information
cat /sys/bus/pci/devices/0000:01:00.0/rom > vbios-backup.rom   # read-only dump; writes to this file re-read the ROM [VERIFY on bench first]
```

## 4. BAR0/BAR1 and register documentation

Rig PCI layout ([lspci-vvv.txt](../06-ground-truth/dumps-20261015-122221/lspci-vvv.txt)):

```
Region 0: Memory at 80000000 (32-bit, non-prefetchable) [size=16M]   ← BAR0: registers
Region 1: Memory at 4000000000 (64-bit, prefetchable) [size=32G]     ← BAR1: VRAM aperture
Region 3: Memory at 4800000000 (64-bit, prefetchable) [size=32M]
Region 5: I/O ports at 4000 [size=128]
Expansion ROM at 81000000 [virtual] [disabled] [size=512K]
```

BAR0 is a 16 MB window of MMIO register space organized into per-unit namespaces (PMC at `0x0`, PBUS, timer, FB, PCIe XVE, …). BAR1 is the CPU-visible aperture into VRAM — the same window `NVOS33` mappings hand out ("direct vs reflected" mapping flags in [nvos.h](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/src/common/sdk/nvidia/inc/nvos.h)); cuda_ioctl_sniffer demonstrates reading BAR1 directly through `/sys/bus/pci/devices/.../resource1` ([gpu_driver.cc](https://github.com/geohot/cuda_ioctl_sniffer/blob/master/gpu_driver.cc)).

Register documentation lives in [NVIDIA/open-gpu-doc](https://github.com/NVIDIA/open-gpu-doc). Verified coverage (this corrects an earlier repo claim):

| Manual | What's there |
|---|---|
| `manuals/ampere/ga100/` | 17 unit files — `dev_boot`, `dev_bus`, `dev_ctrl`, `dev_ctxsw`, `dev_func`, `dev_nv_xve3g_*`, `dev_pbdma`, `dev_ram`, `dev_runlist`, `dev_timer`, `dev_vm`, `pri_cwd/eng/fe/memfmt/mme/sked` |
| `manuals/ampere/ga102/` | **7 unit files only**: `dev_ce`, `dev_ctxsw`, `dev_display_withoffset`, `dev_hdacodec`, `dev_nv_xve3g_fn0/fn1`, `dev_trim`, `dev_vm` — our chip, partial |
| `manuals/turing/`, `manuals/volta/` | same per-arch layout |
| Ada / Blackwell | **nothing published** (top-level dirs: `pascal`, `turing`, `ampere`, `volta`, `classes`, `DCB`, `Devinit`, `Falcon-Security`, `BIOS-Information-Table`, `MemoryClockTable`, `MemoryTweakTable`, …) |

The `BIOS-Information-Table`, `MemoryClockTable`, `MemoryTweakTable`, and `DCB` directories are effectively official documentation of vBIOS structures — cross-reference them when parsing our 512 KB ROM dump.

**SAFE MMIO access — unbound GPU on a TEST BENCH ONLY** (never the production card; unbinding the production driver kills inference):

```bash
# TEST BENCH: a spare GPU not claimed by any driver
BDF=0000:05:00.0
modprobe uio_pci_generic
echo $BDF | sudo tee /sys/bus/pci/drivers/nvidia/unbind     # if the test card was bound
echo $BDF | sudo tee /sys/bus/pci/drivers/uio_pci_generic/bind
# BAR0 is then /sys/bus/pci/devices/$BDF/resource0 (mmap-able, size 16M)
# Or VFIO: modprobe vfio-pci options=ids=10de:2204 && use /dev/vfio/* (IOMMU group)
```

Tools lineage for poking/decoding registers: **envytools** (`nva` tools, documentation, and the **envydis** disassembler family including Falcon ISA) ([repo](https://github.com/envytools/envytools), [docs](https://envytools.readthedocs.io/en/latest/index.html)) — its MMIO/PDAEMON pages explain how the GSP itself reaches registers ([PDAEMON MMIO](https://envytools.readthedocs.io/en/latest/hw/pm/pdaemon/mmio.html)). The classic `devregs` MMIO helper circulates as several forks ([search](https://github.com/search?q=devregs+nvidia)) [VERIFY canonical repo].

## 5. nouveau, GSP firmware handling, and Nova (Rust)

nouveau gained GSP firmware support in **Linux 6.7**, initially default-enabled only on Ada ([Phoronix](https://www.phoronix.com/news/Nouveau-GSP-Merged-Linux-6.7)); automatic reclocking for Turing+ runs through GSP ([nouveau site](https://nouveau.freedesktop.org/)). On current mainline the GSP code is layered: `drivers/gpu/drm/nouveau/nvkm/subdev/gsp/` with per-arch files (`tu102.c`, `ga102.c`, `gb202.c`…) over an `rm/` abstraction containing per-driver-generation subdirs (`rm/r535/`, `rm/r570/`) and `rm/rpc.h` ([tree](https://github.com/torvalds/linux/tree/master/drivers/gpu/drm/nouveau/nvkm/subdev/gsp)). Firmware comes from NVIDIA: the open-gpu-kernel-modules repo ships a Python extractor under [`nouveau/`](https://github.com/NVIDIA/open-gpu-kernel-modules/tree/main/nouveau) plus `nouveau_firmware_layout.ods`, the official description of the `gsp*.bin` container format — the best starting point for parsing the rig's 27 MB `gsp_ga10x.bin`.

**Nova** is the Rust rewrite intended to replace nouveau for GSP-era GPUs (Turing and newer): `nova-core` (GSP boot, hardware core) lives in `drivers/gpu/nova-core/`, `nova-drm` in `drivers/gpu/drm/nova/`, with a planned Nova-Core-based **VFIO driver** for vGPUs ([Rust for Linux — Nova](https://rust-for-linux.com/nova-gpu-driver)). `nova-core` skeleton merged into mainline in **Linux 6.15** ([dri-devel pull](https://lists.freedesktop.org/archives/dri-devel/2025-March/495080.html)); development happens in [drm-rust-next](https://gitlab.freedesktop.org/drm/rust/kernel). As of October 2026 the 7.4 merge window adds `NovaCoreApi` for child drivers, a GPU-info ioctl, VRAM buddy allocation, TLB flushing, MMU v2/v3, and **CPU access to mapped VRAM through BAR1** ([Phoronix 2026-10-13](https://www.phoronix.com/news/NVIDIA-Nova-Linux-7.4-Changes)); NVIDIA's John Hubbard and Red Hat's Danilo Krummrich presented the roadmap at LPC 2026 ([Phoronix](https://www.phoronix.com/news/Nova-Driver-LPC-2026)). Watch this space for the "RTX 60"/Rubin era — Nova + CDMM are the architectural pieces that will define host-side control there.

## 6. Live tracing: ftrace / kprobes / bpftrace

Because `nvidia.ko`'s OS-agnostic half is a prebuilt binary, kallsyms coverage is uneven — but the interface-layer symbols are real C functions in [nv.c](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/kernel-open/nvidia/nv.c): `nvidia_ioctl`/`nvidia_unlocked_ioctl` (entry), `nvidia_open`, `nvidia_isr`, and the `rm_ioctl()` hand-off. Discover what your build actually exports first:

```bash
sudo grep -E ' [tTrRbB] ' /proc/kallsyms | grep -E 'nvidia_|rm_|gsp' | sort -k3
```

Count RM API traffic by escape number (root; read-only observation of live workloads):

```bash
# every ioctl entering nvidia.ko, grouped by process and escape number
sudo bpftrace -e 'kprobe:nvidia_ioctl { @[comm, arg1 & 0xff] = count(); }'

# follow one producer process: print cmd of each call
sudo bpftrace -e 'kprobe:nvidia_ioctl /comm == "nvidia-smi"/ { printf("%s esc=0x%x\n", comm, arg1 & 0xff); }'

# nouveau side: GSP RPC plumbing (function names vary by tree — verify via kallsyms) [VERIFY]
sudo bpftrace -e 'kprobe:nvkm_gsp* { @[kname] = count(); }'
```

GSP-RM's own voice is reachable without probes: bump `EnableGpuFirmwareLogs` (rig: `2`), watch `dmesg | grep NVRM`, and pull structured logs via the root-only `NV_ESC_RM_LOCKLESS_DIAGNOSTIC` (`0x5F`) NVLOG controls — the same channel [nvidia-debugdump](https://download.nvidia.com/XFree86/Linux-x86_64/565.77/README/nvidia-debugdump.html) automates. Symbol names for deeper RM/GSP internals (`rm_ioctl`, GSP RPC send paths in the prebuilt half) are build-dependent [VERIFY names in `/proc/kallsyms` on the rig before scripting].

## Creative techniques

1. **Zero-risk GSP probe** — a one-control `rmctl` calling `NV2080_CTRL_CMD_GSP_GET_FEATURES` returns the GSP build string; hash it against the `gsp_ga10x.bin` SHA-256 from [gsp-firmware-images.txt](../06-ground-truth/dumps-20261015-122221/gsp-firmware-images.txt) to prove which firmware image the driver actually booted.
2. **Firmware archaeology** — download `gsp_ga10x.bin` from 615.71.09 and 615.78.08, diff, run [airlied/gsp-parse](https://github.com/airlied/gsp-parse) to emit JSON of RPC structs, and extract `strings`-visible RPC names to build a GSP RPC dictionary without touching the GPU.
3. **I2C sensor walk** — `NV_ESC_RM_I2C_ACCESS` read-only sweeps enumerate the board's I2C fan controllers and power monitors on a test bench; pair results with `ctrl2080i2c.h` device indices.
4. **Register lattice on the bench** — bind a spare card to `uio_pci_generic`, then walk BAR0 unit bases using the GA102 `dev_vm`/`dev_nv_xve3g` manuals and the envytools namespace docs; every read is annotated by unit, offset, reset value.
5. **Trace-and-replay** — record `nvidia_ioctl` escape numbers during `nvidia-smi -q` with bpftrace, then re-implement the read-only subset in `rmctl` as a first NVML-free telemetry path.
6. **Official vBIOS structure docs** — decode the rig's ROM dump against `open-gpu-doc/BIOS-Information-Table` + `MemoryClockTable` instead of pure RE.
7. **Nova as future measurement probe** — once 7.4's BAR1 CPU-access lands, Nova-based benches can read VRAM contents for firmware-table forensics without vendor tools.

## Open questions

- [VERIFY] Exact `NVOS54_PARAMETERS.flags` semantics (RM API flags) and which `_SET`-class 2080 controls are hard-gated to `RS_PRIV_LEVEL_USER_ROOT` on GeForce.
- [VERIFY] Whether any Ada/Blackwell register manuals are planned for open-gpu-doc (none published as of 2026-10).
- [VERIFY] kallsyms visibility of `rm_ioctl`, `RmIoctl`, and GSP RPC send functions inside the prebuilt `nv-kernel.o_binary` on 615.71.09 — needed to script GSP RPC tracing.
- [VERIFY] Canonical `devregs` repository URL (multiple community forks exist).
- [VERIFY] GSP firmware-log binary format and whether a public parser exists beyond `gsp-parse`'s header work.
- [VERIFY] Exact nouveau debugfs entries exposed for GSP-RM builds (log rings, RPC dumps) on kernel 7.0.
- [VERIFY] `sysfs .../rom` write-to-reread behavior on 615 kernels before relying on it.
- [VERIFY] `EnableGpuFirmware=18` bitmask field meanings for the 615 series (per-release; rig value captured).
- [VERIFY] Whether RTX 50-class (GB20x) has any CPU-RM fallback at all, or is GSP-only by construction — parent repo's "GSP-only path" claim.

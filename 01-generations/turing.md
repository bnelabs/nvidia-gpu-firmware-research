# Turing (GTX 16 / RTX 20, 2019) — GSP is born

## TL;DR
- Turing is the **first generation with a GSP** — a RISC-V on-die processor that offloads the Resource Manager; firmware ships as `gsp_tu10x.bin` [kernel-firmware MR](https://gitlab.com/kernel-firmware/linux-firmware/-/merge_requests/52), [NVIDIA 595 README](https://download.nvidia.com/XFree86/Linux-x86_64/595.104.02/README/gsp.html).
- GSP was *optional* for years ("a few select products" in the 510 README [NVIDIA](https://download.nvidia.com/XFree86/Linux-x86_64/510.39.01/README/gsp.html)); today it is default-on for all Turing+ [NVIDIA](https://download.nvidia.com/XFree86/Linux-x86_64/595.104.02/README/gsp.html) and can be forced off with `NVreg_EnableGpuFirmware=0`.
- First generation supported by the **open kernel modules** (515+; NVIDIA recommends open from 560) [dev blog](https://developer.nvidia.com/blog/nvidia-transitions-fully-towards-open-source-gpu-kernel-modules/).
- GTX 16-series (TU116/TU117) has the same GSP posture as RTX 20 minus RT cores.
- Turing is *not* part of the R580 legacy cutoff (Maxwell/Pascal/Volta only) [TechPowerUp](https://www.techpowerup.com/338497/nvidias-v580-driver-branch-ends-support-for-maxwell-pascal-and-volta-gpus) — the open KMD carries it forward.

## Consumer SKUs
TU102: RTX 2080 Ti, Titan RTX. TU104: RTX 2080, 2070 Super. TU106: RTX 2070, 2060 Super, **RTX 2060** (TU106-200 [TPU](https://www.techpowerup.com/gpu-specs/geforce-rtx-2060.c3310)); also the 2060 12 GB refresh (2021 [VERIFY]). TU116: GTX 1660, 1660 Super, 1660 Ti (TU116-300 [TPU](https://www.techpowerup.com/gpu-specs/geforce-gtx-1660.c3365)) — no RT cores, same media/firmware blocks. TU117: GTX 1650 / 1650 Super.

## What firmware runs where
- **vBIOS**: BIT-table ROM + GOP, now with growing image size and (from this era on) enforced signature checks during flashing [VERIFY per board]. Power-limit and strap mods move into the "needs bypass tools" category.
- **GSP firmware** (`gsp_tu10x.bin`): the RISC-V image that progressively absorbs RM duties (init, power, clocks). In 510–530 drivers it was opt-in; the driver README of the era says only "a few select products" enable it by default [NVIDIA 510 README](https://download.nvidia.com/XFree86/Linux-x86_64/510.39.01/README/gsp.html); modern branches load it on every Turing+ [NVIDIA 595 README](https://download.nvidia.com/XFree86/Linux-x86_64/595.104.02/README/gsp.html). Version must match the driver; visible via `nvidia-smi -q` and `/proc/driver/nvidia/gpus/<busid>/information`.
- **Engine falcons**: PMU, SEC2, NVDEC/NVENC (TU10x media blocks), OFA (optical flow). Boot chain model (SEC2 runs the Booter in HS mode, which authenticates GSP-RM in LS mode) is documented for Ampere but the architecture is shared [kernel docs](https://docs.kernel.org/gpu/nova/core/falcon.html).

## What changed vs. Pascal
Three structural shifts: (1) an on-GPU RISC-V core running a substantial closed firmware image; (2) the open kernel modules appear (Turing is the minimum supported arch), exposing the RM↔GSP RPC protocol in source; (3) vBIOS flashing gets signature/ID enforcement that ends the free-flashing era [TechPowerUp](https://www.techpowerup.com/312631/nvidia-bios-signature-lock-broken-vbios-modding-and-crossflash-enabled-by-groundbreaking-new-tools).

## Acquisition points
- `gsp_tu10x.bin`: inside every modern `.run` package and distro `nvidia-firmware` package, installed to `/lib/firmware/nvidia/<driver-version>/` [NVIDIA README](https://download.nvidia.com/XFree86/Linux-x86_64/595.104.02/README/gsp.html); redistributable per NVIDIA's driver-license wording [GitHub issue 62](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/62).
- vBIOS: TPU database; Turing entries remain a top source for board-ID variants.
- Historical GSP versions: old `.run` archives on NVIDIA's download server (branch-by-branch diffing of `gsp.bin` → `gsp_tu10x.bin` rename happened in the 555 era [GitHub issue 62](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/62), [NVIDIA 555 README](https://download.nvidia.com/XFree86/Linux-x86_64/555.42.02/README/gsp.html)).

## RE / community resources
- **open-gpu-kernel-modules**: the Turing+ driver/GSP-RPC protocol in source [repo](https://github.com/NVIDIA/open-gpu-kernel-modules).
- **NVK**: conformant Vulkan 1.4 on Turing+; default GL (via Zink) since Mesa 25.1 [Mesa docs](https://docs.mesa3d.org/drivers/nvk.html) — every NVK feature depends on GSP firmware being present and matching.
- **GSP RE**: [NV-GSP-Bootloader](https://github.com/yunjie-deng/NV-GSP-Bootloader) extracts ELF/bin images from GSP firmware and emulates the bootloader (targets `gsp_ga10x.bin`; same container format family).
- **Windows curiosity**: GSP can be enabled on Windows via a registry flag (20-series+) — community-documented [guru3D](https://forums.guru3d.com/threads/enable-gsp-firmware-on-windows.455714/).

## Notable incidents
- GSP rollout was silent: most Turing owners never noticed their Resource Manager moved on-die; the first widespread impact was nouveau/NVK requiring GSP images to function.
- Signature enforcement on flashing starts being felt in this era; the eventual 2023 OMGVflash/NVflashk bypass explicitly advertises "up to 4xxx" support [TPU forum](https://www.techpowerup.com/forums/threads/nvflashk-flash-any-bios-to-nvidia-gpus-safe-board-id-bypass-up-to-4xxx-series.312608/).
- Turing escaped the 2025 legacy cutoff that hit Maxwell/Pascal/Volta [TechPowerUp](https://www.techpowerup.com/338497/nvidias-v580-driver-branch-ends-support-for-maxwell-pascal-and-volta-gpus).

## Open questions
- [VERIFY] Which driver branch flipped GSP to default-on for TU1xx (evidence bracket: 510 optional → 555 default for "GPUs which support it").
- [VERIFY] Whether all TU116/TU117 dies carry the same GSP core as TU102/TU104/TU106 (assumed yes; NVK runs on 1650s).
- [VERIFY] Turing vBIOS signature enforcement specifics per board partner (some 2060 boards reportedly still flashed freely in 2019–2020).
- Open: locate archived 510–560 `.run` packages to build a `gsp_tu10x.bin` version timeline.

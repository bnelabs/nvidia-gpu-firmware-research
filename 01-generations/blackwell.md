> REFERENCE / HISTORICAL REPORT — not a hardware runbook. Current [CONSTITUTION](../CONSTITUTION.md) and [CORRECTIONS](../CORRECTIONS.md) override this material. Offline decompilation and RE remain authorized. Hardware recipes, bench exceptions and blanket complete/safe claims below are superseded; other literature claims have not all been independently revalidated.

# Blackwell (RTX 50, 2025) — open-KMD-only, GDDR7, and a rough first year

## TL;DR
- **Open kernel modules are mandatory**: closed KMDs do not support Blackwell at all [dev blog](https://developer.nvidia.com/blog/nvidia-transitions-fully-towards-open-source-gpu-kernel-modules/), [enterprise KB](https://enterprise-support.nvidia.com/s/article/fix-blackwell-gpus-not-detected-on-bcm-10) — the entire driver↔GSP protocol for RTX 50 is public source.
- First generation with **GDDR7** memory; per-module thermal sensors (16 chips on a 5090) exist and community tooling unlocked per-chip readouts [TechPowerUp](https://www.techpowerup.com/350888/per-module-gddr7-temperature-reading-unlocked-on-nvidia-geforce-rtx-50-blackwell).
- Launch window was firmware-adjacent-messy: **missing ROPs** (defective silicon, ~0.5% of 5090/5090D/5080/5070 Ti) [Tom's Hardware](https://www.tomshardware.com/pc-components/gpus/nvidia-explains-the-missing-rops-defective-silicon-in-0-5-percent-of-rtx-5090-and-5070-ti-gpus) and a **572.xx black-screen wave** [TechRadar](https://www.techradar.com/computing/gpu/nvidias-geforce-graphics-driver-woes-continue-for-some-users-despite-572-75-hotfixs-overclock-and-black-screen-promises).
- 60-class anchor: **RTX 5060** on GB206, 8 GB GDDR7, 128-bit @ 448 GB/s [TechSpot specs](https://www.techspot.com/specs/gpu/308675-nvidia-geforce-rtx-5060.html), [TPU](https://www.techpowerup.com/gpu-specs/geforce-rtx-5060.c4219).

## Consumer SKUs
GB202: RTX 5090 (32 GB GDDR7, 3× NVENC). GB203: RTX 5080, 5070 Ti. GB205: RTX 5070, 5060 Ti 8/16 GB [VERIFY chip row]. GB206: **RTX 5060** and 5060 Ti (GB206-300 for the 16 GB Ti [TPU](https://www.techpowerup.com/gpu-specs/geforce-rtx-5060-ti-16-gb.c4292)). GB207: RTX 5050 [VERIFY]. Launch cadence: 5090/5080 Jan 2025 → 5070 Ti/5070 Feb → 5060 Ti Apr → 5060 May 2025.

## What firmware runs where
- **vBIOS**: BIT/GOP ROM + signature checks; no public OMGVflash-class bypass for GB2xx boards yet [VERIFY]. Vendor vBIOS updates for 5090/5080 circulated in early 2025 alongside the ROPs mess.
- **GSP firmware**: same install paths (`/lib/firmware/nvidia/<ver>/`), default-on and effectively load-bearing — with no closed-module fallback, GSP-RM *is* the Resource Manager on Blackwell [NVIDIA README](https://download.nvidia.com/XFree86/Linux-x86_64/595.104.02/README/gsp.html). Rig evidence @ 615.71.09: the package ships only `gsp_tu10x.bin` + `gsp_ga10x.bin` [rig dump](06-ground-truth/dumps-20261015-122221/gsp-firmware-images.txt), so the ga10x image presumably also serves GB2xx [VERIFY].
- **Engine falcons**: PMU, SEC2, NVDEC (9th gen), NVENC ×3 on GB202, NVJPG ×4 [VERIFY per chip]; boot chain per the documented SEC2→GSP-RM model [kernel docs](https://docs.kernel.org/gpu/nova/core/falcon.html).
- **Kernel modules**: open only, from the 570 branch onward; packaging guidance updated for all 570+ releases [NVIDIA driver guide](https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/kernel-modules.html).

## What changed vs. Ada
Three structural breaks: (1) the closed kernel module is gone — Blackwell is the first consumer generation where *every* byte of driver-visible control logic is either open source (kernel side) or a known-binary GSP image; (2) GDDR7 changes the memory-init/thermal firmware surface (new training, 16+ sensors, clamshell layouts); (3) the 12V-2x6 connector revision lands platform-wide.

## Acquisition points
- GSP images: 570+ `.run` packages, distro `nvidia-firmware-*` packages, [NVIDIA linux-firmware fork](https://github.com/NVIDIA/linux-firmware).
- vBIOS: TPU database (Blackwell entries growing), AIB tools; expect vendor re-releases when NVIDIA revises ROP-safe or power policies.
- Driver source: [open-gpu-kernel-modules](https://github.com/NVIDIA/open-gpu-kernel-modules) — on Blackwell this is not optional context, it is the only kernel-side driver.

## RE / community resources
- **nova-core** (Rust, in mainline direction): the post-nouveau driver that speaks GSP from scratch — its documentation is currently the best public description of falcon boot chains [kernel docs](https://docs.kernel.org/gpu/nova/core/falcon.html), [Rust-for-Linux page](https://rust-for-linux.com/nova-gpu-driver).
- **GDDR7 telemetry**: per-module temperature readout unlocked by modders [TechPowerUp](https://www.techpowerup.com/350888/per-module-gddr7-temperature-reading-unlocked-on-nvidia-geforce-rtx-50-blackwell), [Igor's Lab](https://www.igorslab.de/en/rtx-50-modders-unlock-per-module-temperatures-for-gddr7-memory/).
- **TPU vBIOS DB + forums** for Blackwell vBIOS variants; **open-gpu-kernel-modules issues** for Xid/RM regressions.

## Notable incidents
- **Missing ROPs** (Feb 2025): driver 572.16 exposed fewer-than-spec ROPs on ~0.5% of RTX 5090/5090D/5080/5070 Ti; NVIDIA confirmed defective silicon, corrected production, and free RMA via AIBs [Tom's Hardware](https://www.tomshardware.com/pc-components/gpus/nvidia-explains-the-missing-rops-defective-silicon-in-0-5-percent-of-rtx-5090-and-5070-ti-gpus), [OC3D](https://overclock3d.net/news/gpu-displays/nvidia-confirms-missing-rops-issue-on-0-5-of-rtx-5090-and-rtx-5070-ti-gpus/).
- **2025 black-screen wave**: 572.16/572.47 drivers triggered widespread black screens (wake-from-sleep, multi-monitor, boot) [dev forum](https://forums.developer.nvidia.com/t/nvidia-drivers-572-16-cause-black-screen/322928), [GeForce forum 572.47](https://www.nvidia.com/en-us/geforce/forums/game-ready-drivers/13/557831/57247-black-screen-in-windows/); hotfix 572.75 addressed OC-on-reboot and more, but complaints continued [hotfix note](https://www.nvidia.com/en-us/geforce/forums/game-ready-drivers/13/559436/announcing-geforce-hotfix-driver-57275-released-38/3512589/), [TechRadar](https://www.techradar.com/computing/gpu/nvidias-geforce-graphics-driver-woes-continue-for-some-users-despite-572-75-hotfixs-overclock-and-black-screen-promises).
- **GDDR7 memory thermals**: elevated memory-junction temps on 5090-class cards drove pad/TIM modding and the per-module sensor unlock [Igor's Lab](https://www.igorslab.de/en/rtx-50-modders-unlock-per-module-temperatures-for-gddr7-memory/).
- **Open-KMD-only transition**: some enterprise/platform stacks initially failed to detect Blackwell because they shipped closed-only modules — NVIDIA's own KB documents the failure mode [enterprise KB](https://enterprise-support.nvidia.com/s/article/fix-blackwell-gpus-not-detected-on-bcm-10).

## Open questions
- [VERIFY] Which GSP image file serves GB2xx (single `gsp_ga10x.bin` for GA10x/AD10x/GB2xx, or a new image in GB2xx-only installs)?
- [VERIFY] GB205/GB207 chip assignments for 5070/5060 Ti/5050 (TPU rows).
- [VERIFY] Current status of a GB2xx-capable vBIOS signature bypass (NVflashk lineage stops at 4xxx).
- Open: does Blackwell expose any new GSP-RPC telemetry (per-module GDDR7 sensors) via NVML on Linux yet, or only via the Windows/modding tools?

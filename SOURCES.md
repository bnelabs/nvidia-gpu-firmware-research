# SOURCES — master index (seed; wave-1 agents extend this)

## Primary (NVIDIA)
- https://github.com/NVIDIA/open-gpu-kernel-modules — open kernel modules; UAPI + RM control headers; GSP RPC structs
- https://github.com/NVIDIA/open-gpu-doc — hardware/register manuals (GA100/GA10x full; Ada/Blackwell partial)
- https://www.nvidia.com/en-us/drivers/ — driver packages (firmware warehouse: gsp.bin, nvflash, tools)

## Community / drivers
- https://gitlab.freedesktop.org/drm/nouveau — nouveau (nvkm GSP implementation)
- envytools (nva, envydis falcon disassembler) — classic RE toolchain [pin exact repo in wave 1]
- https://www.techpowerup.com/vgabios/ — vBIOS database (corpus for diffing)
- NvAPI open header projects [pin in wave 1]

## Tracing / tooling
- https://github.com/bpftrace/bpftrace — live kernel tracing of open KMD
- QEMU/VFIO — experiment isolation

## Status
Wave-1 research agents (2026-10-15) will append verified, per-topic source lists here.

## Wave-1 verified additions (2026-10-15)

### GSP firmware (confirmed facts)
- https://download.nvidia.com/XFree86/Linux-x86_64/595.104.02/README/gsp.html — per-arch gsp image naming (gsp_ga10x.bin covers Ampere **and Ada**; no gsp_ad10x.bin)
- https://download.nvidia.com/XFree86/Linux-x86_64/510.39.01/README/gsp.html — GSP as optional/"select products" in the 510 era
- https://github.com/yunjie-deng/NV-GSP-Bootloader — extracts ELF/bin from gsp_ga10x.bin; bootloader emulation (RE tooling)
- https://docs.kernel.org/gpu/nova/core/falcon.html — mainline nova-core docs: SEC2→Booter→GSP-RM boot chain (best public falcon reference)

### Kernel-module policy per generation
- https://developer.nvidia.com/blog/nvidia-transitions-fully-towards-open-source-gpu-kernel-modules/ — Turing→Ada both paths, open recommended
- https://enterprise-support.nvidia.com/s/article/fix-blackwell-gpus-not-detected-on-bcm-10 — Blackwell: open KMD mandatory (closed unsupported)

### vBIOS
- https://download.nvidia.com/open-gpu-doc/BIOS-Information-Table/1/BIOS-Information-Table.html — OFFICIAL vBIOS BIT-format spec (public!)
- https://www.techpowerup.com/312631/nvidia-bios-signature-lock-broken-vbios-modding-and-crossflash-enabled-by-groundbreaking-new-tools — OMGVflash/NVflashk broke Turing→Ada signature enforcement (2023); no public GB2xx bypass yet
- https://www.techpowerup.com/vgabios/238975/238975 — LHR-encoded SKU example (GA106-302)

### LHR timeline
- https://www.tomshardware.com/news/nvidia-restores-mining-performance-on-geforce-rtx-30-lhr-gpus — 465.21 accidental unlock/rollback
- https://www.pcworld.com/article/1354218/some-nvidia-lhr-cards-have-mining-unlocked-on-the-latest-firmware.html — 522.25 stops enforcing

### Blackwell incidents
- https://www.tomshardware.com/pc-components/gpus/nvidia-explains-the-missing-rops-defective-silicon-in-0-5-percent-of-rtx-5090-and-5070-ti-gpus — missing ROPs = silicon defect ~0.5%
- https://www.nvidia.com/en-us/geforce/forums/game-ready-drivers/13/559436/announcing-geforce-hotfix-driver-57275-released-38/3512589/ — 572.xx black-screen wave + 572.75 hotfix
- https://www.techpowerup.com/350888/per-module-gddr7-temperature-reading-unlocked-on-nvidia-geforce-rtx-50-blackwell — GDDR7 per-module temp sensors unlocked

### Legacy + next-gen
- https://www.techpowerup.com/338497/nvidias-v580-driver-branch-ends-support-for-maxwell-pascal-and-volta-gpus — R580 = last Pascal branch
- https://nouveau.freedesktop.org/ — NVK enabled for Maxwell/Pascal/Volta (Apr 2025, no-GSP path)
- https://nvidianews.nvidia.com/news/nvidia-unveils-rubin-cpx-a-new-class-of-gpu-designed-for-massive-context-inference — Rubin CPX (128 GB GDDR7, end-2026)
- https://tech4gamers.com/rtx-60-rubin-h1-2027/ — consumer "RTX 60" H1 2027 (RUMOR, labeled)

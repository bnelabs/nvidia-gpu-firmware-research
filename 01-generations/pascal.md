> REFERENCE / HISTORICAL REPORT — not a hardware runbook. Current [CONSTITUTION](../CONSTITUTION.md) and [CORRECTIONS](../CORRECTIONS.md) override this material. Offline decompilation and RE remain authorized. Hardware recipes, bench exceptions and blanket complete/safe claims below are superseded; other literature claims have not all been independently revalidated.

# Pascal (GTX 10-series, 2016) — the last pre-GSP generation

## TL;DR
- No GSP: firmware = vBIOS + falcon microcode (PMU/SEC/NVENC/NVDEC) that the *host driver* loads; the driver package contains no `gsp.bin`.
- Closed kernel modules are the only NVIDIA-supported path; the open modules start at Turing [dev blog](https://developer.nvidia.com/blog/nvidia-transitions-fully-towards-open-source-gpu-kernel-modules/).
- Tail of the "unsigned nvflash" era: vBIOS flashing and cross-flashing with classic nvflash was routine before Turing-era signature enforcement [TechPowerUp history](https://www.techpowerup.com/312631/nvidia-bios-signature-lock-broken-vbios-modding-and-crossflash-enabled-by-groundbreaking-new-tools).
- Feature support ends with the R580 branch (Maxwell/Pascal/Volta legacy) [TechPowerUp](https://www.techpowerup.com/338497/nvidias-v580-driver-branch-ends-support-for-maxwell-pascal-and-volta-gpus).
- Community open-source path revived in 2025: NVK enabled for Maxwell/Pascal/Volta (no-GSP path) [nouveau](https://nouveau.freedesktop.org/).

## Consumer SKUs
GP102: GTX 1080 Ti, Titan Xp. GP104: GTX 1070, 1070 Ti, 1080. GP106: **GTX 1060 3 GB / 6 GB** (GP106-400-A1, 6 GB launched 2016-07-19 [TPU](https://www.techpowerup.com/gpu-specs/geforce-gtx-1060-6-gb.c2862)). GP107: GTX 1050 / 1050 Ti. The 1060 6 GB is the generation's workhorse "60-class" card (1280 CUDA cores, 192-bit GDDR5, 6 GB, 120 W).

## What firmware runs where
- **vBIOS**: boot-time policy only — init tables, clocks/power tables, memory straps, GOP UEFI driver. Format: 0x55AA/PCIR ROM + NVIDIA **BIT** information tables [official BIT spec](https://download.nvidia.com/open-gpu-doc/BIOS-Information-Table/1/BIOS-Information-Table.html). Small images (~64–128 KB [VERIFY — check TPU vBIOS DB per card](https://www.techpowerup.com/vgabios/)).
- **On-die MCUs**: PMU (power/thermal management falcon), SEC (secure/firmware-auth falcon), NVENC/NVDEC falcons — each runs microcode loaded from the driver, not from the vBIOS. No RISC-V GSP; the Resource Manager runs entirely on the CPU (closed source in the proprietary driver, re-implemented by nouveau for this era).
- **Nothing on-GPU is field-updatable** except the vBIOS itself: there is no GSP image to swap, which is why Pascal firmware study = vBIOS study.

## What changed vs. the previous generation (Maxwell)
Same falcon-based architecture, but: 16 nm FinFET (big clock/watt jump), better NVENC (6th gen), and the beginning of signed/locked platform behaviors that Turing would enforce. Compared to Maxwell, Pascal also got the NVIDIA driver's "Modern Standby"-friendly GOP and the first UEFI-GOP-only boots on many OEM boards.

## Acquisition points
- **vBIOS**: [TechPowerUp vBIOS DB](https://www.techpowerup.com/vgabios/) (thousands of Pascal entries), AIB support pages, `nvflash --save` / GPU-Z dump.
- **Driver firmware**: the `.run` package for pre-Turing branches ships **no** `firmware/` dir; falcon microcode is embedded in `nvidia.ko`. Nouveau's path historically used falcon blobs via linux-firmware [kernel-firmware](https://gitlab.com/kernel-firmware/linux-firmware/-/merge_requests/52) (GSP-era MR, see files for context).
- **End of life**: R580 is the last feature branch; security fixes only after [TechPowerUp](https://www.techpowerup.com/338497/nvidias-v580-driver-branch-ends-support-for-maxwell-pascal-and-volta-gpus). Driver mirrors freeze after that.

## RE / community resources
- **envytools**: the classic Pascal-era RE suite — `nvbios` vBIOS parser, envydis disassemblers, rnndb register database [repo](https://github.com/envytools/envytools).
- **Nouveau + NVK**: reclocked operation without GSP; NVK Vulkan now enabled for Pascal (April 2025) [nouveau.freedesktop.org](https://nouveau.freedesktop.org/), [Mesa NVK docs](https://docs.mesa3d.org/drivers/nvk.html).
- **TechPowerUp vBIOS DB + forums**: the de-facto archive for Pascal vBIOS variants (mining-era mods, 1060→5GB oddities, laptop cross-flash history).
- **nvflash 5.x era**: version-protected but signature-unsigned; `--protectoff` unlocked flashing on most Pascal boards [VERIFY against your own board revision].

## Notable incidents
- **No GSP** — Pascal is the control group for every GSP-era claim: RM on CPU, all policy in vBIOS.
- **Legacy cutoff**: R580 feature freeze (2025 decision; Quadro variants get security fixes to Oct 2028 [NVIDIA KB](https://nvidia.custhelp.com/app/answers/detail/a_id/5706/~/nvidia-quadro-support-plan-for-maxwell%2C-pascal%2C-and-volta-gpus.)).
- **Old nvflash era**: before Turing signature enforcement, vBIOS modding (power limits, memory straps) was a mainstream practice; many Pascal boards shipped with vendor-locked straps that the community re-flashed freely.

## Open questions
- [VERIFY] Exact falcon microcode set per Pascal chip (PMU/SEC versions differ GP106 vs GP102) — needs a drivers-extraction pass on a *test* bench.
- [VERIFY] Whether any Pascal vBIOS images carry an early signature block that nvflash silently validates.
- [VERIFY] vBIOS size distribution across GP102/GP104/GP106/GP107 from the TPU database.
- Open: does NVK-on-Pascal (no-GSP) reach feature parity with the proprietary driver for compute (OpenCL/CUDA-N/A) — track Mesa releases.

# Ampere (RTX 30, 2020) — GSP matures, and the LHR firmware story

## TL;DR
- Ampere is where the GSP architecture reaches its modern shape: `gsp_ga10x.bin`, RM split into CPU-RM + GSP-RM, and the documented SEC2→GSP boot chain [kernel-firmware MR](https://gitlab.com/kernel-firmware/linux-firmware/-/merge_requests/52), [kernel docs](https://docs.kernel.org/gpu/nova/core/falcon.html).
- The **LHR** mining limiter (2021) is the generation's signature firmware incident: enforced by board SKU + driver handshake, unlocked and re-locked within months [PCMag](https://www.pcmag.com/news/nvidia-confirms-lhr-mining-limiter-has-been-eliminated-from-gpus), [PCWorld](https://www.pcworld.com/article/1354218/some-nvidia-lhr-cards-have-mining-unlocked-on-the-latest-firmware.html).
- Open kernel modules cover GA10x from 515 onward; Ampere remains the best-documented architecture in `open-gpu-doc`.
- Rig ground truth @ 615.71.09: `gsp_ga10x.bin` = 27,043,992 bytes [rig dump](06-ground-truth/dumps-20261015-122221/gsp-firmware-images.txt).

## Consumer SKUs
GA102: RTX 3090 Ti / 3090 / 3080 Ti / 3080 / 3080 12GB. GA103: RTX 3070 Ti. GA104: RTX 3060 Ti / 3070 / 3070 Ti? (3070 = GA104-400). GA106: **RTX 3060 12 GB** (GA106-300; LHR variant **GA106-302** [TPU vBIOS entry](https://www.techpowerup.com/vgabios/238975/238975)) and RTX 3050 8 GB. GA107: RTX 3050 6 GB [VERIFY]. The 3060 (24 SMs, 192-bit, 12 GB) is the 60-class anchor and the first card NVIDIA put a hash-rate limiter on.

## What firmware runs where
- **vBIOS**: BIT/GOP ROM; in Ampere the mining posture is baked into the **board SKU** — non-LHR GA106-300 vs LHR GA106-302 — plus driver-side hash detection. Flashing is version/ID-checked but the era's tools (later OMGVflash/NVflashk) document the checks [TPU](https://www.techpowerup.com/312631/nvidia-bios-signature-lock-broken-vbios-modding-and-crossflash-enabled-by-groundbreaking-new-tools).
- **GSP firmware**: `gsp_ga10x.bin` under `/lib/firmware/nvidia/<ver>/`; GSP-RM absorbs RM tasks off the CPU [kernel-firmware MR](https://gitlab.com/kernel-firmware/linux-firmware/-/merge_requests/52). With `NVreg_EnableGpuFirmware=0` a GA10x card can still run the legacy CPU-RM path [NVIDIA README](https://download.nvidia.com/XFree86/Linux-x86_64/595.104.02/README/gsp.html) — the last generation where that switch meaningfully matters.
- **Engine falcons**: PMU, SEC2, NVDEC (×2 on GA102), NVENC, OFA. The boot chain is publicly documented: the CPU runs Booter ucode in HS mode on the SEC2 falcon, which authenticates and launches GSP-RM in LS mode on the GSP falcon [kernel docs](https://docs.kernel.org/gpu/nova/core/falcon.html).
- **Open kernel modules**: GA10x supported since 515; the driver↔GSP RPC protocol is fully visible in source [repo](https://github.com/NVIDIA/open-gpu-kernel-modules).

## What changed vs. Turing
Samsung 8 nm (bigger dies, more power tables in vBIOS), double the GSP firmware's role, and — unique to this generation — a **deliberate, market-facing firmware feature**: the Lite Hash Rate limiter, jointly implemented across vBIOS SKU and driver. Ampere is also the first generation where the open KMD covers the whole consumer stack (Turing open support was still settling in 515).

## Acquisition points
- `gsp_ga10x.bin`: every 555+ driver package (pre-555: single `gsp.bin` [GitHub issue 62](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/62)); distro firmware packages; versioned per driver release.
- vBIOS: TPU database is unusually rich for Ampere because miners dumped hundreds of GA10x variants; board-ID tags (GA106-302 etc.) identify LHR stock.
- Driver branches 465–535 are the LHR-forensics window (limiter introduced → unlocked → removed) — archived installers are the primary sources.

## RE / community resources
- **open-gpu-doc**: GA10x has the most complete public register documentation of any NVIDIA arch (dev reference manuals for GA102-class) — start there for BAR0 work.
- **NVK/nouveau**: Ampere GSP support is what made NVK possible beyond Turing; see [Mesa NVK docs](https://docs.mesa3d.org/drivers/nvk.html).
- **LHR forensics**: miner tooling (t-rex, NiceHash QuickMiner) shipped LHR detection/unlock logic; their release notes double as firmware-behavior documentation [Tom's coverage](https://www.tomshardware.com/news/nicehash-quickminer-bypasses-nvidia-lhr-limiter).
- **GSP RE**: [NV-GSP-Bootloader](https://github.com/yunjie-deng/NV-GSP-Bootloader) extracts the ELF/bin payloads inside `gsp_ga10x.bin`.

## Notable incidents
- **LHR timeline**: Feb 2021 — RTX 3060 launches with a hash limiter; May/June 2021 — "LHR" branding rolls across RTX 30 (3080 Ti, 3070 Ti, revised SKUs like GA106-302) [PCMag](https://www.pcmag.com/news/nvidia-confirms-lhr-mining-limiter-has-been-eliminated-from-gpus); June 2021 — beta driver 465.21 "restores" full hash rate, NVIDIA calls it accidental, rolls back [Tom's](https://www.tomshardware.com/news/nvidia-restores-mining-performance-on-geforce-rtx-30-lhr-gpus); Oct 2022 — driver 522.25 stops enforcing the limiter on many cards [PCWorld](https://www.pcworld.com/article/1354218/some-nvidia-lhr-cards-have-mining-unlocked-on-the-latest-firmware.html); later drivers remove the limiter code entirely [r/EtherMining](https://www.reddit.com/r/EtherMining/comments/y2l39i/nvidia_removes_lhr_limiter_from_newest_drivers/).
- **Multi-monitor idle-power bug**: high idle draw (100–120 W reported on a 3080) tied to driver/display-bandwidth behavior across 30/40-series [GeForce forums](https://www.nvidia.com/en-us/geforce/forums/game-ready-drivers/13/506049/multi-monitor-bug/).
- **CMP spinoff**: dedicated mining cards (CMP 30/90 HX) shipped with no display outputs — a vBIOS-level product split from the same silicon era.

## Open questions
- [VERIFY] Full SKU map for GA106/GA107 desktop parts (3050 8 GB vs 6 GB silicon) via TPU database.
- [VERIFY] Whether LHR state is *only* board-SKU+driver or also vBIOS-table-visible (a controlled non-production bench test).
- [VERIFY] Exact branch where `NVreg_EnableGpuFirmware=0` stops being honored for GA10x (suspect 570+).
- Open: build a driver-version ↔ `gsp_ga10x.bin` sha256 timeline (465→615) to date behavior changes in GSP-RM.

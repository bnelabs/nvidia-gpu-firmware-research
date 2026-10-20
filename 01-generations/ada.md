> REFERENCE / HISTORICAL REPORT — not a hardware runbook. Current [CONSTITUTION](../CONSTITUTION.md) and [CORRECTIONS](../CORRECTIONS.md) override this material. Offline decompilation and RE remain authorized. Hardware recipes, bench exceptions and blanket complete/safe claims below are superseded; other literature claims have not all been independently revalidated.

# Ada (RTX 40, 2022) — open KMD matures, vBIOS lock broken

## TL;DR
- Ada runs the *same* `gsp_ga10x.bin` image as Ampere — there is no `gsp_ad10x.bin`; AD10x boards load the ga10x image [NVIDIA forum log (AD102 L20)](https://forums.developer.nvidia.com/t/nvidia-corporation-ad102gl-l20-loading-lib-firmware-nvidia-580-95-05-gsp-ga10x-bin-failed-with-error-4/379900).
- vBIOS signature enforcement peaks here — and was broken in 2023 by OMGVflash/NVflashk, advertised "up to 4xxx series" [TechPowerUp](https://www.techpowerup.com/312631/nvidia-bios-signature-lock-broken-vbios-modding-and-crossflash-enabled-by-groundbreaking-new-tools).
- Open kernel modules are NVIDIA-recommended for Ada [dev blog](https://developer.nvidia.com/blog/nvidia-transitions-fully-towards-open-source-gpu-kernel-modules/); NVK reaches conformant Vulkan 1.4 on this generation [Mesa](https://docs.mesa3d.org/drivers/nvk.html).
- Signature power incident: the **12VHPWR** connector-melting wave on RTX 4090 [TechSpot](https://www.techspot.com/news/102833-rtx-4090-owner-16-pin-power-connector-melted.html).

## Consumer SKUs
AD102: RTX 4090 (and 4090D for China). AD103: RTX 4080, 4080 Super. AD104: RTX 4070 Ti, 4070, 4070 Super. AD106: RTX 4060 Ti 8/16 GB. AD107: **RTX 4060** (AD107-400-A1, launched 2023-06-29 [TPU](https://www.techpowerup.com/gpu-specs/geforce-rtx-4060.c4107)). The 4060 (8 GB GDDR6, 128-bit) is the 60-class anchor; its firmware posture is identical to the 4090's.

## What firmware runs where
- **vBIOS**: BIT/GOP ROM + enforced signature checks (cross-flash blocked by vendor/device ID validation until the 2023 tools) [TPU](https://www.techpowerup.com/312631/nvidia-bios-signature-lock-broken-vbios-modding-and-crossflash-enabled-by-groundbreaking-new-tools). Power tables now matter doubly because Ada's 450 W-class cards run the 16-pin power path.
- **GSP firmware**: `gsp_ga10x.bin`, default-on, version-locked to the driver; queried via `nvidia-smi -q` → `GSP Firmware Version` [NVIDIA README](https://download.nvidia.com/XFree86/Linux-x86_64/595.104.02/README/gsp.html).
- **Engine falcons**: PMU, SEC2, 2× NVDEC / 2× NVENC (8th-gen encoder), OFA, plus NVJPG units [VERIFY per chip]; same SEC2→GSP-RM boot chain as Ampere [kernel docs](https://docs.kernel.org/gpu/nova/core/falcon.html).
- **Kernel modules**: both KMDs fully support Ada; NVIDIA recommends open, and the open tree is where Ada features land first [dev blog](https://developer.nvidia.com/blog/nvidia-transitions-fully-towards-open-source-gpu-kernel-modules/).

## What changed vs. Ampere
TSMC 4N (major perf/watt jump, new power-envelope regime), 12VHPWR/ATX 3.0 platform integration, a stronger signature lock on vBIOS — promptly broken — and GSP-RM now effectively standard on every install. Public register documentation regresses slightly vs GA10x (Ada docs are partial in open-gpu-doc), making the open kernel modules themselves the best Ada reference.

## Acquisition points
- `gsp_ga10x.bin`: `.run` packages and distro firmware packages; same path/versioning rules as Ampere [NVIDIA README](https://download.nvidia.com/XFree86/Linux-x86_64/595.104.02/README/gsp.html).
- vBIOS: TPU database (4090/4060 entries plentiful), AIB tools for vendor updates; OMGVflash/NVflashk made modified Ada images flashable, enabling the power-limit-mod scene [TPU](https://www.techpowerup.com/312631/nvidia-bios-signature-lock-broken-vbios-modding-and-crossflash-enabled-by-groundbreaking-new-tools).
- Driver branches 525–570 document the idle-power and GSP-crash fixes in their release notes.

## RE / community resources
- **NVK**: conformant Vulkan 1.4 across officially supported GPUs [Mesa docs](https://docs.mesa3d.org/drivers/nvk.html) — Ada is a primary NVK target.
- **open-gpu-kernel-modules** + issue tracker: de-facto Ada firmware-behavior archive (GSP Xids, power behavior).
- **OMGVflash / NVflashk**: the signature-lock bypass pair [TPU article](https://www.techpowerup.com/312631/nvidia-bios-signature-lock-broken-vbios-modding-and-crossflash-enabled-by-groundbreaking-new-tools), [NVflashk thread](https://www.techpowerup.com/forums/threads/nvflashk-flash-any-bios-to-nvidia-gpus-safe-board-id-bypass-up-to-4xxx-series.312608/).
- **HWiNFO / nvtop**: expose Ada's telemetry channels (per-rail power, hotspot) that sit above firmware sensors.

## Notable incidents
- **12VHPWR melting** (Oct 2022 →): RTX 4090 16-pin connector melt reports within weeks of launch; traced to insertion/bend conditions and connector tolerances rather than silicon; later standardized as the revised 12V-2x6 [TechSpot](https://www.techspot.com/news/102833-rtx-4090-owner-16-pin-power-connector-melted.html).
- **Idle-power behavior**: the multi-monitor idle-draw bug (100–120 W at desktop) persisted across driver branches on 30/40-series [GeForce forums](https://www.nvidia.com/en-us/geforce/forums/game-ready-drivers/13/506049/multi-monitor-bug/) — a GSP-RM/clock-gating behavior visible to any owner.
- **GSP in practice**: RTX 4070 (AD104) users reported repeated Xid-120 GSP-firmware crashes under sustained CUDA load, with GPU resets required — the clearest public example of GSP-RM being a failure point [NVIDIA dev forum](https://forums.developer.nvidia.com/t/rtx-4070-ad104-gsp-firmware-crash-xid-120-pc-0x1a92c96-under-sustained-cuda-workload-windows-bsod-linux-gpu-reset/369685).

## Open questions
- [VERIFY] NVJPG presence/counts on AD102–AD107 consumer dies (media-block documentation is thin).
- [VERIFY] Whether Ada's vBIOS contains any 12VHPWR-related firmware thresholds (per-connector current monitoring) or that is purely board telemetry.
- [VERIFY] First driver branch where `NVreg_EnableGpuFirmware=0` no longer boots Ada cleanly.
- Open: collect Xid-120 / GSP-reset reports by driver version to correlate GSP-RM regressions with specific `gsp_ga10x.bin` builds.

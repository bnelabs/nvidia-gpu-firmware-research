> REFERENCE / HISTORICAL REPORT — not a hardware runbook. Current [CONSTITUTION](../CONSTITUTION.md) and [CORRECTIONS](../CORRECTIONS.md) override this material. Offline decompilation and RE remain authorized. Hardware recipes, bench exceptions and blanket complete/safe claims below are superseded; other literature claims have not all been independently revalidated.

# Rubin ("RTX 60" watchlist) — what is confirmed, what is rumor

## TL;DR
- **CONFIRMED (datacenter)**: Vera Rubin platform — Rubin GPU (dual reticle-sized chiplets) + Vera CPU — with **VR200 NVL144** racks targeted for volume production in 2H 2026 [TechPowerUp](https://www.techpowerup.com/342049/nvidia-vera-rubin-nvl144-servers-set-for-2026-volume-production), [GTC 2026 coverage](https://www.datacenterknowledge.com/data-center-chips/gtc-2026-nvidia-unveils-vera-rubin-ai-platform-eyes-1t-by-2027).
- **CONFIRMED**: Rubin CPX, a context/inference-optimized GPU with 128 GB GDDR7, announced 2025-09-09 [NVIDIA newsroom](https://nvidianews.nvidia.com/news/nvidia-unveils-rubin-cpx-a-new-class-of-gpu-designed-for-massive-context-inference).
- **RUMOR (consumer)**: "RTX 60 series" on gaming Rubin targeting **H1 2027** per supply-chain leaks [tech4gamers](https://tech4gamers.com/rtx-60-rubin-h1-2027/); earlier rumors said 2028 [The PC Enthusiast](https://thepcenthusiast.com/nvidia-rtx-6090-rtx-60-series-rubin-rumors/).
- **Expected firmware posture**: GSP-only, open-KMD-only (continuing the Blackwell mandate) — inference from confirmed policy, not an NVIDIA statement for Rubin.
- Watch the driver branch cadence and `/lib/firmware/nvidia/<ver>/` contents for the first new per-arch GSP image.

## CONFIRMED — with sources

### Datacenter platform (VR200 / Vera Rubin)
- Announced on the GTC 2025 roadmap; named platform details consolidated at GTC 2026: Rubin GPU = **two reticle-sized GPU chiplets**, up to 50 PFLOPS FP4 per accelerator, **288 GB HBM4 per GPU**; **Vera CPU** = 88 Arm cores; first rack system **Vera Rubin NVL144**, 2H 2026 [cloudnews summary](https://cloudnews.tech/nvidia-debuts-the-vera-rubin-superchip-two-reticle-sized-gpus-vera-cpu-with-88-cores-production-targeted-for-2026/), [Data Center Knowledge](https://www.datacenterknowledge.com/data-center-chips/gtc-2026-nvidia-unveils-vera-rubin-ai-platform-eyes-1t-by-2027).
- Supply-chain validation: Foxconn engineering validation of NVL144 MGX liquid-cooled racks, mass production planned 2H 2026 [TechPowerUp](https://www.techpowerup.com/342049/nvidia-vera-rubin-nvl144-servers-set-for-2026-volume-production).
- NVIDIA's own ISC 2026 announcement positions Vera Rubin systems for science (FP64 emphasis) [NVIDIA newsroom](https://nvidianews.nvidia.com/news/nvidia-vera-rubin-delivers-world-class-supercomputers-for-science).
- **Rubin CPX**: announced 2025-09-09, purpose-built for massive-context inference, 128 GB GDDR7, ~30 PFLOPS NVFP4, availability "end of 2026" [NVIDIA newsroom](https://nvidianews.nvidia.com/news/nvidia-unveils-rubin-cpx-a-new-class-of-gpu-designed-for-massive-context-inference). As of Oct 2026 it has **not shipped**; no confirmed retail date [status roundup](https://www.aquanode.io/blog/nvidia-rubin-cpx-guide) [VERIFY — monitor for updates].

### Consumer "RTX 60" — RUMOR, clearly labeled
- Launch window: **H1 2027** per leak-based reporting (earlier 2028 rumors allegedly superseded); the top gaming Rubin config reportedly has an unusual design element [tech4gamers](https://tech4gamers.com/rtx-60-rubin-h1-2027/), [The PC Enthusiast](https://thepcenthusiast.com/nvidia-rtx-6090-rtx-60-series-rubin-rumors/).
- Tier structure (6090/6080/6070/6060), GDDR7 capacity points (3 GB modules), and any HBM-in-consumer claims remain **unconfirmed speculation** [roundup](https://verdictbits.com/news/rtx-60-series/) [VERIFY].
- No NVIDIA statement names a consumer Rubin chip (nothing like "RB102/RB106" exists in official material yet).

## Expected firmware posture (analysis, not announcement)
- **GSP stays and grows**: every NVIDIA GPU since Turing carries the RISC-V GSP, and the RM has migrated there generation by generation [kernel-firmware MR](https://gitlab.com/kernel-firmware/linux-firmware/-/merge_requests/52) — Rubin will extend this, likely with a *new* per-arch GSP image (post-`ga10x` naming) and a larger share of init/management on-die.
- **Open KMD only**: Blackwell already requires the open kernel modules [dev blog](https://developer.nvidia.com/blog/nvidia-transitions-fully-towards-open-source-gpu-kernel-modules/); the closed KMD will not come back for Rubin. Practically: from day one, the driver↔GSP protocol will be public source.
- **Falcon fleet**: expect PMU + SEC2 + media falcons as today [kernel docs](https://docs.kernel.org/gpu/nova/core/falcon.html), plus whatever new accelerators Rubin CPX's "massive-context" silicon implies (more NVJPG-class units? [VERIFY]).
- **vBIOS**: signature enforcement will persist; assume the NVflashk-era bypasses do not carry over (they stop at 4xxx/Ada) [TPU forum](https://www.techpowerup.com/forums/threads/nvflashk-flash-any-bios-to-nvidia-gpus-safe-board-id-bypass-up-to-4xxx-series.312608/).

## What specifically to monitor
1. **Driver branches**: post-580/590/615 numbering; the first branch listing a Rubin/`gb1xx`-class device ID in `open-gpu-kernel-modules` [repo](https://github.com/NVIDIA/open-gpu-kernel-modules).
2. **Firmware drops**: file listing of each new driver's `firmware/` dir (`.run` package) and [kernel-firmware MRs](https://gitlab.com/kernel-firmware/linux-firmware/-/merge_requests/52) — a new `gsp_*.bin` name is the earliest public Rubin trace.
3. **nova-core**: the Rust driver's device coverage expands from GB-series; its commits preview new-arch bring-up [Rust-for-Linux](https://rust-for-linux.com/nova-gpu-driver).
4. **GTC keynotes** (March + October cadence) and NVIDIA newsroom pressers for the consumer naming event.
5. **TechPowerUp vBIOS DB + GPU DB**: first `RB1xx`/Rubin consumer entries and vBIOS dumps usually appear within weeks of leak-stage sampling.
6. **NVK/Mesa**: `nvk.xml`/device-ID additions track new hardware earlier than driver releases [Mesa NVK docs](https://docs.mesa3d.org/drivers/nvk.html).

## Open questions
- [VERIFY] Has NVIDIA committed to any consumer Rubin date/name in an official channel (check GTC 2026 keynote transcripts + newsroom).
- [VERIFY] Rubin CPX shipping status as of this writing (announced end-2026 availability; no confirmed date).
- [VERIFY] Whether consumer Rubin keeps GDDR7 (with 3 GB modules) or moves tier-0 parts to HBM — currently pure rumor.
- [VERIFY] Whether the next GSP image is named `gsp_gb10x.bin`, `gsp_rb10x.bin`, or folds Rubin into `gsp_ga10x.bin` like Ada/Blackwell did.
- Open: build an alert on kernel-firmware + open-gpu-kernel-modules for first Rubin device IDs.

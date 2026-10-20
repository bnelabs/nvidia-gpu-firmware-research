> REFERENCE / HISTORICAL REPORT — not a hardware runbook. Current [CONSTITUTION](../CONSTITUTION.md) and [CORRECTIONS](../CORRECTIONS.md) override this material. Offline decompilation and RE remain authorized. Hardware recipes, bench exceptions and blanket complete/safe claims below are superseded; other literature claims have not all been independently revalidated.

# GSP Firmware (Turing → Blackwell): notes for offline study of one's own hardware

*Research notes for an owner studying their own RTX 3090 rig from an offline analysis machine. Nothing here touches the production GPU: every command below runs on copies of files on a separate box. No malware, no attacks on other people's systems.*

## TL;DR

- The GPU System Processor (GSP) is an on-die RISC-V microcontroller present since Turing; the open kernel modules treat it as mandatory and offload nearly all Resource Manager (RM) work to it ([DeepWiki on GSP](https://deepwiki.com/NVIDIA/open-gpu-kernel-modules/4.3-gsp-communication), [NVIDIA README ch. 43](https://download.nvidia.com/XFree86/Linux-x86_64/555.42.02/README/gsp.html)).
- Consumer firmware ships as `gsp_tu10x.bin` (Turing) and `gsp_ga10x.bin` (Ampere, Ada, *and* Blackwell consumer) under `/lib/firmware/nvidia/<driver-version>/`; the r6xx branches add `ucodes_*.bin` companions ([Arch nvidia-utils 615.78.08 file list](https://archlinux.org/packages/extra/x86_64/nvidia-utils/files/)).
- The open-gpu-kernel-modules GitHub repo does **not** ship the binary; you must pull it from the `.run` package (`--no-kernel-modules` install per the [repo README](https://github.com/NVIDIA/open-gpu-kernel-modules)) or from a distro package.
- Driver↔GSP RPC runs over a shared-memory ring (page table + command queue + status queue) with 4 KiB elements, max 16 pages per element, oversized messages split via continuation records ([kernel.org nouveau docs](https://docs.kernel.org/gpu/nouveau.html)).
- Message payloads are FINN-serialized RM API calls; interface IDs cover CLK/THERMAL/POWER/VOLT/PERF/LPWR/NVLINK subdevices ([g_finn_rm_api.h](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/common/sdk/nvidia/inc/g_finn_rm_api.h)).
- Firmware size grew ~67 % between r535 and r570 for the same GA102 blob (38,061,600 B → 63,571,696 B) — see [linux-firmware `nvidia/ga102/gsp`](https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/tree/nvidia/ga102/gsp) — so version-diffing is fruitful.
- The 2025 RTX 50 "black screen waves" were fixed by driver hotfixes 572.42/572.65/572.75; no public attribution to GSP firmware itself ([TechPowerUp](https://www.techpowerup.com/333854/nvidia-irons-out-blackwell-black-screen-issues-with-latest-geforce-hotfix-display-driver-v572-75)).
- GPUBreach (2026) shows the trust boundary: the driver blindly trusts `elemCount` written by GSP into the status queue; Rowhammer-corrupted PTEs turn that into a kernel heap overflow ([Stealthium analysis](https://stealthium.io/blog/gpubreach-root-cause-analysis-detection), [gpubreach.ca](https://gpubreach.ca/)).
- Swapping `gsp_*.bin` files cannot brick the card (the GPU just fails driver init until you restore the file); vBIOS flashing is the dangerous operation, not GSP.

## 1. What the GSP is and what it absorbed

The GSP is a dedicated RISC-V processor integrated on NVIDIA GPUs starting with Turing, driven by firmware that runs GSP-RM — a full Resource Manager that used to live in the closed kernel driver ([DeepWiki](https://deepwiki.com/NVIDIA/open-gpu-kernel-modules/4.3-gsp-gpu-system-processor)). The host-side `nvidia.ko` keeps only a thin "CPU-RM" shim and talks to "GSP-RM" over RPC.

What it absorbed, generation by generation, is visible in the driver README changelog:

- **r510 (March 2022)**: single `gsp.bin`; GSP default only on a handful of datacenter boards (T4, A100, A30, A40, A16, A2). Turing+ could opt in with `NVreg_EnableGpuFirmware=1`, but "the driver will not yet correctly support display-related features or power management related features" ([README ch. 42 for 510.39.01](https://download.nvidia.com/XFree86/Linux-x86_64/510.39.01/README/gsp.html)).
- **r530/r535 (2023)**: suspend/hibernate/resume and Resizable BAR support land, then Run-Time D3 (RTD3) "on Ampere and later GPUs" and G-Sync ([CHANGELOG 530.30.02 / 535.43.02](https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/535.104.05/CHANGELOG.md)).
- **r555 (2024)**: "The GSP firmware will be used by default for all Turing and later GPUs" — display, power, thermal all moved behind RPC ([README ch. 43](https://download.nvidia.com/XFree86/Linux-x86_64/555.42.02/README/gsp.html)).
- **Blackwell (r570+, 2025)**: open kernel modules are the only supported kernel driver for GeForce RTX 50, so GSP-RM is structurally unavoidable; the kernel-side modules "must be used with GSP firmware ... from a corresponding driver release" ([open-gpu-kernel-modules README](https://github.com/NVIDIA/open-gpu-kernel-modules)). Community documentation states the open modules require GSP for *all* operations, including hardware init ([DeepWiki compatibility page](https://deepwiki.com/scottjg/open-gpu-kernel-modules/1.2-hardware-compatibility-and-gpu-generations)).

Query side (on any box where the driver is already loaded — do not run this on the production rig; the `/proc` file is read-only and informational): `nvidia-smi -q | grep -A1 "GSP Firmware"` or `cat /proc/driver/nvidia/gpus/<domain:bus:dev.fn>/information` show the running GSP firmware version ([README](https://download.nvidia.com/XFree86/Linux-x86_64/580.95.05/README/gsp.html)).

## 2. Firmware acquisition

**Linux driver path.** The `.run` installer installs firmware to `/lib/firmware/nvidia/<version>/` (changelog-confirmed since 525.53). To extract without installing:

```bash
# extract, don't install (makeself)
sh NVIDIA-Linux-x86_64-615.71.09.run -x --target ./nvrun-615
find ./nvrun-615 -maxdepth 1 -name 'gsp_*.bin' -o -name 'ucodes_*.bin'
```

**Windows driver packages.** The Windows installer is a zip archive; the same OS-agnostic GSP blobs are inside (exact subfolder [VERIFY]):

```bash
7z x 615.71.09-desktop-win10-win11-64bit-international-dch-whql.exe -o./win-drv
find ./win-drv -iname '*gsp*' -o -iname '*ucode*'
```

**GitHub.** open-gpu-kernel-modules releases contain source only; the README explicitly instructs installing GSP firmware + user space from the matching `.run` with `--no-kernel-modules`. Redistribution itself is tolerated: NVIDIA staff stated "the intent is to allow gsp.bin to be redistributed" ([issue #62](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/62)) — still, respect the NVIDIA software license; these are firmware blobs, not GPL artifacts.

**nouveau/linux-firmware path** (per-chip directories rather than per-driver-version, [linux-firmware `nvidia/` tree](https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/tree/nvidia)):

```bash
# ga102/gsp as of 2026-10 (sizes in bytes):
#   gsp-535.113.01.bin      38,061,600
#   gsp-570.144.bin         63,571,696
#   booter_load-570.144.bin     61,304   booter_unload-570.144.bin  41,080
#   bootloader-570.144.bin      24,684
# gb202/gsp (Blackwell): only bootloader-570.144.bin + fmc-570.144.bin
```

The same directories exist for `ad102`, `ga100`, `gh100`, `gb100`. Note GB202 has *no* `gsp-*.bin` yet — the nova-core driver first boots Blackwell through a Firmware Management Controller (FMC) stage and a firmware sequencer before GSP-RM's INIT_DONE RPC ([nova-core patch series](https://lore.freedesktop.org/nouveau/20251113014119.1286886-13-joelagnelf@nvidia.com/)).

**Version map (driver-package naming), as far as verifiable from public changelogs/file lists:**

| Branch / release | GSP files shipped | Evidence |
|---|---|---|
| 515.43.04 (2022-05) | `gsp.bin` (monolithic) | [CHANGELOG](https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/525.53/CHANGELOG.md) |
| 525.53 (2022-11) | `gsp_tu10x.bin` + `gsp_ad10x.bin`, "replacing gsp.bin" | same CHANGELOG |
| 530.30.02 (2023-02) | renamed to `gsp_tu10x.bin` + `gsp_ga10x.bin` | [CHANGELOG 535.104.05](https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/535.104.05/CHANGELOG.md) |
| 570.133.07 (2025) | `gsp_ga10x.bin`, `gsp_tu10x.bin` (observed on-disk) | [NV-GSP-Bootloader README](https://raw.githubusercontent.com/yunjie-deng/NV-GSP-Bootloader/master/README.md) |
| 615.78.08 (2026) | `gsp_ga10x.bin`, `gsp_tu10x.bin`, **plus** `ucodes_ga10x.bin`, `ucodes_tu10x.bin` | [Arch file list](https://archlinux.org/packages/extra/x86_64/nvidia-utils/files/) |

So despite the name, `gsp_ga10x.bin` is the one consumer file that has carried Ampere, Ada and (since r570) Blackwell RTX firmware — the r525-era `gsp_ad10x.bin` name was retired in r530 "to better reflect the GPU architectures supported by each firmware file". A separate Hopper file (`gsp_gh10x.bin`) reportedly exists in datacenter packages [VERIFY]. Which exact branch introduced the `ucodes_*.bin` split [VERIFY].

## 3. Image format and community parsers

The `.bin` is a container ("binArchive") holding multiple stages; community extraction confirms embedded ELF objects inside:

- [yunjie-deng/NV-GSP-Bootloader](https://github.com/yunjie-deng/NV-GSP-Bootloader) — `./bootloader_descriptor` pulls out the boot stage (`kgspBinArchiveGspRmBoot_GA102_ucode_image_prod_data`), `extract_fwimage.py` extracts "all bin and elf inside `gsp_ga10x.bin`", and `disassemble_bootloader.py` disassembles it. It also emulates the bootloader up to LibOS load, and `capture_gsp_wpr_meta.py` grabs runtime WPR (write-protected region) metadata via a live kprobe.
- [airlied/gsp-parse](https://github.com/airlied/gsp-parse) — not a `.bin` parser but the key ABI tool: it parses NVIDIA's open kernel headers into JSON, then generates Rust modules for the GSP interface, which is documented as having "an unstable ABI" (the file names in the firmware change shape between branches).
- `nouveau/extract-firmware-nouveau.py` in the open-gpu-kernel-modules repo repacks driver firmware for nouveau's per-chip layout ([script](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/nouveau/extract-firmware-nouveau.py)).
- A tool called `nvgspfw` circulates in search lore but I could not verify its existence or provenance — treat any such claim [VERIFY] until a repo or release page is found.

Boot chain on Ampere (per nouveau's `nvkm/subdev/gsp/` and the linux-firmware layout): ACR booter (`booter_load`/`booter_unload`) loads a `bootloader` falcon stage, which loads the GSP-RM image; a signed FWSEC sequencer participates ([nouveau gsp sources incl. fwsec.c](https://github.com/torvalds/linux/tree/master/drivers/gpu/drm/nouveau/nvkm/subdev/gsp)). On Blackwell the FMC stage comes first (see §2).

Practical offline first pass:

```bash
strings -a gsp_ga10x-615.78.08.bin | grep -Ei 'acr|wpr|sec2|pmu|nvdec|elf|symbol' | sort -u | head
binwalk gsp_ga10x-615.78.08.bin            # entropy + embedded headers
file ./extracted/*.elf                     # NV-GSP-Bootloader output
readelf -S ./extracted/*.elf               # sections reveal RISC-V code + data
```

Cautions: loading a modified `gsp.bin` is recoverable (delete/replace the file, reload modules), but never mix kernel-module, GSP and user-space versions — the README requires an exact version match. Custom firmware development on signed GPUs is effectively blocked by signature verification at load time ([Stealthium](https://stealthium.io/blog/gpubreach-root-cause-analysis-detection)); keep experiments in static analysis, emulation (NV-GSP-Bootloader), or on paper.

## 4. The GSP RPC protocol

**Shared memory, three regions.** The kernel driver allocates one host-RAM block (`pSharedMemDesc`) that is DMA-mapped for the GPU (IOMMU-permitted): a page table, then the command queue (CPU→GSP), then the status queue (GSP→CPU) — verified against `src/nvidia/src/kernel/gpu/gsp/message_queue_cpu.c` ([Stealthium's annotated walkthrough](https://stealthium.io/blog/gpubreach-root-cause-analysis-detection)).

**Element layout** ([kernel.org nouveau docs](https://docs.kernel.org/gpu/nouveau.html), which mirror the headers at [`src/nvidia/inc/kernel/gpu/gsp/message_queue_priv.h`](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/535/src/nvidia/inc/kernel/gpu/gsp/message_queue_priv.h)):

```
+---------------------------------+
| r535_gsp_msg      (queue header)|
|   nvfw_gsp_rpc    (RPC header: |
|     function number, length,   |
|     seq)                       |
|   payload: FINN message        |
+---------------------------------+
```

- Max element = 16 pages; larger messages are split, later parts tagged with the continuation-record function number.
- Reply policies in nouveau: `NOWAIT`, `NOSEQ`, `RECV`, `POLL`.
- Measured ring parameters from a live instrumented system: `size=262144 msgSize=4096 entryOff=4096 msgCount=63` ([Stealthium](https://stealthium.io/blog/gpubreach-root-cause-analysis-detection)).

**Payload encoding.** RM control calls ride inside RPC payloads; on current branches they are FINN-serialized. `FINN_RM_API` is a 32-byte header `{version, payloadSize, interface, message}` and every RM class gets an interface ID — e.g. `FINN_NV20_SUBDEVICE_0_CLK_INTERFACE_ID = 0x208010`, `..._THERMAL_ = 0x208005`, `..._POWER_ = 0x208027`, `..._VOLT_ = 0x208032`, `..._PERF_ = 0x208020`, `..._LPWR_ = 0x208028`, `..._NVLINK_ = 0x208030`, `..._GSP_ = 0x208036` ([g_finn_rm_api.h, tag 615.78.08](https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/615.78.08/src/common/sdk/nvidia/inc/g_finn_rm_api.h)). The classic `NV_VGPU_MSG_FUNCTION_*` function-number enum still routes the top-level RPCs; a per-branch table [VERIFY].

**Init sequence.** The kernel driver loads `gsp.bin`, the boot stages run (sequencer on Blackwell), GSP-RM boots inside a WPR region, then the driver waits for an `INIT_DONE` RPC and retrieves GPU static info ([nova-core series](https://lore.freedesktop.org/nouveau/20251113014119.1286886-13-joelagnelf@nvidia.com/)). Core kernel-side code lives in `src/nvidia/src/kernel/gpu/gsp/kernel_gsp.c` and `message_queue_cpu.c` ([listing](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/main/src/nvidia/src/kernel/gpu/gsp/kernel_gsp.c)).

**How nouveau speaks it.** `nvkm` has a dedicated `gsp` subdev; since r535 the RM protocol implementation sits under `nvkm/subdev/gsp/rm/r535/...` with per-generation glue (`tu102.c`, `ga102.c`, `ad102.c`, `gh100.c`, `gb202.c`) ([torvalds/linux tree](https://github.com/torvalds/linux/tree/master/drivers/gpu/drm/nouveau/nvkm/subdev/gsp)). The kernel documentation (§ nouveau "GSP Support") is the best free protocol reference.

**Tracing/logging tools.**

- nouveau's GSP RPC debug logging was overhauled in Feb 2026 to classify events vs. responses and to fix wire-level sequence numbers ([LKML patch](https://lkml.org/lkml/2026/2/10/1476), [dri-devel series](https://lists.freedesktop.org/archives/dri-devel/2026-February/548556.html)) — boot with `drm.debug=0x100`-class settings and read `dmesg` for a full RPC trace on the nouveau path.
- On the NVIDIA open modules, `GspMsgQueueReceiveStatus` is the single receive choke point (219k calls observed in one session, `elemCount=1` normally) — kprobe/bpftrace-compatible ([Stealthium](https://stealthium.io/blog/gpubreach-root-cause-analysis-detection)).
- The often-cited "mstoeckl GSP RPC recorder" could not be verified: the author's freedesktop GitLab contains Wayland tooling only ([project list](https://gitlab.freedesktop.org/api/v4/users/mstoeckl/projects)); status [VERIFY].
- [Open-IOV's GSP RPC emulation](https://open-iov.org/index.php/GSP_RPC_Emulation) runs unmodified consumer GSP firmware while emulating missing vGPU RPC handlers in kernel/userspace — a working example of speaking the protocol yourself.

## 5. What GSP controls per generation

From the interface IDs above plus the changelog arc: GSP-RM owns GPU init, memory/FB management, engine allocation, and the subdevice controls for **clocks** (CLK/PERF), **power** (POWER/VOLT/LPWR — RTD3, Dynamic Boost plumbing), **thermal** (THERMAL, via RPC-polled sensor data), **link** (NVLINK/PCIe state; consumer cards mostly PCI-E), and **events/IRQs** (event buffers, MMU fault buffer interfaces; the host only gets notifications via the status queue).

- **Ampere (GA10x)**: first consumer generation to run GSP by default; gained RTD3 in r535 ([CHANGELOG](https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/535.104.05/CHANGELOG.md)). On a RTX 3090 every `nvidia-smi` query of clocks/temperature/loops is an RPC round-trip under the hood.
- **Ada (AD10x)**: served by the same `gsp_ga10x.bin` file from r530 onward; no separate consumer file name, and the ABI differences are handled inside the one blob.
- **Blackwell (GB10x)**: also inside `gsp_ga10x.bin` for the proprietary stack, but the open-source nova path boots via FMC + bootloader first ([linux-firmware gb202/gsp](https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/tree/nvidia/gb202/gsp)); open kernel modules are mandatory, making GSP-RM the *only* RM. Datacenter Blackwell (GB100) and Hopper (GH100) have their own per-chip firmware directories ([linux-firmware nvidia/ tree](https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/tree/nvidia)).

## 6. Bugs, incidents, security

- **RTX 50 black-screen waves (Jan–Mar 2025)**: GeForce community threads tracked black screens on 40/50-series through driver 572.42 ([forum](https://www.nvidia.com/en-us/geforce/forums/game-ready-drivers/13/557368/40-50-series-black-screen-bug-fix-in-driver-57242/)), a 572.65 hotfix that initially "caused more problems" ([XDA](https://www.xda-developers.com/nvidia-hotfix-black-screen-fix-rtx-50-series/)), and the 572.75 hotfix explicitly fixing "GeForce RTX 50 series GPUs crashes with black screen [5120886]" ([NVIDIA forum](https://www.nvidia.com/en-us/geforce/forums/game-ready-drivers/13/559436/announcing-geforce-hotfix-driver-57275-released-38/), [TechPowerUp](https://www.techpowerup.com/333854/nvidia-irons-out-blackwell-black-screen-issues-with-latest-geforce-hotfix-display-driver-v572-75)). Public bug IDs are display-stack items; direct GSP-firmware attribution was never published [VERIFY — diff `gsp_ga10x.bin` across 570.x builds to check].
- **GSP RPC channel deaths**: "Timeout waiting for RPC from GSP!" ([issue #446](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/446)) and "GSP RPC channel stops responding (status 0x11) during GPU suspend" ([issue #1439](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1439)) are the canonical firmware-unresponsive signatures.
- **r570 suspend/resume regression in nouveau**: after R570 firmware, several GPUs failed suspend; fixed with RPC sequence-number handling in Feb 2026 ([Airlie series](https://lore.freedesktop.org/nouveau/f0047a7e-7114-4375-b6eb-8bf1b7a82262@nvidia.com/T/)).
- **GPUBreach (2026, U. Toronto)**: Rowhammer flips aperture bits in a GPU PTE so a framebuffer write lands in the IOMMU-permitted status queue; the driver reads GSP-written `elemCount` without bounds checks (`GspMsgQueueReceiveStatus`, staging buffer = 16 elements, ring = 63) and overflows `msgqMetadata` function pointers — still unfixed in 595.58.03 per the analysis ([Stealthium](https://stealthium.io/blog/gpubreach-root-cause-analysis-detection), [gpubreach.ca](https://gpubreach.ca/)). Lesson for an owner: the RPC receive path is the attack surface, not the signed firmware. (Note the Stealthium post calls the GSP an "ARM processor"; every primary source says RISC-V.)
- **Early-boot fragility**: r515's "kgspInitRm_IMPL: missing NVDEC0 engine, cannot initialize GSP-RM" ([CHANGELOG](https://raw.githubusercontent.com/NVIDIA/open-gpu-kernel-modules/525.53/CHANGELOG.md)) shows how a single missing engine descriptor used to abort GSP-RM init.
- **Adjacent firmware fix waves**: NVIDIA's DisplayID/DisplayPort firmware update tools fix boot-time blank screens — vBIOS/display firmware, *not* GSP ([DisplayID tool KB](https://nvidia.custhelp.com/app/answers/detail/a_id/5233/~/nvidia-gpu-firmware-update-tool-for-displayid), [DP tool page](https://www.nvidia.com/en-us/drivers/nv-uefi-update-x64/)).
- No standalone GSP-firmware CVE surfaced in the security bulletins reviewed for 2025–2026 [VERIFY]; driver CVEs (e.g., CVE-2026-24187 UAF, [May 2026 bulletin](https://nvidia.custhelp.com/app/answers/detail/a_id/5821/~/security-bulletin:-nvidia-gpu-display-drivers---may-2026)) concern the driver, not the RISC-V image.

## Creative techniques

**Version-diffing `gsp_ga10x.bin` across branches.** Collect the same-architecture blob from several driver packages (§2), then:

```bash
sha256sum gsp_ga10x-570.153.02.bin gsp_ga10x-580.95.05.bin gsp_ga10x-615.71.09.bin
cmp -l gsp_ga10x-570.153.02.bin gsp_ga10x-580.95.05.bin | wc -l        # changed bytes
# section-aware diff after ELF extraction (NV-GSP-Bootloader):
python3 extract_fwimage.py gsp_ga10x-570.153.02.bin
python3 extract_fwimage.py gsp_ga10x-615.71.09.bin
diff -rq fwimage-570.153.02/ fwimage-615.71.09/
readelf -n fwimage-615.71.09/*.elf | grep -i version
```

The 38 MB → 63.5 MB jump between r535 and r570 blobs suggests whole subsystems moved in — correlate with changelog feature waves (RTD3, Resizable BAR, suspend, GSP default on all Turing+).

**Strings/symbol mining.** The archive embeds ELF objects with symbol tables, so `strings`, `nm`, and `readelf` recover subsystem names, RPC handler names, and version strings without executing anything. Cross-reference hits against the FINN interface IDs in `g_finn_rm_api.h` to map blobs to RM classes (CLK/THERMAL/POWER/LPWR/…). airlied's JSON-DB approach (headers → structs → codegen) is the scalable version of this for the *wire ABI*, which is officially unstable.

**A userspace GSP RPC client — honest scope.** The wire structs (`r535_gsp_msg`, `nvfw_gsp_rpc`, FINN messages) are all public in the open-kernel-modules tree, so a user-space parser for *captured* RPC logs is straightforward; but the queues live in kernel DMA memory with no user-space export, so a live client means either nouveau-style kernel code, an instrumented module, or Open-IOV's in-kernel emulation approach ([Open-IOV](https://open-iov.org/index.php/GSP_RPC_Emulation)). Start by writing a log replay/decoder against nouveau's documented layout ([kernel.org docs](https://docs.kernel.org/gpu/nouveau.html)).

**Tracing RPCs live via bpftrace/ftrace** (on a *test* box, never the production rig):

```bash
# find the choke point symbols in the loaded modules
sudo cat /proc/kallsyms | grep -E 'GspMsgQueue|gspMsgQueue|r535_gsp'
# count calls and sizes on the open kernel modules
sudo bpftrace -e 'kprobe:GspMsgQueueReceiveStatus { @[comm] = count(); } interval:s5 { print(@); clear(@); }'
# nouveau equivalent
sudo bpftrace -e 'kprobe:gsp_msgq_recv { @[cpu] = count(); }'
```

Caveats: `nvidia.ko` is built from this source but its symbols may be stripped depending on install; if kprobes fail, fall back to the kprobe-based capture script from [NV-GSP-Bootloader](https://github.com/yunjie-deng/NV-GSP-Bootloader) (`capture_gsp_wpr_meta.py` is a working template) or nouveau's built-in debug logging.

**Diff-driven change detection for your rig's firmware.** Keep a private manifest of sha256 sums per branch (`570.x … 615.x`) for `gsp_ga10x.bin`/`ucodes_ga10x.bin`; when a driver update lands, hash-compare *before* installing on the inference box, and diff any changed blob offline to see which subsystems the update actually touched.

## Open questions

- [VERIFY] Does the "mstoeckl GSP RPC recorder" exist at all? Freedesktop GitLab shows only Wayland projects ([list](https://gitlab.freedesktop.org/api/v4/users/mstoeckl/projects)); if it exists it is elsewhere (personal site/blog) — otherwise treat the parent claim as folklore.
- [VERIFY] `nvgspfw` / "NVIDIA GSP firmware extractor": no verifiable repo found as of 2026-10; NV-GSP-Bootloader + gsp-parse cover the same ground.
- [VERIFY] Exact folder of GSP firmware inside Windows driver packages after `7z x` (and whether `ucodes_*.bin` ships there too).
- [VERIFY] Which branch first introduced `ucodes_tu10x.bin`/`ucodes_ga10x.bin` (observed in r615; not in r570.133.07).
- [VERIFY] Presence and naming of datacenter files `gsp_gh10x.bin` (Hopper) / GB100 variants in driver packages.
- [VERIFY] Full `NV_VGPU_MSG_FUNCTION_*` numbering table for r615 (name a source file in the tree or nouveau `rm/r535`).
- [VERIFY] Whether RTX 50-series black-screen fixes (572.42/572.65/572.75) changed `gsp_ga10x.bin` bytes at all — needs blob-level diffing of the 570.x hotfix packages.
- [VERIFY] Blackwell details: whether GSP-RM for GB10x consumer is fully inside `gsp_ga10x.bin` in r615, and what the FMC (`fmc-570.144.bin`) actually does before the sequencer hands off to GSP-RM.
- [VERIFY] Any CVE assigned specifically to GSP firmware (RISC-V image) rather than the driver stack.

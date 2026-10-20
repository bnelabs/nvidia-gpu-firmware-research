# Boot / Verification Chain Across GPU Generations (Pascal → Rubin)

*Compiled 2026-10-20. Primary evidence: `open-gpu-kernel-modules` tag 615.78.08 (local checkout `vendor/open-gpu-kernel-modules`), kernel nova-core docs 7.3.0, NVIDIA open-gpu-doc Falcon-Security, envytools, nouveau `fwsec.c`, binary strings of local `gsp_ga10x.bin` / `gsp_tu10x.bin` (615.71.09). Claim-by-claim citations inline; anything not directly verified is marked [VERIFY].*

## 0. The universal falcon trust model

Everything below reduces to one hardware mechanism that NVIDIA has refined since 2008:

**Falcon BROM (per-microcontroller hardware boot ROM) → HS ucode → LS/NS ucode.**

- **Falcon** = small custom RISC-like microcontroller, first shipped on G98 (2008) as the VP3 video-controller replacement for Xtensa; hardware revisions: v0 (G98/MCP77/79), v3 (GT215+, crude code VM), v4 (GF119+, 24-bit addressing + debug support), v4.1 (GK110+), v5 (GK208+, redesigned ISA encoding). A falcon with the optional AES coprocessor is called a "secretful" unit. [envytools falcon intro](https://envytools.readthedocs.io/en/latest/hw/falcon/intro.html)
- **Security modes** (NVIDIA's own doc): **NS** — pre-Maxwell-equivalent but restricted (some registers inaccessible, physical memory access can be disabled); **HS (Heavy Secure, PL3)** — the core is a black box: no external read/write of any falcon state/registers. Enabled only by NVIDIA-signed microcode: host tags the IMEM block secure, writes the signature into a falcon register, starts execution; **hardware validates the signature and grants HS**; **LS (Light Secure, PL2)** — introduced on **GM20x**; more privileges than NS, fewer than HS; some state visible to host; only HS ucode can enable LS mode. [open-gpu-doc Falcon-Security](https://nvidia.github.io/open-gpu-doc/Falcon-Security/Falcon-Security.html), [nova-core falcon doc](https://docs.kernel.org/gpu/nova/core/falcon.html)
- **Root of trust**: each falcon has a BROM; the host programs BROM/DMA registers so the falcon DMA-loads HS ucode from sysmem into IMEM/DMEM; the **BROM itself computes the signature check**. Once verified HS code runs, it verifies and loads LS/NS ucodes onto other falcons (signature math identical, but computed by HS ucode, not hardware). [nova-core falcon doc](https://docs.kernel.org/gpu/nova/core/falcon.html)
- **LS image encryption**: LS falcon descriptors carry `prdKeys[2][16]` / `dbgKeys[2][16]` / `kdf[16]`, and a separate `LSF_ENCRYPTION_CONTEXT` with `bLsEncrypted` + 16-byte IV — **LS payloads are AES-128-CBC encrypted**, with separate production/debug key slots. [rmlsfm.h L268-576 in 615.78.08](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/arch/nvalloc/common/inc/rmlsfm.h)
- **ACR (Access Control Resource)** is the firmware that orchestrates this: it validates LS ucode descriptors, programs WPR (write-protected region) access masks, and bootstraps target falcons ("Light Secure Falcon Management", LSF). Its host-side descriptor: WPR region ID/offset, read/write masks, VPR lockdown payload, `SIG_VERIF` enable flag. Status codes include `VALIDATION_CODE_FAILED`, `VALIDATION_DATA_FAILED`, **`REVOCATION_CHECK_FAILED`** (anti-rollback), `BOOTSTRAP_READY`. A mailbox value of `0xDEADDEAD` (`LSF_FALCON_MODE_TOKEN_FLCN_INSECURE`) marks a falcon that did not boot securely. [rmlsfm.h](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/arch/nvalloc/common/inc/rmlsfm.h)
- **ACR's home moved by generation** (direct from rmlsfm.h comments): "The PMU supports the ACR task on **GM20X_thru_VOLTA** profiles only" → ACR ran on **PMU** for Maxwell→Volta (incl. Pascal). "pre-hopper **SEC2**-RTOS/ACR ucode" → ACR ran on **SEC2** for Turing→Ada. Hopper+ → ACR runs as **GSP-FMC** on the GSP itself (see §2).
- **LSF falcon ID namespace** (one signing/identity table across all generations): PMU=0, DPU/GSPLITE=1, FECS=2, GPCCS=3, NVDEC=4, NVENC=5, NVENC1=6, SEC2=7, NVENC2=8, MINION=9, FBFALCON=10, XUSB=11, **GSP_RISCV=12**, PMU_RISCV=13, SOE=14, NVDEC1=15, OFA=16, SEC2_RISCV=17, NVDEC_RISCV=18, and RISC-V "_EB" (externally-booted) variants 19-30, LPSEC=31. [rmlsfm.h L125-159](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/arch/nvalloc/common/inc/rmlsfm.h)
- **What HS protects, by era** (Falcon-Security doc): GM10x — fuses/ROM write-protected from non-secure falcons. GM20x — + thermal shutdown registers and I2C bus C writes restricted to secure context, ucode placed in a write-protected memory region (the WPR idea), **physical memory access denied to NS falcons other than PMU and DPU**, and **devinit scripts signed and executed on the PMU**. This is the baseline Pascal inherits.

## 1. The canonical Ampere boot chain (documented end-to-end by nova-core)

Ampere is the best-documented generation because nova-core's kernel documentation walks it explicitly ([falcon.html](https://docs.kernel.org/gpu/nova/core/falcon.html), [fwsec.html](https://docs.kernel.org/gpu/nova/core/fwsec.html)) and every element is cross-checkable in `open-gpu-kernel-modules` 615.78.08:

```
POST: vBIOS (SPI ROM) → BIT falcon-ucode table (type 0xE0 partition)
      → launches FWSEC on the GSP falcon in HS mode (before OS driver loads)
        → runs devinit engine, ECC/VRAM scrubbing, VPR init
        → FWSEC-SB: secure-boots other microcontrollers (PMU etc. in LS)

Driver load (nouveau / open KMD):
 1. Scrubber ucode if needed                      (GSP falcon, HS)
 2. FWSEC-FRTS: carve WPR2 + write FRTS data (1 MiB, GC6 AON)
    → host resets GSP falcon, DMA-loads FWSEC from vBIOS image,
      BROM verifies RSA-3072 signature, runs HS
    → verifies via VBIOS scratch regs (FRTS error code) and
      NV_PFB_PRI_MMU_WPR2_ADDR_LO/HI placement
 3. Booter Load (HS on SEC2 falcon, BROM-verified)
    → loads + verifies + boots GSP-RM into WPR2
 4. GSP bootloader → kernel_<arch>.elf (GSP-RM) runs on GSP RISC-V in LS
    → SEC2-RTOS problem: nothing left to load SEC2's own RTOS, so GSP
      briefly runs a GSP-provided HS "sequencer" that loads SEC2-RTOS
      in LS, then returns to GSP-RM LS
 5. FWSEC-SB re-check ("GFW BOOT progress COMPLETED" +
    "GFW PLM lowered" in NV_PGC6_AON_SECURE_SCRATCH_GROUP_05, error code
    in VBIOS scratch 15) → driver treats GPU as trusted-initialized
 6. GSP-RM raises INIT_DONE RPC → RM control plane moves behind GSP RPC

Driver unload (pre-Hopper): FWSEC-SB restores pre-OS apps, Booter Unload
tears down WPR2; on Hopper+ the driver instead waits for "ACR and GSP FMC
to finish shutdown" (kflcnWaitForHaltRiscv).
```

Sources: [kernel_gsp.c L5551-5556 (FRTS/FWSEC comment)](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/src/kernel/gpu/gsp/kernel_gsp.c), [L5610-5613 (Booter on SEC2/NVDEC0; partitioned-FMC alternative)](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/src/kernel/gpu/gsp/kernel_gsp.c), [kernel_gsp_frts_tu102.c (HS falcon execution, WPR2 checks)](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/src/kernel/gpu/gsp/arch/turing/kernel_gsp_frts_tu102.c), [kernel_gsp_tu102.c L396-442 (boot ordering)](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/src/kernel/gpu/gsp/arch/turing/kernel_gsp_tu102.c), [nouveau fwsec.c (FRTS=0x15/SB=0x19 DMEM-mapper commands, v2/v3 ucode descriptors)](https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/nouveau/nvkm/subdev/gsp/fwsec.c), [nova fwsec.html (FWSEC layout, RSA-3K 384-byte signatures, scrubbing/VPR roles)](https://docs.kernel.org/gpu/nova/core/fwsec.html).

**FWSEC itself** lives in the vBIOS ROM as a falcon ucode application: PMU lookup table, app_id **0x85 = FWSEC-PROD**, **0x45 = FWSEC-DBG** (open-gpu-kernel-modules `FALCON_UCODE_ENTRY_APPID_FWSEC_PROD/DBG`, kernel_gsp_fwsec.c L126-127). The driver picks debug vs prod FWSEC by **fuse state** (§4). Descriptor v3 carries `PKCDataOffset`, `SignatureCount`, `SignatureVersions` — signatures are **384-byte RSA-3K** entries ([nova fwsec.html](https://docs.kernel.org/gpu/nova/core/fwsec.html)).

## 2. FMC — Firmware Management Controller

**What it is.** The first-stage ucode of the GSP boot binary on Hopper and later: the kernel comment says "The GSP-FMC (**namely ACR**) logs error codes to NV_PGSP_FALCON_MAILBOX0 during boot" — i.e., FMC is ACR's new home, running on the GSP RISC-V itself instead of PMU/SEC2 ([kernel_gsp_gh100.c L638](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/src/kernel/gpu/gsp/arch/hopper/kernel_gsp_gh100.c)). It performs the secure boot of the remaining GSP firmware partitions and manages WPR2: on GB10B "the actual offsets are determined by secure ACR ucode and patched into the GspFwWprMeta structure" ([kernel_gsp_gb10b.c](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/src/kernel/gpu/gsp/arch/blackwell/kernel_gsp_gb10b.c), WPR-meta magic `0xdc3aae21371a60b3`, [gsp_fw_wpr_meta.h](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/arch/nvalloc/common/inc/gsp/gsp_fw_wpr_meta.h)).

**When it was introduced.** The HAL field `bPartitionedFmc` ("the secure boot ucode is included in the partitioned FMC, no need for separate Booter ucodes", kernel_gsp.c L5610-5616) is TRUE for exactly: **GH100, GB100, GB102, GB10B, GB10C, GB110, GB112, GB202, GB203, GB205, GB206, GB207, GB20B, GB20C, GR100, GR102** ([g_kernel_gsp_nvoc.c L467-476](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/generated/g_kernel_gsp_nvoc.c)). Corroborating bindata: Booter Load/Unload archives exist **only** for TU102, TU116, GA100, GA102, AD102 (`g_bindata_kgspGetBinArchiveBooter{Load,Unload}Ucode_*`), while Concatenated FMC + FMC-desc archives exist for **GH100, GB100, GB202, GR100** (`g_bindata_kgspGetBinArchiveConcatenatedFMC*`). So: **FMC debuted with Hopper (2022), consumer adoption at Blackwell (2025), Rubin continues**. Ada is the last consumer generation booted by SEC2-Booter. Linux-firmware mirrors this: `nvidia/gb202/gsp` contains only `bootloader-570.144.bin` + `fmc-570.144.bin` (no booter), while `ad102/gsp` retains booter_load/booter_unload.

**How it changes boot.** Pre-Hopper: BROM → FWSEC (vBIOS, HS on GSP) → Booter Load (HS on SEC2) → bootloader → GSP-RM (LS). Hopper+: BROM → **GSP-FMC/ACR (in the boot binary, HS)** → FMC verifies and loads the GSP-RM partitions and pre-OS apps itself; no SEC2 Booter stage. On Blackwell the nova-core driver boots "through a Firmware Management Controller (FMC) stage and a firmware sequencer before GSP-RM's INIT_DONE RPC" (nova-core patch series, [lore](https://lore.freedesktop.org/nouveau/20251113014119.1286886-13-joelagnelf@nvidia.com/)). FMC failures are reported in `NV_PBUS_SW_SCRATCH_GSP_FMC_ERROR` (variant/partition/payload fields, SK error/phase) ([gsp_fmc_error_code_formatting.h](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/arch/nvalloc/common/inc/gsp/gsp_fmc_error_code_formatting.h)) and `NV_PGSP_FALCON_MAILBOX0`. In confidential-compute configurations the FMC image and its descriptor ship as signed bindata embedded in the kernel modules themselves (`GspRmCcFmcGfwProdSigned_GB100`, `ConcatenatedFMC_{GH100,GB100,GB202,GR100}`), and GSP-RM boot **blocks until an SPDM session with the GSP responder is established** ([kernel_gsp_gh100.c L1183+](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/src/kernel/gpu/gsp/arch/hopper/kernel_gsp_gh100.c)).

**Chain-of-Trust (COT) boot** (Hopper+ datacenter/iGPU path): an FSP (fabric/security processor) receives an NVDM/MCTP payload `NVDM_PAYLOAD_COT` containing SHA-384 `hash384[12]`, `publicKey[96]` and `signature[96]` words — **RSA-3072** — plus `gspFmcSysmemOffset`, FRTS sysmem/vidmem offsets ([kern_fsp_cot_payload.h](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/inc/kernel/gpu/fsp/kern_fsp_cot_payload.h)). During COT the "PRIV target mask is typically locked" and `NV_PFALCON_FALCON_HWCFG2.RISCV_BR_PRIV_LOCKDOWN` reports the GSP boot-ROM lockdown state — hardware evidence of a **RISC-V boot ROM on the GSP** whose privileged range gets locked in COT mode ([kernel_gsp_gh100.c L600-620](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/src/kernel/gpu/gsp/arch/hopper/kernel_gsp_gh100.c)).

## 3. The gsp.bin container is multi-architecture (binary-verified)

The shipping consumer image is *not* one architecture — it is a binArchive of per-arch signed kernel ELFs. Strings from the local corpus (615.71.09, sha256 `c420726d…`):

- `gsp_ga10x.bin` (27,043,992 B) embeds: `kernel_ga10x.elf`, `kernel_ad10x` (signature only), `kernel_gb10x.elf`, `kernel_gb10y.elf`, `kernel_gb20x.elf`, `kernel_gb20y.elf`, `kernel_gh100.elf`, **`kernel_gr10x.elf`** — each with a matching `.fwsignature_<arch>` section, **plus confidential-computing signature variants** `.fwsignature_cc_{gb10x,gb20x,gh100,gr10x}`.
- `gsp_tu10x.bin` (22,897,536 B) embeds signatures `.fwsignature_{ga100,tu10x,tu11x}`.

**This directly verifies the "Rubin: gr10x signatures present in shipping firmware" claim**: GR100/GR102 (Rubin) GSP kernels and signatures ride inside the 615.71.09 consumer image, alongside HAL entries (`bPartitionedFmc` includes GR100|GR102) and shipped register headers `src/common/inc/swref/published/rubin/gr100/` in 615.78.08. Note the naming history: 525 shipped `gsp_ad10x.bin`, retired in r530 "to better reflect the GPU architectures supported by each firmware file" → `gsp_ga10x.bin` has been the one consumer file since (see [gsp-firmware.md §2](../02-firmware/gsp-firmware.md)).

## 4. Debug vs production: fuses

- **GSP debug fuse** (selects FWSEC-DBG appid 0x45 / FMC UCODE_DESC_DBG vs PROD): `kgspIsDebugModeEnabled_HAL` reads `NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS` on **Turing (tu102), Ampere (ga100), Hopper (gh100)** — debug mode = fuse *not* burned (`FLD_TEST_DRF(...,_NO,data)`) ([kernel_gsp_tu102.c L90-104](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/src/kernel/gpu/gsp/arch/turing/kernel_gsp_tu102.c)). On **Blackwell the fuses moved to a zero-bank (ZB) register file**: `NV_FUSE_ZB_OPT_SECURE_GSP_DEBUG_DIS` at `gpuGetPrimaryFuseBaseAddr_HAL() + offset` ([kernel_gsp_gb100.c L315-323](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/src/kernel/gpu/gsp/arch/blackwell/kernel_gsp_gb100.c)); Hopper already ships `dev_fuse_zb.h` alongside `dev_fuse.h`, while gb100/gb202 ship **only** `dev_fuse_zb.h` — the legacy FUSE_OPT bank is gone on Blackwell.
- **Anti-rollback / revocation**: `NV_FUSE_OPT_FPF_GSP_UCODE{1..16}_VERSION` — "FPF" (Firmware Protection Fuse) one-hot per-ucode-version fuses; `kgspReadUcodeFuseVersion_GA100` returns highest-bit-index+1, and boot paths compare against the ucode's `SignatureVersions`/`fuse_ver` descriptor field; failure surfaces as `LSF_IMAGE_STATUS_REVOCATION_CHECK_FAILED` ([kernel_gsp_ga100.c L51-73](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/src/kernel/gpu/gsp/arch/ampere/kernel_gsp_ga100.c), [rmlsfm.h L313-321](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/615.78.08/src/nvidia/arch/nvalloc/common/inc/rmlsfm.h)). This is the mechanism that makes downgrading GSP/falcon firmware impossible on fused production parts.
- **GC6 exception**: signature checks are skipped on GC6 exit ("since we dont check signatures in GC6 exit, we need to hardcode the WPR offset", rmlsfm.h L97-99) — the S3/GC6 resume path trusts WPR contents restored by Booter, an intentional gap in the verification chain.
- **Physical debug access**: falcon v4 hardware added debug support (envytools), but the envytools falcon-debug page is an unwritten stub — public knowledge of falcon debug HW ends there; in HS mode the core is a black box by design, and no public JTAG/SWD documentation exists for GeForce dGPUs [VERIFY]. The deepest public defeat of an NVIDIA boot chain remains the 39C3 talk on Tegra X2 (USB bootloader exploit → fault injection → unpatchable BootROM vulnerability) — methodology, not dGPU path ([39C3 talk](https://media.ccc.de/v/39c3-making-the-magic-leap-past-nvidia-s-secure-bootchain-and-breaking-some-tesla-autopilots-along-the-way)).

## 5. Generation-by-generation table

| | **Pascal GP10x (2016)** | **Turing TU10x/11x (2018)** | **Ampere GA10x (2020)** | **Ada AD10x (2022)** | **Blackwell GB2xx (2025)** | **Rubin GR10x (watchlist)** |
|---|---|---|---|---|---|---|
| **MCUs on die** | No GSP. PMU, SEC(-2), FECS/GPCCS ctx-switch falcons, NVDEC/NVENC falcons, PDAEMON; driver-loaded ucodes | **GSP debuts** (RISC-V, LSF id 12) + PMU, SEC2, NVDEC/NVENC, OFA; PMU_RISCV in LSF table | GSP + PMU + SEC2 + NVDEC/NVENC + OFA | GSP + PMU + SEC2 + 2×NVDEC/2×NVENC + OFA (+NVJPG [VERIFY]) | GSP (largest RM share) + PMU + SEC2 + media falcons + NVJPG; FMC-first | GR100/GR102 in 615.78.08 HAL; GSP + FMC-boot chips (bPartitionedFmc=TRUE) |
| **Firmware components** | vBIOS (BIT tables + GOP) + signed devinit scripts run on PMU + falcon ucodes loaded by driver; no gsp.bin | vBIOS incl. FWSEC ucode (BIT falcon table, 0x85/0x45) + `gsp_tu10x.bin`; Booter Load/Unload bindata (TU102/TU116) in KMD | vBIOS + FWSEC + `gsp_ga10x.bin` (kernel_ga10x.elf); Booter (GA100/GA102 bindata); linux-firmware booter_load/unload + bootloader per-chip | Same ga10x image (`.fwsignature_ad10x` inside); **AD102 still Booter** (bindata exists) — last consumer Booter gen | vBIOS + `gsp_ga10x.bin` (kernel_gb20x.elf) + **FMC in boot binary**; linux-firmware `gb202/gsp` = `bootloader` + `fmc` only, no booter | `kernel_gr10x.elf` + `.fwsignature_gr10x` (+ `_cc_`) already inside shipping 615.71.09 `gsp_ga10x.bin`; ConcatenatedFMC_GR100 bindata in 615.78.08 |
| **Boot chain** | vBIOS → signed devinit on PMU → driver loads falcon ucodes (ACR on PMU validates LS) | vBIOS → FWSEC (HS on GSP) → FRTS/WPR2 → Booter (HS on SEC2) → GSP-RM (LS) | Same, fully documented by nova (§1); GSP temporarily runs HS sequencer to load SEC2-RTOS | Same as Ampere; GSP default-on for all Turing+ from r555 | **BROM → GSP-FMC/ACR (HS)** → FMC loads/verifies GSP-RM partitions; no SEC2 Booter; SPDM session gates GSP-RM in CC | FMC-first continues (GR100/GR102 in bPartitionedFmc set) |
| **Signature enforcement** | vBIOS table mods practical (nvflash era); partial signature-hash coverage since Fermi per GPU-Z author; falcon ucodes signed | vBIOS signature lock active (Maxwell-era origin); GSP image signed; FPF ucode-version fuses (tu102 dev_fuse) | Same; FPF_GSP_UCODE{1..16}_VERSION anti-rollback fuses; LHR = SKU/vBIOS + driver heuristics, not crypto | Same; nvflashk board-ID bypass reaches 4xxx; signature bypass **only ≤Turing** (OMGVflash/NVflashk, Aug 2023) | FMC/ACR-signed boot; ZB fuse bank; no public sig bypass for GB2xx [VERIFY] | Same as Blackwell (FMC chips); GR10x kernels ride in consumer blob |
| **LS/HS usage** | LS via ACR-on-PMU (GM20x→Volta window); NS for driver-loaded ucodes | FWSEC HS on GSP; Booter HS on SEC2; GSP-RM LS; SEC2 ACR era begins | Same as Turing (canonical example in nova docs) | Same; ACR-on-SEC2 ("pre-hopper SEC2-RTOS/ACR") | FMC/ACR in HS on GSP; everything else LS/NS; COT locks PRIV target mask | Same |
| **FMC** | none | none | none | none | **standard** (partitioned FMC replaces Booter) | standard (from first silicon in-tree) |
| **Debug/production fuses** | GSP_DEBUG_DIS n/a (no GSP) [VERIFY for non-GSP fuses] | `FUSE_OPT_SECURE_GSP_DEBUG_DIS` (dev_fuse.h); debug FWSEC 0x45 selectable when unfused | Same fuse; FPF version fuses (dev_fuse.h) | Same (ad102 inherits ga100-class fuse map [VERIFY]) | Fuses move to zero-bank: `FUSE_ZB_OPT_SECURE_GSP_DEBUG_DIS` via primary-fuse base; gb202 ships dev_fuse_zb.h only | same ZB scheme expected |
| **RE tooling** | envytools complete (ISA/envydis, rnndb, nvbios, nva); Martin Peres PMU RE (OSPERT'13); Kepler/Maxwell BIOS Tweaker lineage; nvflash | + open-gpu-kernel-modules TU102 HAL; Turing register manual (open-gpu-doc); NV-GSP-Bootloader (extracts + emulates GSP bootloader, WPR-meta capture) | + open-gpu-doc GA100/GA102 manuals; nouveau GSP + extract-firmware-nouveau.py; per-chip linux-firmware blobs; gsp-parse ABI codegen; bpftrace on `GspMsgQueueReceiveStatus`; Open-IOV GSP RPC emulation | + no Ada register manual published [per repo README]; OMGVflash/NVflashk; NVK conformant | + open KMD source as documentation (GB202 HAL + gb202 swref); nova-core Rust driver + kernel docs (falcon/fwsec/vbios); FMC-error scratch decoding; SPDM tooling | + rubin/gr100 swref headers in-tree; GR10x kernel ELF extractable from shipping gsp_ga10x.bin; no manuals [VERIFY] |

## 6. What matters for custom-firmware development

1. **The only software-reachable verification gaps are host-side.** GSP image swaps are recoverable (driver init fails, restore file); falcon/GSP ucodes themselves are BROM/RSA-3072 verified and FPF-fused — custom *signed-payload* development is effectively blocked without NVIDIA keys; the actionable surface is vBIOS BIT tables (power/clock policy), GSP RPC (FINN interfaces), and the driver-visible debug/scratch channels.
2. **FWSEC is the vBIOS↔driver bridge**: extracted from the vBIOS BIT falcon table by both the open KMD and nouveau; runs on the GSP falcon in HS; command interface = DMEM-mapper "DMAP" struct (FRTS 0x15 / SB 0x19). Any custom boot-chain work must be conversant with `FalconUCodeDescV3` (PKC offset, SignatureCount/Versions) and app ids 0x85/0x45.
3. **FMC moves the ACR trust anchor onto the GSP** (Hopper+; consumer from Blackwell): the SEC2-Booter stage disappears, FMC ships inside the boot binary (and as embedded bindata in CC mode), and error telemetry moves to `SW_SCRATCH_GSP_FMC_ERROR` + `PGSP_FALCON_MAILBOX0`. Debug FWSEC/DESC selection still hinges on one fuse bit per generation (OPT → ZB bank at Hopper/Blackwell).
4. **Anti-rollback is fuse-enforced**, not just signature-enforced: FPF one-hot version fuses + `REVOCATION_CHECK_FAILED`. Production parts cannot boot older firmware; debug (unfused) parts select `_DBG` ucode variants.
5. **GC6/resume skips signature checks** (rmlsfm.h L97-99) — a documented trust-chain shortcut worth knowing when reasoning about suspend/resume attack surface.
6. **Rubin is already in the shipping consumer blob**: GR10x kernel ELF + signatures inside `gsp_ga10x.bin` 615.71.09, GR100/GR102 HAL + bindata + swref headers in 615.78.08 — firmware-side Rubin RE can start now, before hardware ships.

## 7. Open questions carried forward

- [VERIFY] Pascal-era non-GSP debug fuse map (only tu102+ verified here).
- [VERIFY] Whether any GB2xx vBIOS signature bypass (nvflashk-class) exists today.
- [VERIFY] Public JTAG/SWD posture of GeForce dGPUs (envytools debug page is a stub; nothing primary found).
- [VERIFY] Exact FMC provenance pre-Hopper (Tegra FMC usage) — kernel comments only define GSP-FMC.
- [VERIFY] Whether `.fwsignature_cc_*` sections are consumed only in CC boots or also in the normal path.


## GC6-exit signature skip — assessment disposition

The documented GC6-exit trust shortcut (rmlsfm.h:96-97: signatures are not checked when
re-booting GSP-RM from WPR2 after a GC6 sleep) was assessed as a security finding and
**closed as INFORMATIONAL** (see 04-gc6/threat-model.md and 04-gc6/exploitability.md).
The shortcut requires host-kernel code execution to reach, grants nothing beyond existing
kernel privileges, cannot persist across reboot (the NORMAL boot path always re-verifies),
and — decisively — the trusted state it reuses lives inside WPR2, a hardware write-protected
region that neither host kernel code nor guests can modify during the GC6 window. The skip
is a deliberate design choice whose safety depends on WPR2 hardware protection, and that
protection holds. No PSIRT report is warranted.

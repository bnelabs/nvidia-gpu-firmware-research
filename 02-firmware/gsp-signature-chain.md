> REFERENCE / HISTORICAL REPORT — not a hardware runbook. Current [CONSTITUTION](../CONSTITUTION.md) and [CORRECTIONS](../CORRECTIONS.md) override this material. Offline decompilation and RE remain authorized. Hardware recipes, bench exceptions and blanket complete/safe claims below are superseded; other literature claims have not all been independently revalidated.

# GSP firmware signature chain: SEC2 → Booter/FMC → GSP-RM (Turing → Rubin)

*Research notes for the lab rig's owner; compiled 2026-10-20 from the vendored r615
open-gpu-kernel-modules tree, the on-disk `firmware-store/gsp*` containers, nova-core
kernel docs, and public web sources. Analysis of owned hardware/files only.*

**Method:** every load-bearing claim below is either (a) decoded directly from the local
r615 driver source / firmware bytes (labeled **[DECODED]**), (b) read from NVIDIA's own
published docs or code (labeled **[CITED]**), or (c) inference (labeled **[INFERRED]** /
**[VERIFY]**). Verified-crypto results were reproduced by script in this analysis session.

## TL;DR

1. **Where the check happens.** The host driver never verifies GSP firmware. The chain is
   hardware-fused root → HS verifier → GSP-RM:
   - **Turing/Ampere (pre-Hopper):** Falcon **Boot ROM** on the SEC2 falcon verifies the
     *Booter* (HS) → the Booter authenticates *GSP-RM* (LS) on the GSP falcon.
     [CITED: nova-core falcon docs]
   - **Hopper / GB100 / GB202 / Rubin (FSP present):** **FSP** (Foundation Security
     Processor, the GPU's internal root of trust, boots from immutable ROM) verifies an
     **FMC** image via a driver-supplied Chain-of-Trust message and boots it; **FMC
     ("GSP-FMC", the secure ACR ucode) then authenticates and loads GSP-RM**. No SEC2
     booter, no FWSEC-FRTS stage. [CITED: nova-core fsp doc + r615 `kern_fsp_gh100.c`]
   - **Blackwell consumer (GB20x/GB10x):** same message-driven COT flow, but **SEC2**
     plays the FSP role (`ksec2SetupGspImages_GB20B` builds the same
     `NVDM_PAYLOAD_COT`). [DECODED: `kernel_sec2_gb20b.c`]
2. **Algorithm.** The FMC image is hashed with **SHA-384** — proven by script:
   `sha384(UCODE_IMAGE) == UCODE_HASH` in the r615 driver bindata for both GB202 and
   GH100 prod images. The signature/key shipped alongside are **RSA-3072 (384-byte
   modulus + 384-byte signature)** on GH100/GB10B/GB20B and, on **GB100/GB202/GR100,
   97-byte public key starting with `0x04` + 96-byte signature = uncompressed ECDSA
   P-384 point + (r‖s)** [INFERRED from sizes/prefix; driver treats the blobs as opaque].
   Falcon-ucode signatures in this family are documented as 384-byte "RSA-3K" per the
   nova FWSEC doc. [CITED + DECODED]
3. **`.fwsignature_<arch>` sections are signature blobs, not keys.** Each is 0x1000 bytes:
   a constant 20-byte header, then **4 × 384-byte RSA-3K signature slots at 512-byte
   stride** (plus an 8-byte-ish trailer) [DECODED]. They are the signatures *for the
   GSP-RM image*, selected per GPU arch (ga10x…gr10x, + `cc_` confidential-computing
   variants). The public key that verifies them is *not* in the container — it lives
   inside the signed verifier (booter/FMC) and/or the fuses [INFERRED].
4. **Custom GSP-RM:** swapping `gsp_*.bin` on disk is unrestricted (host trusts it), but
   the on-GPU HS verifier will reject any modified payload. Loading modified GSP-RM
   therefore requires NVIDIA's per-arch private key, a vulnerability in the HS verifier,
   or a hardware/fuse-level attack. No public GSP-RM signature bypass exists as of
   2026-10. The broken-signature tools (OMGVflash/NVflashk) are **vBIOS-only** and do not
   touch the GSP chain.
5. **Debug mode is a fuse**, `FUSE_OPT_SECURE_GSP_DEBUG_DIS` (Turing/GA; `FUSE_ZB_…` on
   GB100), which flips the driver between *prod-signed* and *debug-signed* FMC/GFW
   images. [DECODED]

---

## 1. Boot chains by generation

### 1.1 Turing / Ampere / Ada (SEC2 booter era)

[CITED: [nova-core Falcon doc](https://docs.kernel.org/gpu/nova/core/falcon.html),
[Falcon-Security](https://download.nvidia.com/open-gpu-doc/Falcon-Security/1/Falcon-Security.html),
[SLM-OS GSP bring-up notes](https://github.com/SLM-OS/SLM-Operating-System/blob/main/docs/nvidia-gsp.md)]

```
Falcon BROM (SEC2 hardware, fused root key)
  └─ HS ucode: Booter (booter_load / booter_unload) on SEC2 falcon
       └─ authenticates GSP-RM (LS) onto the GSP falcon (RISC-V), inside WPR2
```

Order of operations (Ampere), from nova-core + r615 code:
1. FWSEC is extracted from the **VBIOS** (not from gsp.bin); on GA10x **FWSEC-FRTS runs on
   the GSP core in HS mode** and carves the WPR2 write-protected region.
   [CITED: [nova FWSEC doc](https://docs.kernel.org/gpu/nova/core/fwsec.html)]
2. Driver builds a radix-3 page table for the GSP-RM ELF, populates
   `GspFwWprMeta` (256 B, magic `0xdc3aae21371a60b3`, revision 1 — "bumped up when we
   revoke GSP-RM ucode") including `sysmemAddrOfSignature`/`sizeOfSignature`
   (= the `.fwsignature_<arch>` blob). [DECODED: `gsp_fw_wpr_meta.h`,
   `kernel_gsp_tu102.c:753`]
3. Driver resets SEC2, loads the Booter, passes the WPR-meta address in mailboxes
   (`booter.rs::run`). The HS Booter copies the ELF into WPR2, verifies it, and starts
   the GSP RISC-V core; WPR2 is then locked.
4. SEC2-RTOS is later loaded by *temporarily* running GSP HS ucode (the "sequencer")
   because LS/NS loads must come from an HS context. [CITED: nova falcon doc]

Booter packaging (from the driver, converted for nouveau by NVIDIA's own
`nouveau/extract-firmware-nouveau.py`): `nvfw_bin_hdr` (magic `0x10de`, ver 1) +
`nvfw_hs_header_v2` + N signatures (1..15) + `{patch_loc, patch_sig, fuse_ver, engine_id,
ucode_id, num_sigs}`. The signature is *patched into the image* at `patch_loc`; the
signature **index is selected by the hardware fuse version** read per falcon
(`reg_fuse_version`; 0 = use last signature). [DECODED: script + `booter.rs`]

### 1.2 Hopper / GB100 / GB202(FSP SKU) / Rubin — FSP era

[CITED: [nova FSP doc](https://docs.kernel.org/gpu/nova/core/fsp.html);
DECODED: `kern_fsp_gh100.c`, `kern_fsp.c`, `gspifpub.h`]

```
FSP (Foundation Security Processor) — immutable ROM, GPU-internal root of trust
  └─ FMC (Falcon Microcontroller; a.k.a. GSP-FMC / secure ACR ucode)
       └─ authenticates + loads GSP-RM (LS) on the GSP falcon; FMC/ACR sets up WPR2
```

- Driver polls a scratch register for FSP self-boot completion, then sends a **COT
  (Chain of Trust) MCTP/NVDM message** containing: FMC image sysmem address, **SHA-384
  hash**, **RSA-3K public key**, **RSA-3K signature**, FRTS region info, and the GSP boot
  args address. [CITED: fsp doc; DECODED: `NVDM_PAYLOAD_COT` fill in
  `kern_fsp_gh100.c:995-1090` — field literally named `hash384`]
- On Hopper the WPR meta layout is "BOOT BIN (e.g. GSP-FMC)" + "GSP FW ELF", and
  `sizeOfBootloader` = FMC ucode size, `sizeOfRadix3Elf` = GSP-RM ELF size;
  "actual offsets … patched in by secure ACR ucode". [DECODED: `kgspPopulateWprMeta_GH100`]
- FWSEC-FRTS / Booter stages do not exist here ("no SEC2 involvement, no Booter ucode, no
  FWSEC-FRTS stage"). [CITED: fsp doc]

### 1.3 Blackwell consumer (GB20x) — same COT protocol, SEC2 as verifier

[DECODED: `kernel_sec2_gb20b.c:708-800`]

`ksec2SetupGspImages_GB20B()` allocates sysmem for the **GSP-FMC image** and fills the
same `NVDM_PAYLOAD_COT` (`gspFmcSysmemOffset`, `hash384`, `signature`, `publicKey`) —
the consumer Blackwell flow is message-driven with **SEC2** authenticating FMC, then FMC
boots GSP-RM. (GB10B has the equivalent `ksec2SetupGspImages_GB10B`.)

### 1.4 Which SKU uses what (r615 tree)

[DECODED: bindata + HAL files]
- FSP HALs: `hopper/gh100`, `blackwell/gb100` + `gb202`, `rubin/gr100`.
- SEC2 COT HALs: `blackwell/gb20b`, `gb10b` (consumer/GB10 paths).
- Legacy booter HALs (TU102/TU116/GA100/GA102/AD102 bindata): `BooterLoadUcode_*`.
- Monolithic-RM (non-GSP-RM) fallback images (`GspFmcGfw*`, RM-proxy, inst-in-sys) exist
  for the "RM in kernel driver" mode. [DECODED: `_ksec2GetGspUcodeArchive`]

---

## 2. Signature verification mechanism

### 2.1 Root of trust = falcon BROM + fuses

- Falcon security modes NS/LS/HS are NVIDIA-documented; HS entry requires microcode
  "signed by NVIDIA" — IMEM tagged secure, signature written to a falcon register, HW
  validates before granting HS. [CITED: Falcon-Security]
- Root key material: BROM verifies HS ucode against a **fused public-key hash**; the ucode
  image itself carries the **PKC data** (public key) at `pkc_data_offset` and the
  signature patched at `patch_loc`. [CITED: nova falcon/fwsec docs + booter.rs
  `FalconBromParams{pkc_data_offset, engine_id_mask, ucode_id}`]
- Hash: nova FWSEC doc documents **"384 bytes per sig — RSA-3K"** for falcon ucode
  signatures; the FMC COT path uses **SHA-384**. [CITED/DECODED]

### 2.2 The FMC/GFW crypto material — measured from r615 bindata [DECODED]

Driver bindata archives `kgspGetBinArchiveGspRm*FmcGfw*_{ARCH}` contain 4 labels:
`UCODE_IMAGE` (the FMC ucode, 165–287 KB), `UCODE_HASH`, `UCODE_SIG`, `UCODE_PKEY`.

| archive | image (B) | hash | sig | pubkey | read |
|---|---|---|---|---|---|
| GH100 prod / cc / debug | 165–167K | 48 | **384** | **384** | RSA-3K + SHA-384 |
| GB10B prod / debug | 190K | 48 | **384** | **384** | RSA-3K + SHA-384 |
| GB20B prod / debug | 284–287K | 48 | **384** | **384** | RSA-3K + SHA-384 |
| GB100 prod / cc / debug | 196–198K | 48 | **96** | **97** (starts `0x04`) | ECDSA P-384 [INFERRED] |
| GB202 prod / cc / debug | 257–287K | 48 | **96** | **97** (starts `0x04`) | ECDSA P-384 [INFERRED] |
| GR100 prod / cc / debug | 203–216K | 48 | **96** | **97** | ECDSA P-384 [INFERRED] |

- **Verified:** `sha384(UCODE_IMAGE) == UCODE_HASH` for `GspRmFmcGfwProdSigned_GB202` and
  `_GH100` (reproduced by script). So the SHA-384 covers the *entire FMC image*.
- 97 = 1+48+48 (uncompressed P-384 point), 96 = r‖s — the GB202 PKEY's first byte is
  literally `0x04`. Algorithm not named in driver code (blobs are opaque to it; FSP does
  the verify), so "ECDSA P-384" is a strong inference, not a doc'd fact. [VERIFY]

### 2.3 Key rotation / revocation

- Booter/falcon ucodes ship **multiple signatures (1–15)**; the *hardware fuse version*
  per (engine_id, ucode_id) selects which one is valid; `0` = use last.
  [DECODED: `booter.rs` FUSE/PLOC logic, `kgspReadUcodeFuseVersion_GB100`]
- `GspFwWprMeta.revision` "bumped up when we revoke GSP-RM ucode" — revocation is also
  handled by interface revision. [DECODED: `gsp_fw_wpr_meta.h`]
- Per-arch `.fwsignature` blobs (below) carry **4 signature slots** — consistent with the
  same fuse-version rotation scheme, selected by the on-GPU verifier. [INFERRED]

---

## 3. The `.fwsignature_<arch>` sections (decoded from our containers)

[DECODED: `firmware-store/gsp/615.71.09/gsp_ga10x.bin`, `gsp_tu10x.bin`,
`gsp-history/ga102/{535.113.01,570.144}.bin`]

- **Names present per generation** (all 0x1000 bytes each, PROGBITS):
  - 535 (ga102): `cc_gh100, gh100, ad10x, ga10x`
  - 570 (ga102): `+ gb20x, cc_gb10x, gb10x` (7)
  - 615 (ga10x file): `cc_gr10x, gr10x, gb20y, cc_gb20x, gb20x, cc_gb10x, gb10y, gb10x,
    cc_gh100, gh100, ad10x, ga10x` (12)
  - tu10x file: `ga100, tu11x, tu10x` (3)
  - → one file serves every arch since Ampere; the driver picks the section matching the
    GPU (prefix `.fwsignature_` / `.fwsignature_cc_` for confidential computing).
    [DECODED: `g_kernel_gsp_nvoc.h:278-283, 2371`]
- **Blob layout** (identical in 535/570/615 and across arches):
  ```
  +0x000  20-byte header (constant everywhere):
          01 00 02 00 | c8 08 00 00 | 0c 00 00 00 | 01 01 00 00 | 00 02 00 00
          (u16 1, u16 2, u32 0x8c8=2248, u32 12, u32 0x101, u32 0x200=512)
  +0x014  sig slot 0: 384 bytes (ends 0x194)
  +0x214  sig slot 1: 384 bytes
  +0x414  sig slot 2: 384 bytes
  +0x614  sig slot 3: 384 bytes
  +0x800  trailer: sparse metadata (01 01 00 01 …, ends 0x885)
  → 512-byte stride, 384-byte RSA-3K signatures, ~108 bytes zero padding per slot
  ```
- **`gr10x` slots in the 615 blob are placeholders** (`55 aa 00…ffff…`) — Rubin signatures
  are not populated in this consumer build. [DECODED]
- Header semantics (version fields, count `12`, `0x101`, size `0x8c8`) are not publicly
  documented; the on-GPU verifier (booter/FMC) parses it. [VERIFY]
- **They are signatures, not public keys** — no 384-byte modulus structure, and 4 slots
  would not fit a key; the verifier's key is anchored in HS-signed code/fuses. [INFERRED]
- **Driver handling:** `kgspGetGspFw` extracts the section into `GSP_FIRMWARE.pSignatureData`;
  `_kgspCreateSignatureMemdesc` copies it into GPU-visible memory
  (`NV_ALIGN_UP(signatureSize,256)`); the address is handed to the verifier through
  `GspFwWprMeta.sysmemAddrOfSignature` (TU102:753, GH100 populate path). The driver
  performs **no verification of its own**. [DECODED]
- What is signed: the GSP-RM payload. Our digest experiments (sha256/384/512 of the raw
  `.fwimage`) did **not** match anything in the blob — the signed input is presumably a
  hash computed by the verifier over the WPR-loaded ELF (or over an archive sub-image
  list), not a raw digest stored in the blob. [VERIFY]

---

## 4. FMC (Firmware Management Controller) role

- **Identity:** "FMC" = the falcon-arch security microcontroller image NVIDIA calls
  GSP-FMC / ACR ("secure ACR ucode" sets up WPR2 on Hopper+). nova-core calls it the
  "Falcon Microcontroller". [CITED: fsp doc; DECODED: `kgspPopulateWprMeta_GH100` comments]
- **Verification:** FSP (or SEC2 on GB20x) verifies the FMC image via COT (hash+sig+key,
  §2.2) and boots it; **FMC then authenticates and launches GSP-RM** and lays out WPR2.
  [CITED: fsp doc; DECODED: `GSP_FMC_BOOT_PARAMS` in `gspifpub.h` — magic `'FMC '`,
  contains ACR boot params, GSP-RM desc pointer, SPDM params, regkeys]
- **Variants in driver bindata:** prod-signed / debug-signed / CC (confidential computing
  "CcFmcGfw"), plus "GspFmcInstInSysGfwDebugSigned" (inst-in-sys) and monolithic-RM proxy
  images. [DECODED: `kfspGetGspUcodeArchive`, `_ksec2GetGspUcodeArchive`]
- The FMC image is a small falcon-format binary (not `nvfw_bin_hdr`-wrapped; header
  starts `03 04 48 00 …`), distinct from the booter's HS-header-v2 package. Project's
  ODS-layout notes (LOG wave 3e) already cover `nvfw_bin_hdr`/HS-header v2/FMC ELF.
  [DECODED]

---

## 5. What loading custom (modified) GSP-RM would actually take

Trust model, bottom to top:
1. **Host side: no enforcement.** The driver loads whatever `gsp_*.bin` (and now
   `ucodes_*.bin`) is on disk; a modified container with a broken signature blob changes
   nothing host-side. Bricking risk ≈ 0 (driver init just fails). [DECODED + project
   gsp-firmware.md]
2. **On-GPU enforcement:** GSP-RM is authenticated by an HS component anchored in fuses:
   - pre-Hopper: Booter (HS, BROM-verified) checks the payload using the
     `.fwsignature` blob from WPR meta;
   - Hopper+/GB20x: FMC (verified by FSP/SEC2 via COT with SHA-384 + RSA-3K/ECDSA)
     checks the payload.
   WPR2 hardware then write-protects the region. [CITED+DECODED]
3. **Therefore** a custom GSP-RM requires one of:
   - **(a) NVIDIA's per-arch private key** (unobtainable) — the "honest" path; also what
     NVIDIA itself does per release;
   - **(b) a vulnerability in the HS verifier** (booter or FMC) or in the COT handshake —
     none published publicly for GSP as of 2026-10; the verifier code is small falcon
     firmware and is a genuinely unstudied RE target (our r615 bindata contains the FMC
     images, ~165–287 KB each — a tractable disassembly target, envydis/Ghidra);
   - **(c) hardware attack on the BROM/verify step** — precedent: 39C3 2025 broke the
     Tegra X2 secure bootchain via USB bootloader exploit + fault injection + unpatchable
     BootROM bug [CITED: prior-art.md §4]; voltage/clock glitching of the falcon verify
     is the analogous move, effectiveness on GA10x+ unknown [SPECULATIVE];
   - **(d) debug-mode hardware** — dev boards with `FUSE_OPT_SECURE_GSP_DEBUG_DIS` *not*
     blown accept **debug-signed** FMC/GFW images (§6), i.e. a different (debug) key;
     production silicon is fused off. [DECODED]
   - Not viable: nvflash-class vBIOS tools (they don't touch GSP-RM, see §7);
     vgpu_unlock-style driver patches (host-side only); GSP-RM is closed-source, so
     building "your own" GSP firmware is only possible as (1) patch+resign (needs key) or
     (2) a from-scratch RISC-V RM loaded through the same verified channel (needs key or
     bypass) or (3) abandoning GSP-RM for bare-metal bring-up (SLM-OS direction), which
     currently stalls at the SEC2 priv-lock raised by BSI after FLR, not at signature
     checks. [CITED: SLM-OS doc]

Related surfaces worth watching (owner-lab framing):
- **FWSEC in VBIOS** is the HS stage before the driver exists on pre-Hopper — vBIOS
  flashes are the *real* firmware-trust boundary consumers can touch, and it feeds FRTS/SB.
- **WPR meta fields** (signature address/size, revision) are driver-controlled inputs to
  the verifier — malformed-metadata handling inside the booter/FMC is a natural fuzz
  target [SPECULATIVE].
- **CC mode** adds SPDM + a separate `CcFmcGfw` image set; the GPU-CC paper
  ([arXiv:2507.02770](https://arxiv.org/pdf/2507.02770)) maps that stack.

---

## 6. Debug vs production mode

[DECODED]
- `kgspIsDebugModeEnabled_TU102/GA100/GB100` read **`NV_FUSE_OPT_SECURE_GSP_DEBUG_DIS`**
  (GB100: `gpuGetPrimaryFuseBaseAddr() + NV_FUSE_ZB_OPT_SECURE_GSP_DEBUG_DIS`) — "debug
  mode" = the secure-GSP-debug fuse is **not** blown.
- Debug mode switches bindata selection: `*_dbg` vs `*_prod` for every stage — booter
  (`g_booteruc_load_tu10x_{dbg,prod}`), GSP-RM boot image (`g_gsprm_skbl_{dbg,prod}_libos3_*`),
  FMC (`GspRmFmcGfw{,Cc}{Debug,Prod}Signed`), and monolithic-RM inst-in-sys images.
- CC enabled + debug → some combos return NULL (unsupported). [DECODED:
  `kfspGetGspUcodeArchive`]
- There is no runtime "skip verification" switch in the driver; the debug/prod split is
  about **which key** the on-GPU verifier accepts, not whether it verifies. [INFERRED]

---

## 7. nvflash / OMGVflash / NVflashk — scope and limits

- **What they bypass (vBIOS only):** nvflash's pre-flash checks — PCI device ID, PCI
  subsystem ID, board ID, hierarchy/metadata ("mismatch bypass" force-enabled).
  [CITED: [nvflashk README](https://github.com/B47741/nvflash)]
- **Actual vBIOS signature modification** (flashing a *modified* image) is reported
  working **through Turing only**; from Ampere on you can cross-flash *unmodified signed*
  ROMs — modified ones are rejected by the GPU itself ("ERROR: Invalid firmware image
  detected."). [CITED: [TechPowerUp article](https://www.techpowerup.com/312631/nvidia-bios-signature-lock-broken-vbios-modding-and-crossflash-enabled-by-groundbreaking-new-tools) — "vBIOS signature check bypass works up to RTX 20-series"; nvflashk "Not yet tested: unsigned/modified BIOSes"]
- Tools: **OMGVflash by Veii** (TPU thread v5.780, incl. `--gpumode` experiments) and
  **NVflashk by Kefinator** (5.814.0.k1). Neither interacts with `gsp_*.bin` or the GSP
  boot chain. [CITED: TPU article/threads]
- **`--fsoff`:** could not be found in any public nvflash documentation checked
  (mvktech 2026 nvflash reference, LaptopJudge flags article, nvflashk/OMGVflash docs,
  two search engines). It is not part of the documented flag set (`--list/--version/
  --save/-6/--protectoff/--compare/--verify`). If it exists, it is build-specific.
  Working hypotheses to check offline against the actual binary's `strings`:
  (1) "flash **s**ector **off**set" — override of the ROM write offset;
  (2) related to the falcon-ucode partition offset inside the ROM (the FWSEC/BOOT
  partition that FWSEC-SB is read from). **[VERIFY — unresolved]**. The *security* checks
  that matter for GSP are not in nvflash's control path either way.

---

## 8. Open questions / VERIFY list

- [ ] `.fwsignature` header field semantics (12? 0x101? 0x8c8?) — extract the Booter or
      FMC binary from r615 bindata (zlib'd in `g_bindata_*.c`) and disassemble the
      signature-blob parser (envydis falcon / Ghidra RISC-V).
- [ ] Confirm ECDSA-P384 on GB100/GB202/GR100 (97-byte key = uncompressed point + 96-byte
      r‖s) vs RSA-3K on GH100/GB10B/GB20B — check FSP-side code if it ever ships in
      open-gpu-kernel-modules, or the COT message doc.
- [ ] What exactly the 4 signature slots hash (per-slot selection by fuse version?
      hash of ELF vs hash of archive manifest?).
- [ ] `--fsoff` semantics (get an nvflash binary and dump its help/strings).
- [ ] Whether GB202 consumer SKUs use the FSP path in the field (FSP HAL exists, but SEC2
      COT HAL also exists — board/IFR dependent?).
- [ ] Does any public RE of the Booter (falcon disassembly) exist? None found (2026-10-20).

## Sources

Local (this repo / vendored r615):
`g_kernel_gsp_nvoc.h`, `kernel_gsp.c` (`_kgspCreateSignatureMemdesc`, container parsing),
`kernel_gsp_tu102.c`, `kernel_gsp_gh100.c`, `kernel_gsp_booter.c`, `kernel_gsp_fwsec.c`,
`kern_fsp_gh100.c`, `kernel_sec2_gb20b.c`, `gspifpub.h` (`GSP_FMC_BOOT_PARAMS`),
`gsp_fw_wpr_meta.h`, `rmRiscvUcode.h`, `nouveau/extract-firmware-nouveau.py`,
`g_bindata_*FmcGfw*_{GH100,GB100,GB10B,GB20B,GB202,GR100}.c`,
`firmware-store/gsp/615.71.09/*.bin`, `firmware-store/gsp-history/ga102/*.bin`.

Web:
[nova falcon](https://docs.kernel.org/gpu/nova/core/falcon.html) ·
[nova fwsec](https://docs.kernel.org/gpu/nova/core/fwsec.html) ·
[nova fsp](https://docs.kernel.org/gpu/nova/core/fsp.html) ·
[nova booter.rs](https://github.com/torvalds/linux/blob/master/drivers/gpu/nova-core/firmware/booter.rs) ·
[Falcon-Security (open-gpu-doc)](https://download.nvidia.com/open-gpu-doc/Falcon-Security/1/Falcon-Security.html) ·
[SLM-OS nvidia-gsp.md](https://github.com/SLM-OS/SLM-Operating-System/blob/main/docs/nvidia-gsp.md) ·
[nvflashk README](https://github.com/B47741/nvflash) ·
[TPU: signature lock broken](https://www.techpowerup.com/312631/nvidia-bios-signature-lock-broken-vbios-modding-and-crossflash-enabled-by-groundbreaking-new-tools) ·
[TPU OMGVflash thread](https://www.techpowerup.com/forums/threads/omg-vflash-fully-patched-nvflash-from-x-to-ada-lovelace-v5-780.312601/) ·
[mvktech nvflash reference](https://www.mvktech.net/nvflash-guide/) ·
[NVIDIA driver README GSP chapter](https://download.nvidia.com/XFree86/Linux-x86_64/555.42.02/README/gsp.html) ·
[GPU-CC security paper](https://arxiv.org/pdf/2507.02770)

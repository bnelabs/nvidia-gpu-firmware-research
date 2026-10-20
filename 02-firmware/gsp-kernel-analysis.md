> REFERENCE / HISTORICAL REPORT — not a hardware runbook. Current [CONSTITUTION](../CONSTITUTION.md) and [CORRECTIONS](../CORRECTIONS.md) override this material. Offline decompilation and RE remain authorized. Hardware recipes, bench exceptions and blanket complete/safe claims below are superseded; other literature claims have not all been independently revalidated.

# GSP kernel corpus — extraction + first census (2026-10-16, packet C/D support)

Method (reproducible): `inventory_firmware.py` → embedded-ELF candidates → complete extraction
by computed size (`e_shoff + e_shnum × e_shentsize`) → per-file census. Binaries gitignored;
hashes in `firmware-store/gsp-kernels/SHA256SUMS` (+ per-file JSON in `firmware-store/inventory/`).

## 615 (gsp_ga10x.bin) — 12 embedded ELFs, all extracted completely

| Index | Size | Libos strings | Role (status) |
|---|---|---|---|
| 01 | 184,528 | 17 | family kernel (Libos) — order hypothesis: ga10x [VERIFY] |
| 02 | 205,008 | 18 | family kernel — gh100 [VERIFY] |
| 03 | 213,200 | 18 | family kernel — gb10x [VERIFY] |
| 04 | 184,528 | 18 | family kernel — gb10y [VERIFY] |
| 05 | 213,200 | 18 | family kernel — gb20x [VERIFY] |
| 06 | 213,200 | 18 | family kernel — gb20y [VERIFY] |
| 07 | 213,200 | 18 | family kernel — **gr10x [VERIFY]** |
| 08/09/12 | 41–57 KB | 0 | small non-Libos images (unmapped) |
| 10 | 17,305,752 | 0 | **GSP-RM payload** (application, not kernel) |
| 11 | 737,392 | 1 | unmapped |

All 12 md5-distinct. Family kernels share the Libos v3.1.0 string set; sizes cluster
(184,528 / 205,008 / 213,200) — same-kernel-different-arch with real per-arch differences.

## 535 (gsp-535.113.01.bin) — 5 embedded ELFs

| Index | Size | Libos strings | Status |
|---|---|---|---|
| 01/02 | 135,224 (×2, same size) | 0 | booter-class images (unmapped) |
| 03 | 605,688 | 0 | unmapped |
| 04 | 13,767,200 | 2 | GSP-RM payload |
| 05 | 1,132,000 | 3 | Libos-era image (unmapped) |

**Open**: the 535-era family-kernel mapping does not follow the 615 layout (no ~200 KB
Libos-kernel-size match). Resolution path: decode the archive directory via
`nouveau_firmware_layout.ods` + loader consumers (REA task), or extract from the 535 driver's
own loader source (r535 branch). Do NOT infer the mapping from sizes.

## Functional-diff groundwork (next)
Matched-routine baseline: the Libos `sbi.c` assertion call site exists in 615-kernel-01
(string @paddr 0xc230). 535 counterpart image not yet identified — blocked on the mapping
above. r2 (6.0.7) analysis + REA decompiler output are to be treated as hypotheses per
RESEARCH-DIRECTION.md.

## Loader-side family mapping — SOURCE-DECODED (2026-10-16, round 26)

`vendor/open-gpu-kernel-modules/src/nvidia/arch/nvalloc/common/inc/nv-firmware-chip-family-select.h`
(pinned commit ca2d03e) — `nv_firmware_get_chip_family(gpuArch, gpuImpl)`:
- Turing → TU10X/TU11X; Ampere → GA100/GA10X; Ada → AD10X; Hopper → GH100
- Blackwell GB1XX: impl == GB10B → **GB10Y** else GB10X; GB2XX: impl >= GB20B → **GB20Y** else GB20X
- **RUBIN_GR1XX → GR10X** — the loader explicitly selects a GR10X firmware family

Status upgrade: family names in the container archive (`kernel_<family>.elf`) are now
**source-decoded** anchors (not just observed strings). Still [VERIFY]: the storage-order
hypothesis for the 7 extracted kernel ELFs (needs the archive directory-walk code — the
container-internal table at payload ~16 KB — or the closed loader half), and this proves
family-level firmware packaging exists, NOT a shipping consumer Rubin SKU.

Also source-decoded: firmware "tasks" packaged per family — INIT, RM, INTR, VGPU, MNOC,
DEBUG, ROOT, RM_STATE_MONITOR (`nv_firmware_task_t`) — matching the multi-ELF structure
we extracted (kernel + RM + small task images).

## Matched-routine diff - first attempt status (2026-10-16)

- Anchor chosen: shared RM assertion `(pSingle1x->softFloor.clkPropTopIdx != NV2080_CTRL_CLK_CLK_PROP_TOP_ID_INVALID)` - present in BOTH payloads (615 @file 0xebeb00; 535 @file 0xcacb98); 1,298 strings shared overall.
- Function census (r2 default analysis): 615 RM = 1,538 functions; 535 RM = 1,550.
- **Blocked**: xref-to-function resolution requires the RM ELF's virtual-address mapping for .rodata (izz reports vaddr==paddr; code references use lui/addi pairs). Precise next step: program-header-based vaddr mapping, then axt per anchor - REA/IDA tooling or manual phdr walk. No function-level claim committed.

## REA/IDA capability boundary + manual xref stop (2026-10-16, round 6)

- REA server v6.5.0 LIVE; IDA 9.4 container bound (libnvidia-ml.so decoded successfully - x86-64). **But no REA lane admits the RISC-V RM payloads**: IDA adapter = "no verified RISC-V lane"; Ghidra lane requires EF_RISCV double-float ABI (ours is soft-float); Hopper rejects RISC-V. Capability matrix updated accordingly.
- Manual lui/addi resolver (scripts/riscv_xref.py): found the softFloor anchor reference in the 535 payload (file 0x93ed2c, rd=x15) but 0 references in the 615 payload across 3 additional anchors + the original. Second failed approach -> stop rule applied.
- Precise blocker named: the 615 RM payload references .rodata through an unresolved pattern (different pairing/base scheme or relocation-style). Prerequisite for the functional diff: a RISC-V-capable decompile lane (Ghidra with a soft-float language spec, or IDA RISC-V support in a future REA adapter) or manual disassembly of the reference sites.
- No function-level diff committed; the blockage is recorded, not hidden.

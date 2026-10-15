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

# GSP diffing lab — first results (2026-10-15)

Corpus (hashes in `firmware-store/**/SHA256SUMS*`; binaries gitignored):
- `gsp-535.113.01.bin` (38,061,600 B, linux-firmware copy)
- `gsp-570.144.bin` (63,571,696 B, linux-firmware copy)
- `gsp_ga10x.bin` @615.71.09 (27,043,992 B, rig's own installed image)

## 1. Container format — verified by inspection

The shipped `gsp_*.bin` is a **tiny outer ELF wrapper** (RISC-V relocatable, `not stripped`)
whose payload sections are the real content:

| Section | Meaning |
|---|---|
| `.fwimage` | the actual firmware image — raw RISC-V code (boot prologue visible: `auipc/addi`), ~27 MB @615 |
| `.fwversion` | NUL-terminated driver version string — **`615.71.09`** (self-identifying; matches rmctl + nvidia-smi) |
| `.fwsignature_<arch>` | per-chip-family signed blobs |
| `.symtab` | 4 entries — only `_binary_..._ga10x_firmware_bin_{start,end,size}` markers, which leak NVIDIA's Perforce build path: `//dvs/p4/build/sw_rel/gpu_drv/r615/r616_69/drivers/resman/build/gsp/_out/Linux_amd64/release/LibOS/riscv64/release/firmware/ga10x_firmware.bin` |

Extraction recipe (objcopy lacks RISC-V support here — use byte-exact dd):
```bash
OFF=64; SZ=$((0x19be000))            # readelf -SW → .fwimage Off/Size
dd if=gsp_ga10x.bin of=/tmp/fwimage.bin bs=1M skip=$OFF count=$SZ iflag=skip_bytes,count_bytes
```
⚠️ `file` misidentifies the payload ("OpenPGP Secret Key" — magic heuristic); it is raw RISC-V
boot code + packed sub-archives. The official container-format documentation and a converter
("OpenRM binhex → Nouveau/Nova blobs") ship inside open-gpu-kernel-modules:
`vendor/open-gpu-kernel-modules/nouveau/{extract-firmware-nouveau.py, nouveau_firmware_layout.ods}`.

## 2. Signature-section timeline — chip-family support as data

| Driver image | `.fwsignature_*` sections | Interpretation |
|---|---|---|
| 535.113.01 | ga10x, ad10x, gh100 (+cc_gh100) | Ampere/Ada/Hopper era |
| 570.144 | + gb10x (+cc_gb10x), gb20x | **Blackwell added** |
| 615.71.09 | + gb10y, gb20y (+cc_gb20x), **gr10x** (+cc_gr10x) | **Rubin signatures already present**; gb20y/gb10y = new die variants |

Section counts grew 10 → 14 → 19. The 615 container can therefore service Ampere → Rubin from a
single file — and `gr10x` is the first **hard artifact evidence** for next-gen support (feeds
01-generations/rubin.md). `cc_` prefix = likely "code checking"/debug-signed variants [VERIFY].

## 3. Inside `.fwimage` — first strings

Internal source paths survive in the image:
`/gpu_drv/uproc/os/libos-v3.1.0/src/common/nvriscv-2.0/sbi.c` — the GSP runs NVIDIA's **Libos
microkernel v3.1.0** on an nvriscv-2.0 core, with assertion strings intact (`Runtime failure: a0
== 0 @ ...sbi.c:%d`). Assertion/trace strings = free telemetry for behavior diffing across
versions.

## 4. Next steps (P2)

- [ ] Parse the container per `nouveau_firmware_layout.ods` (script: unpack bootloader / RM /
      libos sub-archives; check gzip/zlib compression) → per-sub-image symbol tables
- [ ] Run the same extraction on 535/570 payloads → first functional diff (new symbols/strings
      per version; RPC message tables live in the RM sub-image)
- [ ] Extend corpus via `.run` extraction (more versions per branch) — `fetch_gsp.sh` ready
- [ ] Feed interesting symbol names into rmctl control mapping (closed CLK/FAN/VOLT families
      live in this image — symbol names may reveal handler naming conventions)

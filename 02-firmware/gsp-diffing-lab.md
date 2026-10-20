> REFERENCE / HISTORICAL REPORT — not a hardware runbook. Current [CONSTITUTION](../CONSTITUTION.md) and [CORRECTIONS](../CORRECTIONS.md) override this material. Offline decompilation and RE remain authorized. Hardware recipes, bench exceptions and blanket complete/safe claims below are superseded; other literature claims have not all been independently revalidated.

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

## 5. Payload strings-diff: 535 → 615 (first functional diff)

`strings -n 10` unique sets: 535 = 4,932; 615 = 4,163; **2,020 strings new in 615** (proper
`LC_ALL=C sort` + `comm -13`; note: strings sets shrink because 615 reorganized/compressed
content — diff direction still valid).

Headline findings:

1. **Per-arch kernel archive directory** sits near the payload start (offset ~16 KB):
   `kernel_{ga10x,gh100,gb10x,gb10y,gb20x,gb20y,gr10x}.elf` — and the names repeat right before
   the first embedded ELF (0x6A000). **Each chip family ships its own GSP kernel ELF inside the
   one container** — the four embedded stripped RISC-V ELFs found at 0x6A000/0x97000/0xC9000/
   0xFD000 are these kernels. `kernel_gr10x.elf` = a **Rubin GSP kernel image inside shipping
   consumer firmware**.
2. **Voltage-control vocabulary expanded 4 → 9 strings**: `OVERVOLTAGE_{IODVDD,NVVDD,MSVDD(+_0/_1)}`,
   `EnableCoreVoltage`, `OVERVOLTAGE_LOGIC` — the GSP RM manages explicit voltage rails
   (NVVDD/MSVDD are the core rails, IODVDD the I/O rail). Combined with mVolt+ runtime power
   bypass (vbios.md), this is the firmware-level control vocabulary for power/voltage.
3. Clock/fan/thermal surface: `EnableMClkSlowdown`, `MCLK_LIMIT`, `MCLK_MAX_CAPABILITY`,
   `MIN_FAN_LEVEL`, `MXM_ACPOWER`, `NETIR_THERMAL_EVENT`.
4. An embedded **NLS Root CA certificate (valid 2024-09-19 → 2049)** — NVIDIA Licensing Service
   trust anchor inside GSP firmware (attestation/licensing path — fuels the secure-boot questions
   in prior-art.md "unexplored angles").
5. `rm.bindata.bin`, `gsp_cpu_{dma,replayable_fault,non_replayable_fault}` — bindata archive
   format + CPU fault-handling telemetry names.

## 6. Kernel archive table — partial decode (2026-10-15, round 10)

Entry layout (stride 160 B, first entry @ payload 0x69014, name at +16, then u64 descriptors):
- VA1 `0xffffffff92fff000` + VA2 `0xffffffffa3000000` — match **every kernel ELF's LOAD VAs**
  (all 7 kernels: EXEC, entry `0xffffffff93000000`, statically linked, **stripped**, RVC).
- Descriptor fields per entry: (offset, size, count) triples + small ints — loader patch tables;
  exact semantics live in `nouveau_firmware_layout.ods` [VERIFY next].
- All 8 early embedded ELFs are **distinct binaries** (md5s recorded; 7 kernels + 1 other,
  the 8th @0x1C6000 has a different entry point 0x10027cc — likely libos/bootloader [VERIFY]).
- **Validation attempt (2026-10-15, round 11): md5 matching FAILS** — zero common hashes between
  570's 6 early ELFs and 615's 8, i.e. **GSP kernels are rebuilt for every driver release**
  (firmware churns with each driver, even for unchanged chip families). Mapping validation must
  go through the ODS layout decode [VERIFY — gr10x @0x192000 remains a hypothesis, not a fact].
- Note: a second name list earlier in the payload (~16 KB) lists the same kernels in REVERSE
  (newest-first: gr10x…ga10x) — two tables, two orders; the one adjacent to the ELF blob is
  the loader table [VERIFY].

## Next steps (P2, updated)

- [ ] Extract `kernel_gr10x.elf` + `kernel_gb20x.elf` via the archive directory (parse name→
      offset table at ~16 KB) → keep per-arch kernels for cross-family diff
- [ ] Diff GSP-RM config vocabulary (bindata names) 535 vs 615 in full (the 2,020 new strings)
- [ ] Same treatment for `.fwsignature_gr10x` blob → signature format RE (falcon auth chain)

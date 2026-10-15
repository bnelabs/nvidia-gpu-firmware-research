# vBIOS lab — BIT directory parsed (2026-10-15)

## Corpus
- `evga-3090-94.02.42.00.0F.rom` (999,424 B) — EVGA RTX 3090, same BIOS family as the rig's
  `94.02.42.00.F4`. Source: [bmgjet/EVGA-Bios-Unpacker](https://github.com/bmgjet/EVGA-Bios-Unpacker)
  (extracted from EVGA Update.exe); also available via the
  [TechPowerUp VGA BIOS DB](https://www.techpowerup.com/vgabios/?model=RTX+3090).
  sha256 recorded in `firmware-store/vbios/ga102/SHA256SUMS` (binary gitignored).

## Findings
1. **The EVGA download is wrapped**: file starts with `NVGI` magic (updater container, ~36 KB
   header). The real option ROM (`55 AA …`, PCIR) begins at file offset **0x9200**.
   The parser auto-locates it.
2. **PCIR**: vendor `0x10de`, device `0x2204` (GA102 RTX 3090), code type 0 (x86 legacy image).
   Multiple 55AA/PCIR pairs exist (0x9200, 0x19000, …) = the multi-image ROM (x86 + UEFI).
3. **BIT directory decoded** at ROM-relative 0x1b2, header 16 bytes, token = {u8 id;
   u16 loc BE; u16 size BE; u8 ver}:

```
 id  token       location     size  ver   target(abs)   preview
  B  BIOSDATA    0x000225  0x0003e   2    0x009425
  C  (data)      0x00022c  0x00063   2    0x00942c
  D  display?    0x000104  0x0008f   2    0x009304      "GPU Board…"
  I  NVINIT      0x000124  0x00093   2    0x009324      "Chip Rev …"
  M  MEMORY      0x000229  0x000b7   2    0x009429
  N  (end-mark)  0x000000  0x00000   0
  P  PERF        0x0002e8  0x000e0   2    0x0094e8      fc 93 06 00 …
  S  (data v3)   0x000218  0x000c8   3    0x009418      0d 00 fb 03 …
  T  thermal?    0x000102  0x000e0   3    0x009302      ff ff "GPU Board"…
```

4. **Parser semantics that cost a debugging round** (documented for reuse):
   - token stream does NOT end with a zero id — it stops when the next byte isn't a known
     token character (a following table begins immediately);
   - header_size=16 (not 10–13), locations are **big-endian**, ROM-relative;
   - 'N' with zeros appears mid-table (end-marker-style entry) with more tokens after it.
5. Next token 'P' (PERF, 0xe0 bytes @0x2e8) is the power/performance table — the blind hex-edit
   target of community guides. Now locatable *by name* — enabling proper structured edits via
   the official spec (SOURCES: NVIDIA BIOS-Information-Table).

## Next
- [ ] Dump+decode the P/PERF table substructure per spec (power limits, clk/vf curve entries)
- [ ] Fetch the FE 3090 ROM (TPU 231642) + partner variants → partner-diff the P tables
- [ ] Locate 'M' MEMORY strap table + 'p' falcon-ucode tokens (absent in this legacy image?
      — check the UEFI image at 0x19000 for a second BIT)

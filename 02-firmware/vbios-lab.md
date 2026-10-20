> REFERENCE / HISTORICAL REPORT — not a hardware runbook. Current [CONSTITUTION](../CONSTITUTION.md) and [CORRECTIONS](../CORRECTIONS.md) override this material. Offline decompilation and RE remain authorized. Hardware recipes, bench exceptions and blanket complete/safe claims below are superseded; other literature claims have not all been independently revalidated.

# vBIOS lab — BIT directory parsed (2026-10-15)

## Current interpretation (reviewed 2026-10-16)

Sections 1–5 below preserve early, superseded notes: the 16-byte header and big-endian
claims are incorrect. Section 6 also incorrectly labels 16-bit token fields BE: the parser
uses **little-endian** size and pointer fields. Current parser validates the header checksum,
uses the header PCIR pointer and image lengths, and applies the UEFI adjustment to targets.
All four local corpus ROMs pass `--perf`; seven synthetic regression tests pass offline.
Re-run earlier table comparisons before relying on their conclusions. A NULL legacy
PowerControlTable pointer does not establish where runtime power policy executes.
The named PERF prefix has 40 fields; remaining entries are reported as unknown `fieldN`.

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

## 5. Variant & cross-SKU diffs (2026-10-15, round 13)

Corpus (hashes committed): EVGA 3090 variants `94.02.42.00.{0B,0F,44}` + EVGA 3080
`94.02.26.40.BE` (all 999,424 B, from the bmgjet repo).

1. **Same-family EVGA variants are nearly identical**: across `0B/0F/44`, every named BIT table
   differs by ≤1 byte; total ROM-region diff = 172 bytes (clusters at 0x92ce, 0x9442, 0x960c,
   0x9650-0x965f, 0x18fff, 0x8706b, 0x8cf0c, 0x8d9xx, 0x8f3ff, 0xf201b-0xf20a9 [143 B block]).
   → EVGA point-releases change metadata/small config, NOT the P/PERF table.
   **Partner-diff for power-limit hunting needs cross-AIB samples, not point releases.**
2. **Cross-SKU (3090 vs 3080, same GA102)**: BIT layout *identical* (same offsets/sizes/versions)
   — the format is stable across the family. Differences live in the data:
   - P table first u32: 3090 `0x000693fc` vs 3080 `0x000684d2` (semantics TBD — clock/
     capability-ish values)
   - B (BIOSDATA) and M (MEMORY) carry per-board bytes (`04 74 3f 18 7e fd 84 20 85` vs
     `04 a4 3f 48 7e 52 85 70 85`)
   - PCIR device: `0x2204` (3090) vs `0x2206` (3080) ✓
3. TechPowerUp download note: TPU serves an HTML form for `?download` (no direct GET) — corpus
   growth from TPU needs the form flow or a browser; GitHub-hosted corpora are script-friendly.

## 6. Spec-accurate BIT decode + PERF chain walk (2026-10-15, round 14)

Parser rewritten per the official [BIOS-Information-Table spec](https://download.nvidia.com/open-gpu-doc/BIOS-Information-Table/1/BIOS-Information-Table.html):

- Header (12 B): `[u16 ID=0xB8FF][BIT\0][u16 BCD=0x0100][u8 hdr=12][u8 tok=6][u8 entries=17][u8 cksum]`
  — our earlier "16-byte header / BE locations" reading was wrong: token = **{u8 id; u8 ver; u16 size BE; u16 ptr BE}** (version and pointer positions swapped vs my first guess).
- All 17 tokens decoded by name (I2C, BIOSDATA v2, CLOCK v2, DFP, NVINIT, MEMORY v2, NOP,
  **PERF v2 (232 B)**, STRING v2, TMDS, DISPLAY, VIRTUAL, MXM, DP, **FALCON_DATA v2**, UEFI, + undocumented 0x69).
- **PERF_PTRS v2 walked** (58 u32 fields): Performance/MemoryClock/MemoryTweak/Thermal*/Power*/
  Fan*/Voltage*/LowPower*/Overclocking tables all located.
- **UEFI pointer-adjustment rule validated**: pointers > legacy length (0xFE00) get + UEFI length
  (0x16600); every adjusted table then starts with a sane structured header (e.g. PowerPolicy
  `30 2c 47 14…`, ThermalDevice `10 04 0b 12…`). Voltage tables (ptr < legacy) need NO adjustment.
- **Notable: PowerControlTable pointer is NULL on this Ampere image** ([3] = 0) — power policy
  lives in PowerPolicyTable/PowerSensorsTable/PowerTopologyTable; consistent with power
  management having moved into the GSP (see gsp-firmware.md).
- Raw u32 scan for watt-like values (300k–470k) is too noisy to pin limits; exact power-limit
  fields need the dedicated PERF-tables spec (open-gpu-doc) — next round.
- One exact **350000 (350 W)** u32 found @file 0x3c9e0 (region between UEFI end and adjusted
  PERF area) — candidate default-power-limit encoding in mW [VERIFY].

## 7. Table-content observations (round 15 — leads, each [VERIFY] pending structure spec)

- **OverclockingTable** (0xe8-size region @adj 0x8f247): header `10 07 05 02 05 02 00 01`;
  u32 `c8 af 00 00` = 45,000 (min-clock or power floor?); @+23: u32 **0x001D4C00 = 1,920,000 KHz
  = 1,920 MHz** — plausible OC boost ceiling (3090 stock boost 1,695); @+26: 0x81000 = 528,384
  KHz. Structure matches the community "OC table" that OC Scanner / -lgc consume.
- **PowerSensorsTable**: header `20 08 3d 07` — v2.0, 8 sensors, `0x073d` = 1,853 (power scale
  mW/LSB candidate); byte fields `1e 19 78 3e` look like INA3221-style rail config (the 3090
  monitors its 12V rails via INA3221 — cross-check with hardware telemetry [VERIFY]).
- **FanCoolerTable**: u16 sequence `f4 01 d0 07 85 0b 88 13` = **500 / 2,000 / 2,949 / 5,000**
  — min/max RPM + duty values; `64 00` = 100 (% duty). This is the fan-curve source the
  driver/NVML fan controls read.
- General: these v2 PERF subtables carry their own {version, size, entry-count} headers
  (`10/20/30` first bytes observed) — same self-describing style as the BIT itself.

## Next
- [ ] Dump+decode the P/PERF table substructure per spec (power limits, clk/vf curve entries)
- [ ] Fetch the FE 3090 ROM (TPU 231642) + partner variants → partner-diff the P tables
- [ ] Locate 'M' MEMORY strap table + 'p' falcon-ucode tokens (absent in this legacy image?
      — check the UEFI image at 0x19000 for a second BIT)

## 8. Packet D first pass — table-attributed variant diffs (2026-10-16, corrected offsets)

EVGA 3090 variants `0B/0F/44`, diffs attributed via the fixed parser's adjusted table map
(method: cluster → containing table by [start, next-start) ranges; raw bytes retained):

| Cluster (file) | Table (+offset) | 0B | 0F | 44 | Reading (hypothesis) |
|---|---|---|---|---|---|
| 0x8cf0c (3B) | PowerPolicyTable +0xc4 | `d0 dd 06 00` | `40 ef 07 00` | `d0 dd 06 00` | u32 mW: **450,000 vs 520,000** — per-variant power value (0F = EVGA 520 W-class model candidate) |
| 0x8d9ad | FanPolicyTable +0x46 | `26 64` | `37 64` | `3c 64` | fan duty % + 100 cap (38/55/60 %) — per-SKU cooler curves |
| 0x8d9b6 | FanPolicyTable +0x4f | `78 05` | `08 07` | `08 07` | u16 (1400 / 1800) — RPM candidate |
| 0x8f3ff | OverclockingTable +0x1b8 | `e0` | `ff` | `60` | single byte, unknown |

Statuses: byte values = observed-bytes; the mW/duty readings = **hypothesis** (needs the
versioned table definitions or driver-consumer confirmation). Cross-checks queued: NVML-reported
limits per variant (bench), and the rig's own F4 vBIOS (not in corpus — read-only rule).
Consistency note: the mW encoding independently recurs in the live RM path (0x2080a61d →
370,000), supporting u32-mW as the family-wide unit [VERIFY per field].

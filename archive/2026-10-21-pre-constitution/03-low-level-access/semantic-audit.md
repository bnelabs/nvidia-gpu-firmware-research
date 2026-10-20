> HISTORICAL / SUPERSEDED. Not an authorized runbook. Claims may be retracted. Read current CONSTITUTION.md and CORRECTIONS.md at the repository root.

# Semantic decoder audit — every printed metric, with its contract

Per RESEARCH-DIRECTION.md ("semantic decoder audit" path). Each metric printed by our tools
gets a contract: command, field, type, units, encoding, selector/sentinel, source, status.
**Statuses**: source-decoded (struct + enum in pinned headers) / cross-validated (two
independent sources agree) / hypothesis / raw (unknown — printed, never interpreted).

Pinned header source: `open-gpu-kernel-modules` @ `ca2d03e6fafd4d4b56b383497d931c25b283bfcf`
(RESEARCH-DIRECTION.md). Deviations from pinned structs are decoder bugs.

## 1. rmctl (07-prototype/rmctl.c)

| Printed metric | Command | Field(s) | Type / units | Encoding & selector | Sentinel | Source | Status |
|---|---|---|---|---|---|---|---|
| `rm api version` | NV_ESC_CHECK_VERSION_STR (0xD2), 72 B | `versionString[64]`, `reply` | char[]; u8 | cmd='2' (QUERY) → RM copies its string; reply=1 RECOGNIZED | — | `osapi.c RmPerformVersionCheck` | source-decoded |
| `client/device/subdevice` | NV_ESC_RM_ALLOC (0x2B) NVOS64 | `hObjectNew` per class NV01_ROOT=0x0 / NV01_DEVICE_0=0x80 / NV20_SUBDEVICE_0=0x2080 | u32 handles | deviceId=0 selects GPU (ctl-fd alloc) | — | cl0000/0080/2080.h | source-decoded |
| `gsp.bValid` | 0x20803601 GET_FEATURES | `bValid` | u8 bool | 1 = RM is GSP client w/ offload | — | ctrl2080gsp.h | source-decoded |
| `gsp.bDefaultGspRmGpu` | 0x20803601 | `bDefaultGspRmGpu` | u8 bool | family default per chip-family select | — | ctrl2080gsp.h | source-decoded |
| `gsp.gspFeatures` | 0x20803601 | `gspFeatures` | u32 bitmask | bit0 UVM_ENABLED; **other bits raw** | — | ctrl2080gsp.h | bit0 source-decoded, rest raw |
| `gsp.firmwareVersion` | 0x20803601 | `firmwareVersion[0x40]` | char[] build string | filled iff offloaded | empty = not offloaded | ctrl2080gsp.h | source-decoded |
| `pmumon.samplesReturned` | 0x20801037 GET_SAMPLES | `super.numSamples` | u32 count (≤250) | in/out metadata, pass back unmodified | — | ctrl2080clk.h | source-decoded |
| `last gpcClk` | 0x20801037 | `samples[n-1].activeGpcClkFreqKHz` | u32 KHz | "programmed GPCCLK", PMU 20 ms cadence | 0xFFFFFFFF = SAMPLE_INVALID | ctrl2080clk.h | source-decoded; cross-validated vs nvidia-smi clocks (1665/1680 busy, 210 idle) |
| `perf.currPstate` | 0x20802068 GET_CURRENT_PSTATE | `currPstate` | u32 **one-hot** | `NV2080_CTRL_PERF_PSTATES_Pn = 2^n` (P0=1…P15=0x8000) | non-one-hot → printed raw | ctrl2080perf.h @ca2d03e | source-decoded; **cross-validated** (0x4=P2 busy, 0x100=P8 idle, both match nvidia-smi) |
| *(removed)* 0x2080014a "pstate" | — | — | — | — | — | — | **retracted**: identity/UUID getter (selector 2 in, UUID out); see LOG wave 3a |

## 2. decode_telemetry.py

| Metric | Contract |
|---|---|
| `pstate` | one-hot → ordinal via PSTATE_ONEHOT map; non-one-hot stays `raw(0x…)` |
| `gpc_clk_mhz` | KHz/1000; fixture value 210.0 idle |
| `gsp_features` | named bits + `unknown_bitN` preserved (unknown stays raw) |
| fixture provenance | device UUID/vBIOS, driver 615.71.09, pinned commit in JSON |

## 3. parse_vbios_bit.py

| Output | Contract |
|---|---|
| PCIR vendor/device | u16 LE @PCIR+4; image size u16 @+0x10 ×512 B; 0 = auto [spec §PCI Data Structure] |
| BIT header | ID 0xB8FF + "BIT\0"; hdr/tok sizes at +6/+7; entries +8; 0-checksum over HeaderSize bytes [spec] |
| tokens | {u8 id; u8 ver; u16 size LE; u16 ptr LE}, ptr ROM-relative; **ptr > legacy-img-len ⇒ + UEFI img len** [spec rule; parser uses LE - verified against reviewer-fixed source] |
| PERF_PTRS v2 fields | 58 u32 offsets in spec order (PerformanceTable … LowPowerNVLINK); NULL = absent (e.g. PowerControlTable = 0 on this Ampere image) |
| raw pointer targets | printed as file offsets + first bytes; **no field meaning inferred from magnitude** |

## 4. sniffer2 records

| Field | Contract |
|---|---|
| `shape` | nvos54 only if magic 'F' ∧ nr 0x2A ∧ _IOC_SIZE==32; else passthrough, no deref |
| `syscall_errno` vs `rm_status` | logged separately; RM status captured **only on successful ioctl** (failed syscall ⇒ -1, stale input not reported) |
| `full/captured/TRUNCATED` | capture bound SNIF_CAP_MAX=4096; full size from NVOS54+24 |
| `first_diff@+n` | pre/post byte diff of the caller's buffer; direction INOUT per API |

| `power candidate (+4)` | 0x2080a61d (CLOSED, undocumented) | 12 B: byte0-3 `01 fe 00 00`, u32 @+4 | mW **hypothesis** (370,000 observed live; fixture mirrors it) | selector unknown | - | observed-bytes + sniffer | hypothesis - needs versioned table spec or libnvidia-ml decode |

## Unknowns deliberately kept raw
- `gspFeatures` bits ≥ 1; PMUMON sample fields beyond activeGpcClkFreqKHz; PERF v2 subtable
  internals (PowerPolicy/Overclocking bytes); 0x00000d01 response layout (NVML getter path —
  offline decode queued); everything tagged `[VERIFY]` in the labs.

## Audit result
Contracts above are **proposed until this branch merges and fixtures cover them** (REVIEW
finding 6). Historical misprints (raw-4→"P4", 0x14a→"pstate") are corrected and retracted.
rmctl now validates PMUMON sample counts against capacity, reports the invalid-clock sentinel
as a sentinel, and propagates probe failures to the exit code (packet 1).

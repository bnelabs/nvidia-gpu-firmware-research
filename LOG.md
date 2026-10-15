# Research log (append-only)

## 2026-10-15 — wave 2d: spec-accurate BIT decode; PERF chain fully walked; table leads (Europe/Istanbul)
- Official BIT spec pulled; parser rewritten: header {0xB8FF, BIT\0, BCD, hdr=12, tok=6, 17, cksum},
  token {id, ver, size BE, ptr BE}; UEFI pointer-adjustment rule (+0x16600) validated on all
  PERF tables; Voltage tables need no adjustment.
- PERF_PTRS v2: 58 fields decoded by name (Power/Thermal/Fan/Voltage/LowPower/Overclocking).
- **PowerControlTable pointer NULL on Ampere** — power policy moved to GSP era (matches
  CLK/FAN/VOLT absence from open SDK).
- Table-content leads ([VERIFY]): OverclockingTable 1,920 MHz ceiling candidate; PowerSensors
  8 sensors + INA3221-style config; FanCoolerTable RPM values 500/2000/2949/5000.
- README repo map + SOURCES updated (official BIT spec added). Commits 7d7e798, 21-total.

## 2026-10-15 — wave 2c: vBIOS BIT parser working; cross-SKU diffs done (Europe/Istanbul)
- scripts/parse_vbios_bit.py: self-calibrating BIT parser (auto-carve NVGI wrapper, PCIR,
  token table). Debug lessons: hdr=16B, BE loc/size, stream ends at non-token byte.
- Corpus: EVGA 3090 x3 (94.02.42.00.{0B,0F,44}) + EVGA 3080 (94.02.26.40.BE); hashes committed.
- Same-family variants: ≤1 B/table diff (172 B total ROM-side) → point releases don't touch P/PERF.
- Cross-SKU: BIT layout identical across GA102 (3090/3080); P first-u32 + B/M carry per-SKU data.
- Next: P/PERF substructure per official spec; cross-AIB samples (TPU needs form flow — noted).

## 2026-10-15 — wave 2b: kernel archive table decoded ~80%; 7 distinct per-arch kernels (Europe/Istanbul)
- Entries (stride 160 B @ payload 0x69014): name + VA descriptors matching kernel LOAD VAs
  (0xffffffff92fff000 / 0xa3000000); loader patch triples; exact semantics in layout ODS [VERIFY].
- 8 embedded ELFs md5-fingerprinted: 7 unique per-arch kernels (ga10x…gr10x hypothesized order,
  ELF @0x192000 = gr10x candidate) + 1 different image (0x1C6000, entry 0x10027cc).
- Validation path: decode via nouveau_firmware_layout.ods, or diff vs 570 container (only
  gb10x/gb20x kernels → new families pin the mapping).
- gsp-diffing-lab.md §5–6 updated; commits 892eed2, 3b4ad3b.

## 2026-10-15 — wave 2a: GSP container decoded; Rubin signatures found in shipping firmware (Europe/Istanbul)
- Corpus: 535.113.01 (38.0 MB) + 570.144 (63.6 MB) from linux-firmware + rig's 615.71.09 (27.0 MB).
- **gsp_*.bin = tiny outer ELF wrapper** (.fwimage raw RISC-V / .fwversion self-id / .fwsignature_<arch>).
- Signature timeline: ga10x+ad10x+gh100 (535) → +gb10x/gb20x (570) → +gb10y/gb20y/**gr10x** (615).
  → 615's single file services Ampere→**Rubin**; first hard artifact for the RTX-60 watchlist.
- Symtab leaks Perforce path //dvs/p4/build/sw_rel/gpu_drv/r615/r616_69/...; .fwimage carries
  Libos v3.1.0 / nvriscv-2.0 assertion strings (microkernel identified).
- objcopy lacks RISC-V here → byte-exact dd recipe documented; `file` heuristic misfires (documented).
- Official container docs located in-tree: nouveau/extract-firmware-nouveau.py + layout ODS.
- 02-firmware/gsp-diffing-lab.md written; next: unpack sub-archives per ODS, functional diff.

## 2026-10-15 — wave 1e: userspace-control.md authored by parent; WAVE 1 COMPLETE (Europe/Istanbul)
- Userspace agent silent 4+ hours with no file → declared stalled; parent authored
  03-low-level-access/userspace-control.md from wave-1 verified material + rig facts
  (sanctioned-surface cheat-sheet, NVML snippet, NvAPI/Coolbits, RM-control mapping table,
  mVolt+ lead). If the agent delivers later, merge rather than overwrite.
- Wave 1 (P1) now complete: 6/6 topics delivered across 13 research files, all cited.
- Cross-file leads captured for P2/P3: mVolt+ runtime power programming; InfoROM as the
  likely persistence store for memory-training results [VERIFY]; GSP-as-ELF parsing via
  NV-GSP-Bootloader / airlied-gsp-parse; LHR prior-art corrections.

## 2026-10-15 — wave 1c: 🎯 rmctl v0.3 WORKS END-TO-END (Europe/Istanbul)
- Built a from-scratch userspace RM client (07-prototype/rmctl.c, public headers only) and ran
  it READ-ONLY against the production rig: version handshake → client/device/subdevice alloc →
  NV2080_CTRL_CMD_GSP_GET_FEATURES. Result: gsp.bValid=1, bDefaultGspRmGpu=1,
  firmwareVersion="615.71.09" — cross-validated with nvidia-smi XML + on-disk gsp_ga10x.bin.
- Working recipe documented in 07-prototype/rmctl-notes.md: _IOWR('F', esc, struct) encoding,
  NVOS64 for ALLOC (48 B), all allocs on nvidiactl (deviceId selects GPU), version QUERY cmd='2'.
- Debug method: strace diffing of nvidia-smi vs our binary (ioctl _IOC triples).
- Impact: Technique T3 is now PROVEN, not just plausible — the documented RM control surface
  (ctrl2080{fan,perf,power,thermal,volt,clk}) is reachable from userspace with no patching.
  Next (P3): enumerate read-only controls (clocks/thermal/infoROM) into an rmctl query mode.

## 2026-10-15 — wave 1b: firmware + kernel files landed; rmctl v0.1 compiles (Europe/Istanbul)
- Delivered: 02-firmware/gsp-firmware.md (2,675 words), 02-firmware/vbios.md (~3,530),
  03-low-level-access/kernel-drivers-and-registers.md (2,801), 04-tools/tools-inventory.md (32 tools).
- **rmctl v0.1 (07-prototype/) compiled clean against vendored r615 headers** — allocates
  client/device/subdevice, probes NV2080_CTRL_CMD_GSP_GET_FEATURES (read-only).
- Register-doc coverage corrected (agent audit): open-gpu-doc has NO Ada/Blackwell manuals;
  GA102 = 7 units vs GA100 = 17; README/TECHNIQUES fixed.
- GSP naming history: gsp.bin → tu10x+ad10x @r525.53 → ga10x rename @r530.30.02; r615 adds
  ucodes_*.bin; gsp_ga10x.bin carries Ampere+Ada+Blackwell consumer; GB202 linux-firmware =
  bootloader+fmc only (FMC-first boot, nova era).
- FINN interface IDs for future RPC work: CLK=0x208010, THERMAL=0x208005, POWER=0x208027.
- Security: GPUBreach (2026) — trust boundary is driver's use of GSP-written memory (status
  queue), not the signed RISC-V image; unfixed in 595.58.03.
- vBIOS: mVolt+ v0.36 (Aug 2026) bypasses 50-series power limits at RUNTIME without flash —
  power controllers are runtime-programmable beyond vBIOS tables (top research lead).
- Official NVAPI now on GitHub (NVIDIA/nvapi); geohot/cuda_ioctl_sniffer = rmctl reference.
- Claim corrections honored: "mstoeckl RPC recorder" and "nvgspfw" unverifiable → [VERIFY].
- Remaining agents: userspace-control, prior-art/legal.

## 2026-10-15 — wave 1a: generation-matrix agent complete (Europe/Istanbul)
- All 7 files landed in 01-generations/ (matrix + pascal/turing/ampere/ada/blackwell/rubin), cited to 2024–2026 sources.
- Key facts absorbed into SOURCES.md: per-arch GSP images (ga10x covers Ampere AND Ada),
  NVreg_EnableGpuFirmware=0 only Turing→Ada, Blackwell open-KMD-only, official vBIOS BIT spec
  is public, OMGVflash/NVflashk broke vBIOS signature enforcement (Turing→Ada; no GB2xx bypass),
  nova-core falcon boot-chain docs, LHR timeline, R580 = last Pascal branch, NVK no-GSP path,
  Rubin VR200/CPX confirmed + consumer RTX 60 rumor (H1 2027).
- New RE tool for inventory: NV-GSP-Bootloader (extracts ELF/bin from gsp_ga10x.bin).
- .gitignore fixed: SHA256SUMS.all / MANIFEST now committed; binaries still ignored.
- Pending agents: gsp-firmware, vbios (in progress), kernel+tools, userspace, prior-art.

## 2026-10-15 — wave 0.5: P2/P3 groundwork while wave-1 agents run (Europe/Istanbul)
- **Sudo obtained from user for READ-ONLY root captures only** (never stored in repo; never
  used for any GPU mutation). Root dump added full 4 KiB PCI config space: Resizable BAR,
  Secondary PCIe, 16 GT/s PHY caps now in 06-ground-truth/dumps-*-root/.
- `nvidia-smi -q -x` exposes `<gsp_firmware_version>615.71.09</gsp_firmware_version>` —
  GSP firmware version is directly queryable (fact recorded).
- `scripts/fetch_gsp.sh` written + tested (local pass): GSP images collected to
  firmware-store/gsp/ with SHA256SUMS.all committed (binaries gitignored).
- open-gpu-kernel-modules shallow-cloned to vendor/ (default branch = 615.78.08; tag
  v615.71.09 absent upstream). Source mining produced 07-prototype/rmctl-notes.md:
  - `NV_ESC_RM_CONTROL = 0x2A` (nv_escape.h) + `NVOS54_PARAMETERS` (nvos.h) → rmctl recipe.
  - ctrl2080 {fan,perf,power,thermal,volt} headers = the public control surface.
  - msgq library = GSP RPC transport.
  - **`dev_gsp.h` register manuals exist per-arch INCLUDING rubin/gr100** — next-gen GSP
    register docs already public in-tree (feeds 01-generations/rubin.md).

## 2026-10-15 — wave 0: scaffold + wave 1 launch (Europe/Istanbul)
- Goal armed (max 30 rounds); repo scaffolded.
- Recon: `gh` authenticated as **bnelabs** → real private GitHub repo possible.
- **Lab rig found: RTX 3090 (GA102, rev a1) @ 01:00.0, Open Kernel Module 615.71.09, CUDA 13.4
  (branch r615), running production inference (95% util, 80C, 417W/420W).**
  → USER RULE: GPU must never be disturbed. All captures strictly read-only
  (NVML queries, /proc, /sys reads, lspci config dumps). No mutations, no resets, no unbinds.
- Authored: README, ROADMAP, TECHNIQUES (12 techniques), SOURCES seed, ground-truth docs,
  passive capture script.
- Launched 6 parallel research agents (web-only, forbidden from touching the GPU):
  1. 02-firmware/gsp-firmware.md
  2. 02-firmware/vbios.md
  3. 03-low-level-access/kernel-drivers-and-registers.md + 04-tools/tools-inventory.md
  4. 03-low-level-access/userspace-control.md
  5. 01-generations/* (matrix + pascal/turing/ampere/ada/blackwell/rubin)
  6. 05-security-research/* (prior-art, legal-and-safety)
- Next: passive ground-truth capture, wave-0 commit, private GitHub push; then integrate wave 1.

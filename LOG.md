# Research log (append-only)

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

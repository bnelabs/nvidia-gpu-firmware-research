# Research log (append-only)

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

> HISTORICAL / SUPERSEDED. Not an authorized runbook. Claims may be retracted. Read current CONSTITUTION.md and CORRECTIONS.md at the repository root.

# Ground truth rig

- **GPU:** GeForce RTX 3090 (GA102, rev a1) @ PCI 01:00.0 — **runs production inference, do not disturb**
- **Driver:** NVIDIA Open Kernel Module 615.71.09 (branch r615), CUDA UMD 13.4, Ubuntu, gcc 15.2
- **State at wave 0 (2026-10-15):** P2, 95% util, 80C, 417W/420W, 21GB/24GB VRAM in use

## Rules
- Captures here are **read-only only** (NVML queries, /proc, /sys reads, lspci config dumps).
- Never: resets (-r), power/clock mutations, driver unbind, sysfs writes, rom dump (`echo 1 > rom`), flashing.
- Mutating experiments live in P4 on a disposable test bench / VFIO VM.

## Usage
```bash
bash scripts/capture_state.sh   # passive snapshot -> dumps-<timestamp>/ (text, committed)
```

## Why this rig matters
Ampere (GA10x) is the generation where GSP-capable open kernel modules matured (510+), the LHR
era firmware interplay is documented, and the card idles at a driver branch (r615) far past the
last public guides — perfect for verifying which community knowledge still holds in 2026.

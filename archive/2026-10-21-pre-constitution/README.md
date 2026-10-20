> HISTORICAL / SUPERSEDED. Not an authorized runbook. Claims may be retracted. Read current CONSTITUTION.md and CORRECTIONS.md at the repository root.

# NVIDIA Consumer GPU Firmware & Low-Level Control — Research Lab

Private research repository. Mission: understand the firmware running inside NVIDIA consumer
GPUs and map every practical way to observe and command that hardware at the lowest possible
level — vBIOS, the GSP firmware (RISC-V SoC present since Turing), engine falcons
(PMU/SEC2/NVDEC/NVENC), and the command surface above them (BAR0 registers, RM ioctls,
GSP RPC, NVML/NVAPI).

## ⚠️ Lab operating rule
The lab rig GPU is running **production inference** at all times. Every capture on this host is
**strictly read-only** (NVML queries, `/proc`, `/sys` reads, `lspci` config-space dumps).
No resets, no clock/power mutations, no driver unbinds, no sysfs writes, no flashing —
mutating experiments belong to a separate test bench (see ROADMAP P4).

## Why GSP is the center of gravity
Since Turing (2018), NVIDIA GPUs contain a RISC-V based **GPU System Processor (GSP)** running
a substantial firmware image that has progressively absorbed the closed-source Resource Manager
(RM): clocks, power, thermal, link training. Since the RTX 50 (Blackwell) generation the
**open kernel modules are mandatory**, so the entire driver↔GSP protocol is public source.
Low-level control of a modern NVIDIA card therefore decomposes into four layers:

1. **vBIOS** — boot-time policy: power targets, perf tables, display/GOP, memory init straps.
2. **GSP firmware** — the runtime brain (RISC-V): shipped as `gsp.bin` with every driver.
3. **Registers** — BAR0/BAR1; documented in `open-gpu-doc` (manuals exist for Volta/Turing/Ampere
   only: GA100 broadest at 17 units, GA102 a 7-unit subset; **no Ada/Blackwell manuals published**;
   the GSP/falcon registers live in the kernel-module tree's `swref/published/` per-arch headers).
4. **RM control plane** — the ioctl surface `/dev/nvidiactl` + `/dev/nvidia0`, fully defined by
   the open kernel modules' headers; NVML (`nvidia-smi`) and NvAPI are just frontends to it.

## Scope
| Generation | Arch | Consumer chips (incl. "60-class") | Firmware posture |
|---|---|---|---|
| GTX 10 | Pascal GP10x | 1050–1080 Ti (1060 tier) | closed KMD; vBIOS-centric control |
| GTX 16 / RTX 20 | Turing TU1xx | 1650/1660, 2060–2080 Ti (2060 tier) | GSP introduced, optional |
| RTX 30 | Ampere GA10x | 3050–3090 Ti (3060 tier, LHR era) | GSP via open KMD (510+) |
| RTX 40 | Ada AD10x | 4060–4090 (4060 tier) | open KMD mature |
| RTX 50 | Blackwell GB2xx | 5060–5090 (GDDR7) | **open KMD mandatory**, GSP-only path |
| "RTX 60" | Rubin (watchlist) | TBD | tracked in 01-generations/rubin.md |

Per-generation briefs: [01-generations/](01-generations/).

## Repo map
```
01-generations/        per-gen briefs + cross-generation firmware matrix
02-firmware/           gsp-firmware.md, vbios.md, gsp-diffing-lab.md, vbios-lab.md
03-low-level-access/   kernel-drivers-and-registers.md, userspace-control.md, tracing-notes.md
04-tools/              tools-inventory.md (32 tools)
05-security-research/  prior-art.md, legal-and-safety.md
06-ground-truth/       lab rig facts + timestamped passive dumps (text only)
07-prototype/          rmctl.c (working RM client) + rmctl-notes.md
scripts/               capture_state.sh, fetch_gsp.sh, fetch_gsp_history.sh,
                       parse_vbios_bit.py (spec-accurate BIT/PERF parser)
firmware-store/        collected firmware (binaries gitignored) + SHA256SUMS inventories
TECHNIQUES.md          12 creative acquisition/analysis/control techniques
ROADMAP.md             phases P0–P5 and status
LOG.md                 append-only dated research log
SOURCES.md             master source index
```

## Method
1. **Desk research** — web sources, open-source code (open-gpu-kernel-modules, nouveau), community RE. Citations in every doc.
2. **Ground truth** — passive captures from the live rig (06-ground-truth/).
3. **Tooling** — build the missing tools (rmctl prototype, gsp.bin diffing, vBIOS BIT parser).
4. **Experiments** — only on disposable hardware / VFIO-VMs, never on the production rig.

## Ground rules
- Owner-hardware research only; no attacking systems you don't own; no malware.
- **No firmware binaries in git** (copyright): store URL + version + sha256 only (see .gitignore).
- Flashing and destructive paths are documented *before* performed, with recovery runbooks.

## Progress tracking
- `LOG.md` — dated entries, append-only.
- `ROADMAP.md` — phase checkboxes.
- Git history — one commit per research wave, tagged `wave-N`; private GitHub remote.

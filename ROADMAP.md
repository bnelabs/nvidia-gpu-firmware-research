# Roadmap

## P0 — Scaffold (done 2026-10-15)
- [x] Repo, structure, ground rules, private remote
- [x] TECHNIQUES.md v1 (12 acquisition/control techniques)
- [x] Passive ground-truth capture script (`scripts/capture_state.sh`)

## P1 — Literature & codebase wave (running)
- [x] Launch 6 parallel research agents: GSP firmware, vBIOS, kernel drivers & registers,
      userspace control, generation matrix (+Rubin watchlist), prior art & legal
- [ ] Integrate outputs, cross-check citations, fill generation matrix

## P2 — Firmware acquisition lab
- [ ] `scripts/fetch_gsp.sh` — collect gsp.bin for driver branches r550→r615+ (installed driver,
      .run/Windows packages, GitHub releases); log sha256 per version
- [ ] `scripts/fetch_vbios_samples.sh` — vBIOS corpus (TechPowerUp DB + partner update zips)
- [ ] First binary-diff experiments: gsp.bin across driver versions; vBIOS across board partners

## P3 — Command surface tooling
- [ ] `rmctl` prototype: userspace RM-control caller via `/dev/nvidiactl` ioctls using
      open-gpu-kernel-modules UAPI headers (src/common/sdk/nvidia/inc/ctrl/)
- [ ] RPC tracer recipe: ftrace/bpftrace on open KMD symbols; evaluate GSP RPC loggers
- [ ] devregs-style BAR0 register definitions from open-gpu-doc (uio/vfio on unbound GPU only)

## P4 — Controlled experiments (test bench only, never the production rig)
- [ ] vBIOS mod sandbox on spare card / VFIO+QEMU VM; flash + recovery drill (SPI clip read/write)
- [ ] Map RM controls ↔ NVML/NVAPI effects for power/clock/fan/thermal

## P5 — Writeups
- [ ] Per-generation control playbooks; bricking & recovery runbook; responsible disclosure notes

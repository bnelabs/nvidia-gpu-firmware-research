# Roadmap

## P0 — Scaffold (done 2026-10-15)
- [x] Repo, structure, ground rules, private remote
- [x] TECHNIQUES.md v1 (12 acquisition/control techniques)
- [x] Passive ground-truth capture script (`scripts/capture_state.sh`)

## P1 — Literature & codebase wave (done 2026-10-15)
- [x] Launch 6 parallel research agents: GSP firmware, vBIOS, kernel drivers & registers,
      userspace control, generation matrix (+Rubin watchlist), prior art & legal
- [x] Integrate outputs, cross-check citations (13 research files; userspace-control.md
      parent-authored after one agent stalled; corrections applied: open-gpu-doc coverage,
      "Breaking Band" misattribution, unverifiable RPC-recorder claims → [VERIFY])

## P2 — Firmware acquisition lab (in progress)
- [x] `scripts/fetch_gsp.sh` — written + local pass (hashes committed: 615.71.09 ga10x/tu10x)
- [ ] Collect gsp/ucodes images across branches r550→r615+ via .run extraction; start version-diff
- [ ] `scripts/fetch_vbios_samples.sh` — vBIOS corpus (TechPowerUp DB + partner update zips)
- [ ] Binary-diff experiments: gsp_ga10x.bin across driver versions (38→63.5 MB growth already
      documented via linux-firmware); vBIOS across board partners (BIT parser route)

## P3 — Command surface tooling (rmctl DONE; expand next)
- [x] `rmctl` prototype WORKS END-TO-END (wave 1c): version handshake → object alloc →
      NV2080_CTRL_CMD_GSP_GET_FEATURES read-only probe, unprivileged, zero patching
- [ ] rmctl query mode: enumerate read-only controls (CLK/THERMAL/POWER reads, infoROM)
- [ ] RPC tracer recipe: ftrace/bpftrace on open KMD symbols; evaluate GSP RPC loggers
- [ ] devregs-style BAR0 register definitions (uio/vfio on unbound GPU only)

## P4 — Controlled experiments (test bench only, never the production rig)
- [ ] vBIOS mod sandbox on spare card / VFIO+QEMU VM; flash + recovery drill (SPI clip read/write)
- [ ] Map RM controls ↔ NVML/NVAPI effects for power/clock/fan/thermal

## P5 — Writeups
- [ ] Per-generation control playbooks; bricking & recovery runbook; responsible disclosure notes

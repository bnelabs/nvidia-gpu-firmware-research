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

## P2 — Firmware acquisition lab (largely done; extend corpus opportunistically)
- [x] `scripts/fetch_gsp.sh` + `fetch_gsp_history.sh` (local pass + 2-version series, hashes committed)
- [x] GSP container decoded: outer ELF wrapper, per-arch signature timeline (incl. gr10x/Rubin),
      kernel archive table, Libos identified; md5 cross-version churn finding (rebuilt per driver)
- [x] vBIOS corpus started (EVGA 3090 ×3 + 3080); BIT + PERF chain decoded per official spec;
      variant/cross-SKU diffs done; power mW encoding confirmed via sniffer
- [ ] Extend: more driver branches via .run extraction; cross-AIB vBIOS samples (TPU form flow)
- [ ] P/PERF subtable deep decode (PowerPolicy/Overclocking structures) — needs PERF-tables spec

## P3 — Command surface tooling (partial; telemetry semantics remain open)
- [x] `rmctl` v0.5 WORKS: version handshake → object chain → GSP features → PMUMON telemetry
      (250-sample ring) → PSTATE probe; all unprivileged, read-only, cross-checked
- [x] **sniffer.c** — LD_PRELOAD NVOS54 decoder: NVML→control-ID map built empirically
      (power 0x2080a6xx, clocks 0x208090xx, fan 0x208085xx; query correlation only);
      0x2080014a identity query disproves earlier P-state attribution
- [ ] rmctl query mode: validate closed-control response schemas before adding query modes; P-state source OPEN
- [ ] Write-path (Set) control-ID capture — **bench only** (never mutate the production rig)
- [x] RPC tracer recipe: kprobe/ftrace path closed on stock build (tracing-notes.md); strace +
      LD_PRELOAD sniffer are the working tracers
- [ ] devregs-style BAR0 register definitions (uio/vfio on unbound GPU only)

## P4 — Controlled experiments (test bench only, never the production rig) — BLOCKED on hardware
- [ ] vBIOS mod sandbox on spare card / VFIO+QEMU VM; flash + recovery drill (SPI clip read/write)
- [ ] Map RM Set-controls ↔ NVML/NVAPI effects for power/clock/fan/thermal (sniffer on bench)

## P5 — Writeups
- [ ] Per-generation control playbooks; bricking & recovery runbook; responsible disclosure notes

## Lead review — next execution order (2026-10-16)

Detailed findings and acceptance criteria: [REVIEW.md](REVIEW.md).

1. **Offline correctness first:** BIT/PCIR parser fixes and regression tests; repeat all
   corpus diffs with corrected offsets before assigning table meanings.
2. **Repair tracing evidence:** exact NVOS54 ABI validation, RM status, errno preservation,
   bounded capture, per-call provenance, synthetic tests; then isolated NVML getter traces.
3. **P-state encoding corrected:** raw 0x4 = P2 (one-hot RM enum), matching the recorded
   NVML P2. Verify decoder offline first. NVML retrieval-path RE is secondary, not required
   to explain a discrepancy that was caused by formatting.
4. **Validate power:** compare paired NVML readings, selectors, timestamps and complete
   payloads across natural operating variation. 370000 alone does not prove a power limit.
5. **GSP structural RE:** pinned source commit + firmware hash, reproducible section/archive
   inventory, architecture mappings validated by loader consumers, then function-level diffs.
6. **Bench experiments:** remain blocked until spare hardware and recovery procedure exist.

Completion requires reproducible artifacts and explicit uncertainty, not merely a plausible
field value or successful ioctl. Continue offline work while bench hardware is unavailable.

## Final status — 2026-10-16 (30-round session complete)

Delivered and merged-or-in-review (PR #3):
- Packets A (hardened tracer + 13 tests), B (NVML pstate path traced to 0x00000d01 with
  in-process cache proven), C (offline JSON inventory + 17 kernel ELFs + loader provenance),
  D first pass (PowerPolicy/FanPolicy per-SKU bytes), bounded milestone (source-pinned
  GA102 telemetry decoder + offline fixture + tests).
- Corrections absorbed: one-hot P-state enum, 0x2080014a retraction, open-gpu-doc coverage,
  Codex review fixes (ELF ph offsets, RM-status semantics, unknown-bit preservation).
- REA-gated queue (when engines come up): libnvidia-ml.so.1 decode (0x00000d01 response),
  archive directory-walk decode (535-era family mapping), matched-routine functional diff.
- Bench-gated queue (needs hardware): vBIOS mod sandbox, Set-control capture, flash+recovery drill.
- Production rig: read-only throughout; zero mutations; inference never disturbed.

## Goal E/F/G final status (2026-10-18, waves 5-16)
- E: opaque 0x214/0x215 channel mapped structurally (call site -> entry list -> parser
  -> global store); field offsets = named open item
- F: pstate two-source chain END-TO-END decoded (primary one-hot -> gate {2..5} ->
  clock-remap fallback, sentinel 32)
- G: deferred (RISC-V lanes blocked in all REA providers; documented)
- Power provenance: final table in power-provenance.md; a61d reclassified; 0x214 = limit
  transport; per-entry field offsets = open item
- PR #3: open with final summary; branch carries all waves through 16


## COMPLETE RESEARCH STATE (2026-10-20, all goals closed)

### Decoded (source-pinned, evidence-backed)
1. **Control plane** (6 layers): NVML API (626 tags) -> client controls -> kernel RM ->
   BoardObj protocol -> 55-slot RMFunctions tables -> GSP firmware
2. **BoardObj taxonomy**: public Tegra enumeration (MAX=0x3C) + GSP-era extension;
   RPC protocol {class_id, command_id}; method set INFO/STATUS/CONTROL/READINGS
3. **P-state synthesis**: RM one-hot -> arch lookup table -> gate {2,3,4,5} -> clock-remap
4. **Power provenance**: opaque channel (no raw-scalar persistence), a61d = auxiliary,
   vBIOS PowerPolicy mW candidates
5. **GSP firmware signature chain**: SHA-384+RSA-3K / ECDSA P-384, fwsignature = signature
   slots, host has zero enforcement, all on-GPU by fuse-anchored HS verifiers
6. **All-generation boot trust chain**: universal BROM->HS->LS model, ACR migration
   (PMU->SEC2->GSP-FMC), FMC-first boot from Hopper, Rubin verified at binary level

### Gated (precisely named)
- RISC-V RM payload functional diff: needs REA RISC-V lane
- Per-field limit decode: needs bench differential or live debugger
- Custom GSP firmware: needs NVIDIA key, verifier 0-day, or hardware attack

### Key documents
- CONTROL-PLANE.md - the definitive control-plane reference
- 02-firmware/gsp-signature-chain.md - complete signature chain analysis
- 01-generations/boot-trust-chain-comparison.md - all-generation firmware architecture
- 03-low-level-access/power-provenance.md - power control provenance chain
- 03-low-level-access/nvml-control-plane-tags.txt - 628-tag function inventory
- 03-low-level-access/rmfunctions-slot-map.json - 55-slot method map

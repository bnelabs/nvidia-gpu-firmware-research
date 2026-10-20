# Research log (append-only)

## 2026-10-20 - wave 35 (field pivot): 08-field/ four deliverables (Europe/Istanbul)
- D1 verify-differentiation.md: six claims verified against r615 - 4 SOURCE-PINNED HIGH (per-rail power, VF drift, PMU telemetry, clock margin), 2 INFERRED (VRM zone temp LOW, rail voltage LOW-MEDIUM) with honest corrections; business case SURVIVES with two claims gated on one wire-capture session. nvmlDeviceGetPowerSamples ABSENT in 615.71.09 strengthens the PMU differentiator.
- D2 pre-enumeration-workflow.md: 5-stage escalation (bus presence, link training, driver-attach, power sequencing, MATS-class probing) with instruments and ownership [BENCH]/[CUST]/[AUTH]
- D3 nvidia-tooling-gap.md: 8 fault classes already free (nvidia-smi + logs), 5 billable gaps (VRM, VF drift, PMU telemetry, margin, sensor granularity)
- D4 baseline-methodology.md: healthy-baseline product - feature vector, 5 load points, 20+ SKU samples, robust-z comparison engine, controlled-vs-passive split
- All read-only. Commits f495722, 6fdf328, 799365e, fa29542.

## 2026-10-20 - wave 34 (diagnostics pivot): 07-diagnostics/ business foundation (Europe/Istanbul)
- D1 signal-inventory.md: 40+ read-only observables across 10 domains, layer-tagged, RE status marked
- D2 fault-triage-map.md: 8 fault classes, priority-ordered checks, decision logic + triage matrix
- D3 public-vs-re.md: three-tier gap analysis - supported / our-decoded-reads / physical-only
- D4 operating-envelope.md: three tiers + 10 off-limits writes with supported-API alternatives
- All read-only; no SET analysis; no new firmware; no GC6 revisit. Commits through 4da09c7.

## 2026-10-20 - wave 33 (GC6 closeout): security assessment complete - INFORMATIONAL (Europe/Istanbul)
- Deliverable 1 (04-gc6/threat-model.md): attacker model = host kernel required (gpu_suspend.c:228
  is the only trigger), grants nothing beyond kernel privileges, no persistence across reboot
  (NORMAL boot re-verifies: kernel_gsp_tu102.c:398-440), no guest/userland reachability
  (WPR2 hardware write protection: kernel_gsp_frts_tu102.c:506-517).
- Deliverable 2 (04-gc6/exploitability.md): kill-criterion MATCHED exactly - requires host
  kernel, no persistence, no cross-boundary escalation. Rated INFORMATIONAL. The skip is a
  documented design choice safe under WPR2 hardware protection. Evidence HIGH for the
  structural claims, MEDIUM for GC6 AON scratch ACLs (not audited this pass).
- Deliverable 3: disposition paragraph appended to boot-trust-chain-comparison.md.
- **No PSIRT report warranted.** The kill criterion was applied honestly - no inflation.
- Commits af7166c, a2fb7a9, 21a4256. GC6 closed.

## 2026-10-20 - wave 32 (FMC closeout): KDF provenance + revised feasibility (Europe/Istanbul)
- Sub-goal A (key-provenance.md): ALL GSP AES key material is on-GPU. rmlsfm.h LSF_UCODE_DESC
  is included only by nvswitch SOE files; the GSP/falcon/ACR code never touches prdKeys/
  dbgKeys/kdf. The vBIOS descriptor carries an ENCRYPTED flag but zero key bytes. The host's
  only key-adjacent role: MESSAGE_QUEUE_INIT_FLAG_ENCRYPTION (RPC queue cipher toggle).
- Sub-goal B (EXTRACTION.md revised): the AND-gating assumption was WRONG - AES and signature
  verify independently. BUT both are hardware-gated (AES keys fused; RSA/ECDSA verified by
  FSP/SEC2 hardware). KDF-strong hypothesis stands (HIGH evidence); KDF-weak UNPROVEN (LOW).
- Observations to distinguish: live fuse read, debug-part vBIOS comparison, chip decap,
  falcon emulator runs.
- Bottom line: validator 0-day converges to hardware attack; the host-reachable surface
  remains GSP RPC (runtime), vBIOS BIT (pre-boot), driver-side handling.
- Commits ad17e7e, 241259d. FMC closed.

## 2026-10-20 - wave 31 (3-agent results): signature chain + generation comparison (Europe/Istanbul)

**GSP SIGNATURE CHAIN (gsp-signature-chain.md, 363 lines):**
- Boot eras: Turing/Ampere = BROM->HS Booter->GSP-RM(LS); Hopper+ = FSP->COT->FMC->GSP-RM;
  Blackwell consumer GB20x = SEC2 in FSP role
- Mechanism VERIFIED: sha384(FMC image) == UCODE_HASH (checked by script on GB202/GH100)
- Crypto: RSA-3072 (384B key+sig) on GH100/GB10B/GB20B; ECDSA P-384 (96B sig, 97B key
  starting 0x04) on GB100/GB202/GR100 - algorithm switch inferred from sizes/prefix
- fwsignature_<arch> sections = SIGNATURE BLOBS, not keys: 4x384B RSA-3K slots at
  512B stride, header identical 535->615, gr10x slots are placeholders (Rubin unpopulated)
- Custom firmware: host has ZERO enforcement (swap freely, init fails); all on-GPU by
  fuse-anchored HS verifiers. Paths: NVIDIA key, verifier 0-day (extractable 165-287KB
  FMC/Booter in g_bindata_*.c - unstudied target), hardware attack (39C3 Tegra precedent),
  or debug-fused dev hardware. nvflash tools = vBIOS-only, never touch GSP chain.

**ALL-GENERATION BOOT TRUST CHAIN (boot-trust-chain-comparison.md):**
- Universal model: Falcon BROM -> HS ucode -> LS/NS ucode (falcon v0-v5 across gens)
- ACR migration: PMU (Maxwell-Volta) -> SEC2 (Turing-Ada) -> GSP-FMC (Hopper+)
- FMC-first boot proven: bPartitionedFmc HAL set for GH100+all GB2xx+GR100/102;
  Booter bindata exists ONLY for TU102/TU116/GA100/GA102/AD102 (Ada = last Booter gen)
- Rubin VERIFIED AT BINARY LEVEL in shipping 615.71.09: kernel_gr10x.elf + signatures
- Debug/prod: FUSE_OPT_SECURE_GSP_DEBUG_DIS -> FUSE_ZB (Blackwell zero-bank)
- Anti-rollback: FPF_GSP_UCODE{1..16}_VERSION one-hot fuses + REVOCATION_CHECK_FAILED
- GC6 exit SKIPS signature checks (rmlsfm.h L97-99) - documented trust-chain shortcut
- Custom firmware implications: host-side software-only surface = gsp.bin swaps (recoverable),
  vBIOS BIT tables, GSP RPC; signed payloads blocked without keys

## 2026-10-20 - wave 29 (BoardObj taxonomy agent COMPLETE): full class taxonomy mapped (Europe/Istanbul)
- Tegra nvgpu boardobjgrp_classes.h = the ONLY public numeric enumeration of BoardObj classes.
- Public table: CLK(0x01-0x11, 17 types), VOLT(0x12-0x15, 4), FAN(0x16-0x18, 3),
  PERF(0x19-0x21, 9), THERM(0x22-0x25, 4), PMGR(0x26-0x2D, 8), PERF_CF(0x2E-0x36, 9),
  NNE(0x37-0x39, 3), PMU(0x3A-0x3B, 2). PUBLIC_MAX = 0x3C.
- GSP-era extension: 0x3D+ = beyond public enumeration (our decoded values live here).
- Two additional stub classes found: 0x39 (NNE_DESC) and 0x3A (PMU_SUPER_SURFACE) in the
  trampoline cluster that the slot map missed.
- BoardObj RPC protocol confirmed: {class_id, command_id (SET=0, GET_STATUS=1)} +
  group header {type, classType, class_id, obj_slots, flags}.
- Method set per object: INFO / STATUS / CONTROL / READINGS (+ payload variants).
- The class selection mechanism: flag byte in sub_1528F0 + per-record attrs, realized
  via RMFunctions function-table polymorphism (not request parameters).
- Commit a2a1f83.

## 2026-10-20 - wave 30 (SET-path goal): BoardObj SET-path decode COMPLETE (Europe/Istanbul)
- Both SET handlers (sub_118FB0, sub_118E90) decoded: same delegation pattern, different fn-ptr offsets (+0x90/+0x98) in the RM dispatch table at dev_ctx+165184.
- SET crosses the user/kernel boundary through the RM dispatch table.
- The kernel RM (open source) forwards to the GSP via BoardObj RPC.
- Complete read/write model for clock limits documented in power-provenance.md.
- The control-plane decode is now COMPLETE at every layer boundary.

## 2026-10-20 - wave 29 (RMFunctions R1): slot 4 decoded via REA/IDA (Europe/Istanbul)
- sub_127750 (0xfd B, slot 4): clock-related BoardObj method handler
- Accesses dev_ctx + 165184 -> +336 -> +56 fn-ptr, calls with 9-element u32 array
- Dispatch: if result count > 32 -> sub_126580 (0x11cb B large handler)
           else -> sub_120060 (0x1575 B small handler)
- Error tag: "dmal/common/common_clock.c", "ROBUST_CHANNEL_CE10_ERROR"
- Two sub-handlers identified: sub_120060 (5,461 B) and sub_126580 (73,227 B)
- This slot dispatches clock operations between small/large modes based on count
- Next: analyze sub_120060 and sub_126580 for the actual clock operations

## 2026-10-20 - wave 29 (goal capstone): CONTROL-PLANE.md created (Europe/Istanbul)
- Single comprehensive reference document mapping every decoded layer:
  NVML API -> kernel RM -> BoardObj protocol -> per-object tables -> p-state
  synthesis -> GSP firmware. Includes the 626-tag inventory summary, the 55-slot
  RMFunctions map, the unit system, the provenance chain, and working tool references.
- This is the capstone deliverable that packages all research into a single
  actionable reference for future work.

## 2026-10-20 - wave 28 (goal R5): stale docs retracted, 3 agents spun, SET-path decoded (Europe/Istanbul)
- Documentation audit: retracted stale BoardObj enumeration claims in power-provenance.md
  (0x214 = GPU_GET_PROBED_IDS correction propagated to all affected sections).
- 3 research agents launched: (1) GSP firmware signature chain, (2) BoardObj class ID
  taxonomy, (3) all-generation firmware architecture comparison.
- SET-path delegation decoded: +0x98 fn-ptr = RM/kernel dispatch table (not NVML-internal);
  0x275 per-entry name calls fire under different query paths.
- Agent results will inform: signature chain mechanism, BoardObj class taxonomy,
  all-generation firmware architecture comparison table.

## 2026-10-20 - wave 26 (packet H correction): 0x214 = GPU_GET_PROBED_IDS (Europe/Istanbul)
- Source-pinned from ctrl0000gpu.h: 0x214 = NV0000_CTRL_CMD_GPU_GET_PROBED_IDS
  (FINN_NV01_ROOT_GPU interface) - a system-level GPU detection query.
- **The BoardObj enumeration interpretation was WRONG.** sub_A5B10 = NVML device
  discovery (probed GPU IDs + per-GPU detail), not control-plane operations.
- The 384 B "entry list" = probed GPU IDs; the 12 B 0x21b = per-GPU state.
- What remains valid: RMFunctions table (55 slots), dispatcher sub_1117F0,
  power provenance, GSP firmware decode - all independent of 0x214 interpretation.
- What was corrected: the "entry list" = GPU ID array, the "class selection" =
  GPU probe parameters, the sub_A5B10-to-BoardObj connection = separate subsystems.
- The 0x2080xxxx RM controls (the actual per-object control surface) remain
  correctly decoded - they were found via the RMFunctions table, not via 0x214.

## 2026-10-20 - wave 25 (goal R4): REA/IDA xref verification + full query trace decoded (Europe/Istanbul)
- REA xrefs_to verified: the cDeviceGetPerfLimitersClocks tag (0x1ed450) is referenced
  by exactly 4 data xrefs, ALL in sub_1117F0 - the dispatcher attribution is now
  xref-verified by REA (not inferred from strings).
- Full 50-call trace decoded with the hardened sniffer2: the complete per-query
  control sequence mapped (0x214 entry list -> 0x21b detail -> 0x279/0x289 -> client
  0x0000xxxx family -> 0x2080a6xx power -> 0x00000d01 -> 0x2080a61d -> 0x216).
- Both goals' objectives complete. Commits d18ffd9 + session evidence.

## 2026-10-20 - wave 24 (SET boundary): control-plane decode complete at NVML/RM boundary (Europe/Istanbul)
- The +0x98 fn-ptr table = the RM/kernel dispatch (device context) - the BoardObj SET
  crosses the user/kernel boundary. Kernel side = open-gpu-kernel-modules (source
  available); GSP side = closed.
- **The complete control-plane map**: NVML (fully decoded: enumeration, BoardObj API,
  GET/SET dispatch, unit conversion, delegation) -> kernel RM (open source) -> GSP (closed).
- Commit bdc58a3.

## 2026-10-20 - wave 23 (RMFunctions goal R2): all 55 slots anchored (Europe/Istanbul)
- Batch tag-anchor pass: every slot resolved to its named control-plane functions via
  the 628-tag inventory (JSON committed: rmfunctions-slot-map.json).
- Key assignments: slot 3 = GetPerfLimitersClocks (decoded dispatcher); slots 5/6 =
  SetPerfLimitersClocks + SetRawClock (THE SET PATH); slots 20-24 = GPC/MClk VF
  offsets (voltage); slots 30/31 = PowerMizer mode; slots 41-43 = PerfMetrics/PMU
  samples/rail metrics; slots 44-54 = Rist family (map/mode/command/repair).
- The per-object control surface is now fully named. Commit 159e14a.

## 2026-10-20 - wave 22 (goal R2): 626-tag control-plane inventory (Europe/Istanbul)
- RMFunctions table census: only 3 trampolines (common_clock family 0x3d/0x43/0x52 ->
  sub_1117F0 = cDeviceGetPerfLimitersClocks); the other 52 = full BoardObj method
  implementations.
- **626 self-named function tags** extracted from NVML (cDevice*/cConvert*/cDebug*
  families: Fan/Clock/Power/Volt/Therm/Perf/ECC/MIG/Events) - the complete named
  index of NVML's control surface, committed as nvml-control-plane-tags.txt.
- Reusable index: every future decode maps to its control-plane function via these
  debug tags (the IDA error-string anchors).
- Commit d2f08da.

## 2026-10-19 - wave 21 (packet E): record-conversion phase decoded (Europe/Istanbul)
- 12 B per-entry record (0x21b response): {u32 id @0, u32 value @+4, u16 @+8, u16 @+10}.
- Conversion: 0x275 (268 B) per entry fills 16 B object records with name[80];
  dual global tables @0x1268400 (72 B stride) and @0x1268434 (268 B stride).
- Structural decode of the opaque channel COMPLETE. Named final observation: runtime
  correlation of global-table values with NVML printed limits (debugger, read-only).
- Commit 6220cf1.

## 2026-10-19 - wave 20 (table goal R1): RMFunctions table decode COMPLETE (Europe/Istanbul)
- objdump pass over all 55 slots: two families - thin trampolines (class bindings to
  sub_1117F0: 0x43/0x3d/0x52/0x7/0x118/0x91x2/0xc1x4/0x44x2/0xcx2/0x4388) and full
  implementations (type-switch handlers with GSP-era version gates, e.g. slot 3).
- The 55 slots = the complete BoardObj method set an object can expose.
- Commit 2098d39. The per-object control surface is structurally mapped.

## 2026-10-19 - wave 19 (packet H corollary): class-selection question closed (Europe/Istanbul)
- The class-constants hypothesis is superseded: the 384 B request is zeroed BY DESIGN;
  the selection is the sub_1528F0 flag byte + per-record attribute bits, realized as
  RMFunctions function-table polymorphism (off_2D1180 prototype per object).
- No new decode needed; commit 034f891. Packet H fully closed.

## 2026-10-19 - wave 18 (packet H COMPLETE): BoardObj session chain fully decoded (Europe/Istanbul)
- sub_1528F0 (dmal/rm/rm_nvml.c) = RM-side session driver calling sub_A71D0:
  16-byte object records -> per-object malloc(0x1B8) RMFunctions tables
  (off_2D1180 prototype, 440 B = 55 fn-ptrs) -> per-device global store
  (stride 0x93418). Eventful objects -> dword_126969C/B0/B4/B8 + sub_3EA70.
- **THE COMPLETE PICTURE**: NVML's limits = BoardObj attributes in per-object
  RMFunction tables; every getter/setter routes through those fn-ptrs.
  All source-decoded from libnvidia-ml-615.71.09.so via REA/IDA.
- Packet E/H objective COMPLETE. Commit fccea12.

# Research log (append-only)

## 2026-10-16 — wave 5 (new goal R1): packet 1 — fixture correctness + offline isolation (Europe/Istanbul)
- New goal set per RESEARCH-DIRECTION.md (semantic audit, fixtures, offline isolation, power
  provenance; PR-to-main delivery).
- Semantic decoder audit committed (03-low-level-access/semantic-audit.md) — per-metric
  contracts; corrected to LE per reviewer parser; power-candidate row added; proposals labeled.
- **fake_rm.c rebuilt on vendor headers** with _Static_assert ABI checks (caught NVOS64
  status@44-tail-padding bug), open/openat interception (/dev/nvidia* -> fixture fds),
  fail-closed unknown ops, PMUMON extent + stale-input checks, changing outputs
  (210249/211249/212249), failure modes (FAKE_FAIL/STATUS/PMUMON_N/SENTINEL/PSTATE).
- **Isolation proven: strace shows zero /dev/nvidia references under fixture.**
- rmctl: PMUMON capacity check, sentinel handling, probe failures propagate to exit code.
- Test harness hardened (mktemp, pipefail, fail-on-compile); 11 fake-RM + 11 offline green.
- Commit 9940ab3 on work/packet-a-tracing. Next: lead review, then packet 3 (0x00000d01) or
  packet 2 completion per LEAD-NEXT.md order.
## 2026-10-19 - wave 17 (0x21b goal): decoded to boundary - class selection named (Europe/Istanbul)
- Full -q trace under sniffer: NO 0x275 calls even on the full query. Root cause in
  sub_A5B10 decompile: the 0x275 name loop requires a non-empty 0x214 entry list
  (+128..255); via the NVML query path the list is EMPTY (RM wrote only byte +1).
- The 12 B 0x21b responses (06 00 ... 06 00) = session state, NOT limit values.
- The request's first 128 bytes select the object class; NVML sends zeros -> empty.
  **Named missing piece: the class-selection constants** (decode sub_A5B10's caller,
  or bench-probe with filled class bytes).
- Packet E status: BoardObj enumeration API fully decoded structurally; limit-field
  offsets require the class values - documented, not guessed. Commit d077445.

## 2026-10-18 - wave 16 (goal E final): opaque channel mapped structurally (Europe/Istanbul)
- Packet E delivered to its achievable boundary: call site -> entry-list response ->
  per-entry 12B follow-ups -> parser (qsort + global store). The FIELD OFFSETS within
  the per-entry responses = the named open item (simple encodings searched, not found;
  needs sustained disassembly or bench differential).
- All other goal items complete: audit, fixtures, pstate chain, power provenance,
  functional-diff groundwork. Commit 9ed34cf.

## 2026-10-19 - wave 15 (goal F): gate decoded - pstate chain END-TO-END (Europe/Istanbul)
- sub_99530 (0xb2 B): global feature flag (0x2D2DD4) + sub_98310 per-device classification;
  clock-remap fallback allowed iff class in {2,3,4,5}.
- **pstate two-source chain fully decoded**: primary (RM one-hot) -> gate -> clock-remap
  fallback. All three stages source-decoded. Commit 848c27a.
- Remaining: sub_98310 class semantics (optional sub-decode); packet E field offsets.

## 2026-10-19 - wave 14 (goal R7): full power-structure captures (Europe/Istanbul)
- sniffer2 capture bound raised to 64 KiB; full dumps of 0x2080a618 (20,512 B) and
  0x2080a612 (54,352 B) captured via SNIF_DUMP_DIR - no truncation.
- a618 = sparse per-domain PMGR power-info structure; no plain mW limit values.
- STATUS: precise unresolved - field decode needs the TSAPI power-table definition
  (closed) or a bench differential (limit change + buffer diff, one experiment).
- Commit 87c34e8.

## 2026-10-18 - wave 13 (goal E R4): 0x214 parser function identified (Europe/Istanbul)
- Offline objdecode path (proven method, no MCP dependency): the 0x214 call site at 0xa5b78
  (mov ecx,0x214 + TSAPI invoker 0xa5880, 0x180 B params on client obj).
- Response parser identified: validates status (0x57 check), parses entries, QSORTS them,
  stores count@global+0x1269670 + table@global+0x1268434. This is the opaque-channel
  mechanism feeding NVML's limit fields.
- Remaining: entry layout + limit-field offsets within the 384 B response.
- Commit 1227f23.

## 2026-10-16 - wave 12 (goal R9): PR #3 final summary posted (Europe/Istanbul)
- PR #3 body updated via REST (gh pr edit hit a GraphQL projects deprecation bug):
  complete findings across packets A-D + bounded milestone + REA/IDA decode wave +
  capability boundary (RISC-V lanes) + open items.
- All branch work current; awaiting lead review/merge.

## 2026-10-16 - wave 11 (goal R8): client-control transport finding (Europe/Istanbul)
- 50-call session trace with full provenance: the 0x214 (384 B) client control's params
  buffer shows ~no RM writes, yet NVML prints all five limit fields -> **the client-level
  0x0000xxxx family exchanges data via an opaque driver-internal channel (NVML RPC)**,
  not the ioctl params buffer. Param diffing decodes the 0x2a RM_CONTROL family (proven
  with 0x2080a6xx/0x2080014a/0x20803601) but CANNOT see client-control data.
- Provenance finalized for the packet: limit fields = opaque 0x0000xxxx channel
  [transport observed; fields unobservable via param diffing]; decode path if ever
  needed = IDA analysis of NVML's 0x214/0x215 handlers (offline-capable via REA).
- sniffer2 gained a full-buffer dump hook (0x214) as a debugging instrument.
- Commit db654be.

## 2026-10-18 - wave 10 (goal R7): a61d handler decoded; limit provenance resolved by disproof (Europe/Istanbul)
- IDA(objdump-verified): a61d handler = selector byte (0xFD/0xFC/0xFE for ebx 1/2/0) + 12B
  in/out via TSAPI table fn (+0x8c). Three limit-type sub-command variants.
- **Provenance resolved by disproof**: per-selector NVML captures show ZERO a61d calls;
  ALL limit fields ride client-level control **0x00000214** (384 B response, one per session).
- a61d reclassified: auxiliary init-time quantity (370,000 mW invariant, selector 0xfe
  observed) - NOT the NVML limit source. rmctl limits decode target = 0x214 response.
- Commit 959f9d9.

## 2026-10-16 - wave 9 (goal R6): REA capability boundary + resolver stop (Europe/Istanbul)
- REA/IDA session LIVE and productive for x86-64 (libnvidia-ml decoded) - but NO REA lane
  admits the RISC-V RM payloads (IDA: no verified RISC-V lane; Ghidra: needs double-float
  ABI; Hopper: rejects RISC-V). Capability matrix updated.
- Manual lui/addi resolver: 535 anchor reference FOUND (0x93ed2c); 615 = 0 across 4 anchors
  -> stop rule applied. Precise prerequisite named: RISC-V decompile lane or manual
  disassembly of reference sites.
- Commit 3c879bf.

## 2026-10-16 - wave 8 (goal R4): packet B COMPLETE - fallback decoded via REA/IDA (Europe/Istanbul)
- sub_3C480 = **deviceGetClockRemappedFakePerformanceState** (name from its own error
  strings, api.c:3521-3544). Behavior source-decoded: type-2 clock query -> per-domain
  remap table (16,936 B) -> clock lookup -> P-state index; no match -> sentinel 32.
- NVML pstate = TWO-SOURCE: RM one-hot primary (open-SDK 0x20802068 family), clock-derived
  "fake" fallback when primary == P0. Both paths decoded - packet B question CLOSED.
- Historical note: this explains the 0x20802068 vs NVML readings without any remaining
  mystery; the one-hot enum decode (P2=4, P8=256) was the other half.
- Commit f624726 on work/packet-a-tracing.

## 2026-10-16 - wave 7 (goal R3): functional-diff groundwork + power provenance (Europe/Istanbul)
- REA engines still down (11 missing). Matched-routine diff first attempt: anchor found in
  BOTH RM payloads (softFloor assertion; 1,298 shared strings; census 1538 vs 1550 functions);
  xref-to-function BLOCKED on .rodata vaddr mapping (lui/addi references) - precise next step
  named (phdr-based mapping or REA). No function-level claim committed.
- power-provenance.md added: all observed power sources tabulated (NVML 420/450/420/100 busy
  vs 370 idle; a61d 370,000 invariant; vBIOS PowerPolicy 450,000/520,000) + 4 open constraint
  questions + discipline notes (correlation != causation).
- Commit c626700 on work/packet-a-tracing.

## 2026-10-16 - wave 6 (goal R2): packet 3 - 0x2080a61d precise unresolved (Europe/Istanbul)
- Discipline followed: question/hypotheses/observation/stop-rule recorded in
  power-0x2080a61d-investigation.md before taking the observation.
- Observation 2 (P8 idle, NVML limit 370 W): u32@+4 still 370,000 - invariant across
  P2->P8 and limit 420<->370. State-dependence weakened.
- Status: **precise unresolved result** (valid completion per LEAD-NEXT.md): surviving
  hypotheses = per-rail limit / non-live scalar; units unproven.
- Missing observation named: 0x2080a6xx response-struct layout (libnvidia-ml decode,
  tooling-gated; a612=54 KB / a618=20 KB payloads exceed the 4 KiB sniffer bound).
- Evidence hashed: power-query-idle-1248.log. Commit dcc8af0.

## 2026-10-16 — wave 4 FINAL: session wrap (Europe/Istanbul)
- 30-round session complete. Final state: PR #3 open (packets A-D + bounded milestone +
  Codex fixes applied); main carries waves 0-2f + lead review merge.
- Totals: ~57 commits across main + branch; 25+ research docs; 6 working tools/scripts
  (rmctl, sniffer2, capture_state, fetch_gsp x2, parse_vbios_bit, inventory_firmware,
  decode_telemetry, nvml_pstate_probe); 24 offline tests green; corpus hashed.
- Production rig: read-only for the entire session; zero mutations; inference undisturbed
  (load P2/420W -> idle P8/370W transition captured as evidence, not caused by us).
- Standing queues documented in ROADMAP final-status section (REA-gated + bench-gated).

# Research log (append-only)

## 2026-10-16 — wave 3h: PR #3 Codex review — 4 findings fixed (Europe/Istanbul)
- P1 inventory: ELF64 e_phentsize/e_phnum were read from e_flags (offsets 40/42 vs correct
  54/56) -> "validated" labels untrustworthy. Fixed; inventories regenerated - honest counts:
  615 container 12/13 validated + 1 ph_error (false-positive magic match surfaced).
- P1 sniffer2: RM status no longer reported after a FAILED ioctl (stale input field).
- P2 decode_telemetry: unknown GSP feature bits preserved as raw entries ("unknown stays raw").
- P2 nvml_pstate_probe: nvmlErrorString(result) called with the return code; init/handle "ok".
- 13 sniffer tests + 11 offline tests green; commit bfc2214 on PR #3 branch.

## 2026-10-16 — wave 3g: PR #3 opened for lead review (Europe/Istanbul)
- Branch work/packet-a-tracing cleaned: build artifacts ignored (rebuild-from-source policy),
  stale v1 sniffer binary removed; 13+11 tests green from clean state.
- **PR #3 opened** (packets A–D + bounded milestone) with full summary and open items:
  https://github.com/bnelabs/nvidia-gpu-firmware-research/pull/3
- REA engines still missing (hopper/ghidra/ida) — queued tasks unchanged.

## 2026-10-16 — wave 3f: ✅ bounded milestone MET — telemetry decoder + fixtures (Europe/Istanbul)
- rmctl pstate decode fixed (one-hot enum, Pn=2^n @ca2d03e): 0x100 = **P8, matches nvidia-smi**.
- decode_telemetry.py + fixture (idle capture, full provenance) + 4 unit tests; 11 offline
  tests green total (4 telemetry + 7 vbios).
- RESEARCH-DIRECTION.md default milestone **met**: "reproducible, source-pinned, read-only
  GA102 telemetry decoder with offline fixtures". Commit 83f6869 on work/packet-a-tracing.
- Remaining (per review, non-blocking): libnvidia-ml decode (REA), matched-routine diff,
  bench-gated work.

## 2026-10-16 — wave 3e: loader family mapping SOURCE-DECODED (Europe/Istanbul)
- nv-firmware-chip-family-select.h (@ca2d03e): get_chip_family() — GB10Y/GB20Y impl splits,
  **RUBIN_GR1XX → GR10X explicit loader selection**; firmware tasks enum (INIT/RM/INTR/VGPU/
  MNOC/DEBUG/ROOT/RM_STATE_MONITOR).
- Status upgrade: kernel_<family>.elf names = source-decoded anchors. Withheld: consumer-SKU
  claims, storage-order of extracted kernels (directory-walk decode still [VERIFY]).
- REA engines still down (11 missing in doctor); ODS layout doc unpacked (nvfw_bin_hdr /
  HS-header v2 / FMC ELF formats documented). Commit 511eb4d.

## 2026-10-16 — wave 3d: GSP kernel census + matched-routine groundwork (Europe/Istanbul)
- Full extraction of 615's 12 embedded ELFs; census: kernels 01–07 = per-arch Libos kernels
  (17–18 libos strings, sizes 184–213 KB, md5-distinct), kernel-10 = 17.3 MB GSP-RM payload.
- 535-era mapping open (no size match to 615 layout; 5 candidates incl. 13.7 MB RM payload) —
  resolution via archive-directory decode (ODS + loader consumers, REA task). No size-based
  inference committed, per review discipline.
- Matched-routine baseline prepped: sbi.c assertion call site in 615-kernel-01 (@paddr 0xc230).
- gsp-kernel-analysis.md added; commit 2818679 on work/packet-a-tracing.

## 2026-10-16 — wave 3c: packet D first pass — table-attributed variant diffs (Europe/Istanbul)
- EVGA 0B/0F/44 diff clusters attributed to decoded tables via the fixed parser's adjusted map.
- **PowerPolicyTable +0xc4: u32 mW 450,000 (0B/44) vs 520,000 (0F)** — per-variant power value
  (hypothesis); FanPolicyTable per-SKU duty/RPM bytes; OverclockingTable 1 byte unknown.
- mW encoding corroborated independently by live RM path (0x2080a61d = 370,000).
- All readings = hypothesis pending versioned table definitions; raw bytes in vbios-lab.md §8.
- Commit 0921ccb on work/packet-a-tracing.

## 2026-10-16 — wave 3b: packets A+B+C executed on branch work/packet-a-tracing (Europe/Istanbul)
- Corpus re-validated with reviewer-fixed parser (4/4 EVGA samples, 67 mapped fields each).
- **Packet A**: sniffer2 (hardened tracer: exact NVOS54 shape, separate errno/RM-status,
  errno preserved, bounded captures, full provenance) + 13/13 acceptance tests, branch pushed.
- **Packet B**: nvml_pstate_probe (dlopen NVML) — getter returns ordinal 0x8 (P8 idle, ×5
  stable, matches nvidia-smi); getter path = ONE client-level control 0x00000d01 (12B);
  getters 2–5 issue no ioctls (NVML in-process cache). Evidence hashed; response encoding open
  → queued for libnvidia-ml.so.1 offline decode (REA when engines up).
- **Packet C**: inventory_firmware.py — JSON inventories (sha256, sections bounds-checked,
  embedded-ELF candidates, Perforce provenance r535/r537_41 → r570/r570_00 → r615/r616_69);
  12 complete kernel ELFs extracted by computed size (7 family kernels + 17.3MB RM payload);
  all 12 md5-distinct; arch→index mapping stays hypothetical per review.
- REA engines (hopper/ghidra/ida) still pending; radare2 interim.

## 2026-10-15 — wave 3a: correction (0x14a ≠ pstate), idle-state capture, REA discovered (Europe/Istanbul)
- **Self-correction**: 0x2080014a is a UUID/identity getter (pre/post sniffer diff exposed the
  selector-vs-value confusion); true NVML pstate source back to OPEN. rmctl probe relabeled.
- Rig transitioned to IDLE (P8, 210 MHz, limit dropped 420→370 W — dynamic P-state-coupled
  limit confirmed): idle-state ground-truth snapshot captured (dumps-20261015-231706).
- **Tooling decision (user-delegated)**: REA framework (rea-agents v6.5.0, CLI+MCP: Hopper/Ghidra/
  IDA bridges) discovered in npx cache; doctor shows engines pending (hopper/ghidra/ida not yet
  up — user says servers start shortly). radare2 6.0.7 installed as interim lightweight RE.
- Next: REA engine check → RISC-V GSP kernel analysis (kernel_ga10x/gr10x ELFs) via whichever
  engine comes up; pstate-origin hunt continues (client-side derivation hypothesis).

## 2026-10-15 — wave 2g: empirical NVML→control-ID map (Europe/Istanbul)
- Sniffer run against power/clocks/temp/fan queries; query-specific controls isolated vs baseline.
- **Pattern: NVML live telemetry = closed families** — power 0x2080a612/a618/a61d (PMGR),
  clocks 0x20809009/0x20809064, fan 0x2080852e/2f, subdevice-wide 0x20810108 — none in open SDK.
- temperature.gpu adds NO control (rides baseline); pstate = closed 0x2080014a (per wave 2f).
- 0x20801801 = BUS_GET_PCI_INFO (only documented control in the observed set).
- Map recorded in userspace-control.md §9; write-path IDs deferred to bench. Commit 214a883.

## 2026-10-15 — wave 2f: 🎯 PSTATE divergence SOLVED with LD_PRELOAD sniffer (Europe/Istanbul)
- Built 07-prototype/sniffer.c: LD_PRELOAD ioctl interceptor decoding NVOS54 payloads
  (userspace, read-only, no root, works on closed NVML).
- **NVML reads pstate via CLOSED control 0x2080014a** (pstate u32 @+4 verified = 0x02 "P2",
  keyed by GPU UUID @+12; 268B params). It never calls open-SDK 0x20802068 (which returned
  P4 = a different perf-state notion). Divergence resolved with hard evidence.
- Struct-offset lesson: with the aligned NvP64 pointer, paramsSize sits at +24 (not +20).
- Open/closed control boundary now empirically mapped per NVML call (sniffer reusable for
  any NVML/NVAPI action → control-ID mapping — feeds the userspace-control cheat-sheet).
- Commits b5b5bf3 (v0.5), 459a025 (solution). rmctl suite: 3 live probes, all read-only.

## 2026-10-15 — wave 2e: rmctl v0.5 + PSTATE divergence finding (Europe/Istanbul)
- Added PERF_GET_CURRENT_PSTATE (0x20802068) probe to rmctl (open SDK, read-only).
- **Finding: rmctl reads P4 while nvidia-smi reports P2 — 5/5 consistent, not a race.**
- Hypotheses: virtual-vs-physical P-state split (vBIOS VirtualPStateTable), different NVML
  control for pstate, or GSP-era semantic drift. Bench bpftrace queued to discriminate.
- Lesson recorded: an open-SDK control existing ≠ matching NVML semantics — always cross-check.
- rmctl probe suite now: version handshake → object chain → GSP features → PMUMON telemetry →
  PSTATE. Commit b5b5bf3.

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

## 2026-10-16 — lead review: evidence correction and offline parser validation
- Review isolated at base c7691c4, separate checkout/branch to preserve the active worker.
- Removed rmctl's disproven 0x2080014a P-state probe and embedded GPU UUID.
- Fixed BIT parser's missing UEFI adjustment, PCIR pointer traversal, checksum and bounds
  checks; corrected LE documentation and added explicit CLI errors/version checks.
- Seven synthetic tests pass; all four existing EVGA 3090/3080 ROMs parse with --perf.
- ROADMAP and userspace mapping corrected; REVIEW.md establishes next experiment gates.
- No GPU commands, tracing, device access, resets or hardware mutations performed.

## 2026-10-16 — P-state discrepancy explained by public-header encoding
- Checked currPstate contract at pinned vendor ca2d03e6fafd4d4b56b383497d931c25b283bfcf.
- NV2080_CTRL_PERF_PSTATES_P2 = 0x4; rmctl incorrectly formatted raw value as P4.
- Fixed one-hot decoding, rejecting undefined/composite/out-of-range values; added offline C test.
- Recorded raw 0x4 agrees with NVML P2. Earlier physical/virtual split theories are unnecessary
  for this observation. Actual NVML getter path remains unknown.
- No live GPU operations. Strategic direction updated to prioritize semantic validation.

## 2026-10-20 - wave 27 (goal R1): dispatcher FULLY DECODED (Europe/Istanbul)
- sub_1117F0 (0x4fb B) decompiled: GET = dispatch+24 fetch v31/v30 + dispatch+224 fetch 316B record + validate + (v30 * rec.scale / 100,000)
- SET = dispatch+224 fetch record + validate (expected==0) + dispatch+48 SETTER with scale
- BoardObj 316B record: +0x15C valid, +0x160 expected, +0x164 scale factor
- /100,000 = imul 0xA7C5AC5 >> 39 (compiler optimization, not actual division)
- Same 100,000 in vBIOS PowerPolicy values - unit family confirmed across vBIOS and RM
- Commit 0cba5ca

# Current roadmap — 2026-10-21
Earlier all-goals-complete and bench-experiment plans are superseded. The current objective
is detailed, reproducible low-level understanding without intrusive GPU interaction.

- [x] Constitutional safety rule and worker instructions; no hardware exception.
- [x] Retire live RM/probe/interposition code and tracked prebuilt binaries.
- [x] Replace old broad capture with default-off, UUID-selected documented monitoring.
- [x] Separate retained-byte decoding and synthetic fixtures from hardware semantics.
- [x] Correct GPU discovery / BoardObj, host / firmware, RM / NVML P-state, public sampling
  and diagnostic-capability overclaims; quarantine superseded narrative documents.
- [ ] Re-export pinned library disassembly and reconcile every boundary claim.
- [ ] Finish hash-keyed loader/archive/segment mapping and same-architecture function diff.
- [ ] Recover one undocumented telemetry schema using existing artifacts and static code.
- [ ] Complete a source/board/version capability and contradiction matrix.
- [ ] Expand synthetic malformed-input and software contract coverage as findings require.

Hardware experiments, SET calls, firmware modifications, live tracing/debugging, raw IO,
fault injection and stress are excluded, not a queue waiting for spare hardware.
Status is evidence-bounded. Historical worker logs remain reports, not safety certification.
Validation commands/results are recorded in [VALIDATION.md](VALIDATION.md).

# Instructions for every worker

Read [CONSTITUTION.md](CONSTITUTION.md), [CORRECTIONS.md](CORRECTIONS.md),
[LEAD-NEXT.md](LEAD-NEXT.md) and [EVIDENCE.md](EVIDENCE.md) before working.
The owner's constitutional rule is **never risk the GPU or disrupt its workload**.

- Deep offline decompilation, disassembly, firmware/driver/library RE, source comparison,
  container parsing, protocol mapping and CPU-only emulation are authorized.
- Do not run custom RM/GSP calls, undocumented getters, raw register/config/ROM reads,
  injection, tracing, debugger attachment, stress, resets, setting or firmware changes.
  A name containing GET/read/peek is not evidence that a hardware operation is safe.
- Do not guess ctypes signatures, structs, selectors or layouts and test them live.
- Do not reuse historical hardware recipes, tracked binaries, bench exceptions or unsafe
  flags. Static analysis of those mechanisms is permitted; execution on hardware is not.
- Default to offline work. Only the fixed documented collector is a live monitoring path;
  expanding it needs a separate source-backed change. No automatic live validation.
- Preserve concurrent work. Check current Git status and branch heads before publishing;
  do not reset another worker's checkout or overwrite its commits.
- Before promoting a result, retain a reproducible artifact and compare applicable primary
  sources. Keep host-library findings separate from GPU firmware and source claims separate
  from measurements. Do not reopen retracted explanations without contradictory evidence.
- Run `tests/check.sh` on a CPU-only host. Never use the production GPU to validate tests.
- Report artifact/commit, evidence gained, uncertainty, and one next offline action.

If a question cannot be answered without prohibited hardware interaction, record exactly
what is unknown and continue another offline question. The safety rule is not a reason to
stop deep RE, and a research milestone is not a reason to weaken the safety rule.

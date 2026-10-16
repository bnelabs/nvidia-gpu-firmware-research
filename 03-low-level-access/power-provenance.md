# Power-limit provenance - constraint-source analysis (packet D continuation)

Per RESEARCH-DIRECTION.md "constraint-source analysis": distinguish requested, default,
enforced and measured power. All values for the lab rig (RTX 3090, UUID 8a9c05b3..., driver
615.71.09) unless noted. Statuses per the discipline.

| Source | Value | Units (status) | When observed | Provenance |
|---|---|---|---|---|
| NVML power.limit (busy, P2) | 420 W | W - cross-validated (nvidia-smi + XML) | 2026-10-15 12:22 | observed-bytes |
| NVML power.max_limit | 450 W | W - cross-validated | 2026-10-15 12:22 | observed-bytes |
| NVML power.default_limit | 420 W | W - cross-validated | 2026-10-16 12:47 | observed-bytes |
| NVML power.min_limit | 100 W | W - observed-bytes | 2026-10-16 12:47 | observed-bytes |
| NVML power.limit (idle, P8) | **370 W** | W - cross-validated (dynamic, P-state-coupled) | 2026-10-16 23:17 | observed-bytes |
| RM control 0x2080a61d @+4 | 370,000 | **mW - hypothesis** | 2026-10-15 21:33 (P2, limit 420) AND 2026-10-16 12:47 (P8, limit 370) | observed-bytes; invariant across states |
| vBIOS PowerPolicyTable +0xc4 | 450,000 / 520,000 | mW - hypothesis (corpus variants 0B/44 vs 0F) | 2026-10-16 | observed-bytes |
| 0x2080a612 / 0x2080a618 | 54,352 B / 20,512 B payloads | unknown (capture-truncated) | 2026-10-16 | observed-bytes |

## Open constraint questions
1. Which source NVML's power.limit reads from at runtime (a61d? a618 table? PowerPolicy?) - blocked on 0x2080a6xx response-struct decode (REA tooling).
2. Is 370,000 a per-rail (NVVDD) limit while 420,000 is total? Requires rail topology (PowerTopologyTable decode) or a paired multi-rail capture.
3. Does the 420->370 idle transition originate in the GSP policy engine (RM one-hot P-state input) or the driver? Distinguisher: paired traces at the transition (bench, or natural transition with sniffer2 attached - read-only, queued).
4. vBIOS PowerPolicy 520,000 in variant 0F vs 450,000 in 0B/44 - board-class difference; requires the variant board names (corpus metadata gap).

## Discipline notes
- Natural state variation only; temporal correlation != causation.
- No setters used; NVML getters are read-only but may wake hardware (documented).

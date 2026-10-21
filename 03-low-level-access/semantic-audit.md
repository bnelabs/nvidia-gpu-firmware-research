# Decoder contracts — current scope
All decoding is offline. [CORRECTIONS.md](../CORRECTIONS.md) overrides older claims.

| Input | Contract | Limit |
|---|---|---|
| RM P-state mask | Pn = 1 << n for n=0..15, pinned ctrl2080perf.h | Undefined/composite mask stays raw; not NVML ordinal |
| NVML/nvidia-smi P-state | Public ordinal / formatted Pn string | Preserve as supplied; no one-hot conversion |
| NVOS54 retained record | 32-byte, 64-bit little-endian header; fields and statuses decoded explicitly | Pointer fields are recorded values, never dereferenced; no live syscall |
| Record payloads | Bounded by declared and available length and 65536-byte cap | Short/oversized data marked truncated; output writes only captured bytes |
| Syscall/RM failure | Separate return value, errno and RM status | Stale caller status is not returned RM status on syscall failure |
| 0x2080a61d pattern | Raw 12-byte historical/synthetic pattern | No proven physical meaning, selector or mW claim |
| PMUMON clock field | Versioned KHz field / sample count / invalid sentinel | Only interpret a validated retained payload/fixture; no live PMUMON call |
| vBIOS BIT/PERF | Versioned LE pointer table, validated PCIR/header/bounds | A target's bytes alone do not define the target's field semantics |
| GSP feature bits | Named bit0; unknown bits retained | A fixture is not hardware corroboration |

The active tools have no RM allocation/control path. The former claim that rmctl
propagated every live probe failure was false and is superseded by retiring that path.
Synthetic byte tests validate bounds/encoding only. See [VALIDATION.md](../docs/testing.md).

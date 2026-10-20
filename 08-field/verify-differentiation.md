# Capability verification — prior differentiation claims withdrawn
The previous four-of-six proven / business-case-survives verdict was not supported by a
working GA102 payload contract and validated diagnostic outcomes.

| Claim | Current status | Next offline comparison |
|---|---|---|
| Per-rail power | Candidate; firmware strings and Tegra class names are insufficient | Match exact library/driver/firmware consumer and payload schema |
| VRM-zone temperature | Unproven sensor exposure on this board | Versioned sensor topology and exact consumers |
| VF drift | Public offset APIs exist; drift/aging interpretation unvalidated | Compare documented offsets and configuration semantics |
| Rail voltage | Unproven host path/physical readback | Exact VOLT consumer and units, without hardware calls |
| PMU telemetry | Candidate, with public sampling alternatives to compare | nvmlDeviceGetSamples and exact library routines/cadence |
| Clock margin | Host-method lead; not temperature margin and not proof of silicon health | Distinguish clock headroom from thermal margin contracts |

Do not transfer a public Tegra PMU enumeration numerically into a GeForce GSP ABI without
versioned evidence. Presence of a named string, function tag or header is a lead, not a
live capability test. No new wire capture, selector experiment or debugger is authorized.

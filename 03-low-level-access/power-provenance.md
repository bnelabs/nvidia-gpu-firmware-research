# Power provenance — current evidence and unresolved boundary
Earlier completion/opaque-channel/BoardObj discovery claims are superseded.
Historical detailed notes are retained in archive/2026-10-21-pre-constitution.

## Retained observations
The old ground-truth files report board power limits including 420 W and 370 W in
different captures. The 0x2080a61d candidate pattern contains a u32 value of 370000 at +4.
These are separate observations. They do not prove a common quantity, per-rail identity,
units, paired timing, a selector contract, or that P-state caused a limit change.

0x214 is GPU_GET_PROBED_IDS and 0x21b is GPU_GET_PCI_INFO, not rail/limit enumeration.
Their occurrence in a query session does not prove an opaque power-value transport.
An unsuccessful scalar search cannot prove where values live or how they are encoded.

## Offline work
Trace the exact pinned library's getter from its output back through conversions,
callbacks and the demonstrated transport boundary. Export instructions/data with hashes.
Then compare the matching public driver consumer and neighboring library versions.
Distinguish measured draw, requested/default/min/max/enforced limits and policy budgets.
Do not derive sensor or component names from magnitude alone.

The 55-slot RMFunctions JSON is an annotated host-library candidate table. Mixed tags
and nearby strings do not establish one semantic identity for each slot or a GSP method.
All sub_... addresses cited from the x86-64 NVML artifact remain host addresses.

No fresh private control, selector experiment, live debugger or forced workload transition
is permitted. An unresolved power schema is an honest result, not a reason to touch hardware.

# Signal inventory — contracts and candidates
This is a capability map, not a promise that every signal works on the owner's GA102.
Only the collector's fixed documented fields are approved for live monitoring.

| Family | Permitted retained/documented interpretation | Limits |
|---|---|---|
| Identity | UUID, PCI BDF, name, driver and vBIOS strings | Same UUID/context required for comparisons |
| Power | API-specific measured draw and limit fields with their own units | Average/instant/requested/enforced/default are distinct |
| Clocks / P-state | Public MHz and ordinal/formatted Pn; RM mask only in validated offline records | Clock state alone is not a fault diagnosis |
| Thermals | Documented die temperature | Board/VRM/hotspot sensor availability unproven here |
| Fans | Intended percent in the fixed collector | Percent is not measured RPM; per-fan support varies |
| Utilization | Reported percentage under the existing workload | No stress or load generation |
| PCIe | Vendor-reported negotiated width/generation | Idle link downshift is not by itself signal-integrity failure |
| ECC/remap | Existing logs/captures with exact API/status and device support | A header constant does not prove GeForce support or failing VRAM |
| XID | Existing error code and context | Interpret with official documentation; no unique component verdict |
| PMUMON / BoardObj / rails / margin / MMA | Offline RE candidates with source/hash/address provenance | No live custom calls; taxonomy transfer and usefulness remain unproven |

Sources: [NVIDIA queries](https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlDeviceQueries.html),
[XID documentation](https://docs.nvidia.com/deploy/xid-errors/index.html),
and the pinned driver headers identified in [EVIDENCE.md](../EVIDENCE.md).

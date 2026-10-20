# Tooling gap — an evidence question
Before calling a signal proprietary or unavailable, compare the exact documented NVML
API, matching header/library versions and board support. nvmlDeviceGetSamples provides
documented power/clock/utilization sampling types; a missing GetPowerSamples symbol proves
nothing about that API. Clock-offset getters are public.

A signal absent from the current fixed collector is not necessarily absent from NVIDIA
tools. A function name or firmware string is not proof of a safe or working private path.
No claim of a billable diagnostic advantage or physical fault accuracy is validated here.

Next result: an offline capability matrix with documented contract, local symbol evidence,
retained status/result, inferred firmware path and remaining uncertainty. Do not expand live
probes to resolve it. See [LEAD-NEXT.md](../LEAD-NEXT.md).

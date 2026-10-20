# Non-intervention finding notes
This project records observations and hypotheses; it does not run fault-reproduction
experiments, repair a card or certify a component diagnosis.

| Observation in existing evidence | Record | Do not conclude automatically |
|---|---|---|
| High temperature / thermal event | Timestamp, documented threshold/reason and workload context | Cooler failure or VRM hotspot |
| Power/clock limiting | Exact getter, units, requested/enforced distinction | Bad PSU, rail imbalance or damage |
| ECC/remap/XID | Full status, exact device/API, existing error context | A particular VRAM chip or irreversible degradation |
| Fan percent unusual | Intended percentage and supported API | Actual fan RPM, obstruction or bearing failure |
| Low PCIe width/generation | Existing state and expected configuration | Card/slot failure; idle power management may affect link state |
| Undocumented metric candidate | Raw bytes/source path plus competing meanings | A functioning sensor or billable diagnostic capability |

Use official NVIDIA XID descriptions and compare like configurations. Preserve uncertainty.
Do not force load, reset a GPU, change fan/power settings, reseat hardware or issue a private
read to distinguish explanations. Name the missing evidence and continue offline RE.

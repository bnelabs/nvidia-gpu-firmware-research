# Research direction: depth through offline evidence
The objective is a detailed low-level account of NVIDIA GPU firmware, drivers and control
paths under [CONSTITUTION.md](CONSTITUTION.md). Research depth is unrestricted offline;
uncertain hardware interaction is prohibited.

Prioritize source-pinned decompilation, disassembly, dataflow and protocol recovery, public
driver/loader tracing, versioned table decoding, and matched architecture comparisons.
Use CPU-only emulation and synthetic or retained-capture tests. Keep the host library,
kernel driver, transport, boot firmware and runtime firmware as separate address domains.

The first bounded result is one telemetry path explained to its proven boundary with a
hash-keyed artifact, exact source references, units/selectors/status handling and a short
claim matrix. Then map a container and match one function/table across nearby versions.
See [LEAD-NEXT.md](LEAD-NEXT.md) for packet acceptance and [EVIDENCE.md](EVIDENCE.md) for method.

Do not infer a physical power rail from 370000, a sensor from a class name, a new GPU model
from a signature label, or firmware code from a host callback. Do not revisit the P4/P2
discrepancy: RM mask 4 means P2; the public NVML value is an ordinal.

No live debugger, preload tracer, raw IO, undocumented getter, command sweep, setting
change, firmware operation or stress experiment is part of this plan. Ordinary documented
monitoring is a separate, fixed collector. Offline evidence does not certify live safety.

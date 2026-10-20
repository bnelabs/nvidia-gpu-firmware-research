# Constitutional rule: protect the GPU and its running workload

Owner instruction, 2026-10-21: **Never risk the GPU. No intrusive interventions.**
This rule overrides older lab notes, P4/bench exceptions, tool suggestions and research goals.
If an operation's effects or ABI are uncertain, do not try it on hardware. Record the gap
and continue offline. Do not describe an operation as zero-risk merely because it reads.

## Research that is in scope

Decompile, disassemble and reverse engineer firmware, drivers, libraries, bootloaders,
protocols and tools from existing files and legitimate source packages. Parse containers,
recover schemas and call graphs, inspect setters statically, compare versions and
architectures, and emulate isolated code **without physical GPU access**. Preserve all
available detail, including unknowns and conflicting evidence. No need to stop at public
API documentation. The restriction is on interacting with hardware, not understanding it.

Offline execution must have no GPU device passthrough, privileged container access,
hardware service/socket forwarding, `/dev/mem`, PCI resource mounts or remote GPU access.
A VM with a passed-through GPU still operates physical hardware and is not offline.

## The only live activity in scope

Ordinary, low-rate monitoring of the existing configuration through a fixed allowlist of
documented vendor telemetry getters, plus already available log/capture analysis. The
repository collector performs one explicitly requested, UUID-selected `nvidia-smi`
query, without elevation, tracing, retries, plugins or remediation. Its default is a
plan that does not contact a GPU. A per-user lock enforces at least 10 seconds between
attempts and refuses concurrent collection. A new getter requires an exact published ABI
and a reviewed allowlist change; symbol existence is not permission to call it.

Supported monitoring still invokes the driver and may wake hardware or impose overhead.
If even that operational contact is unacceptable, use retained captures only. Nothing in
this repository certifies hardware health or promises mathematically zero risk.

## Prohibited hardware operations

- Custom RM ioctls, GSP RPC, undocumented GETs, selector/command enumeration or fuzzing.
- Raw BAR/MMIO, register/fuse reads, broad PCI configuration dumps, ROM enabling/dumping,
  I2C/SMBus access, debugger memory reads or device-memory mapping.
- LD_PRELOAD/injection, kernel probes, live tracing or instrumentation of GPU processes.
- Firmware loading, swapping, signing experiments, flashing, protection bypasses or SPI work.
- Clock, voltage, power, fan, thermal, persistence, ECC, compute, MIG or link-policy changes.
- Reset, suspend/resume/GC6 experiments, unbind/rebind, driver/module/package changes,
  PCI rescans/removal, fault injection, synthetic load or stress/thermal cycling.
- Attempts to bypass permissions, enable debug modes or use root to obtain more readings.

There is **no bench exception or unsafe override** in this project. Older hardware recipes
are historical research material only. Discovery of spare hardware does not authorize them.
On timeout, API error, inconsistent identity, unfamiliar encoding or instability: stop
collection, preserve evidence and report. Never reset, reconfigure or escalate to recover.

## Evidence rules

Each claim records artifact hash, chip/board, OS, driver/firmware version, source commit,
address domain (file offset / host VA / GPU VA), exact field/units, and uncertainty.
Use: observed bytes, source-decoded, independently corroborated, hypothesis, unresolved,
retracted. Synthetic fixtures test software; they do not verify hardware semantics.

Compare like with like: same architecture and component across nearby versions first;
then other vendors/boards/architectures with differences stated. Prefer NVIDIA source and
manuals, Linux/nouveau/nova source, and independently reproducible research. Two tools
using the same NVML/driver path are consistency checks, not independent physical evidence.

Absence from a public header or a local symbol lookup does not prove absence of a feature.
Strings, plausible values, entropy and function-name proximity do not prove a wire contract,
encryption algorithm, sensor availability, causal diagnosis or complete firmware mapping.

## Enforcement boundary

The retired live prototypes cannot be rebuilt from the active sources. The remaining C
tools consume files and synthetic fixtures only; they contain no device opens or ioctl
forwarding. `tests/check.sh` checks these properties without GPU access.

A repository instruction cannot revoke another process's permissions or stop an already
running external worker. Run that worker in an existing CPU-only environment with no GPU
access, and transfer captures through a separate allowlisted collector. Do not change the
production host to set this up during research. Never claim the worker is contained merely
because this file exists; confirm its environment separately without GPU intervention.

# NVIDIA GPU Firmware Research

This project investigates how NVIDIA's Linux driver, NVML library and GPU
firmware communicate. It contains binary analysis, source comparisons and tools
for inspecting copied firmware and recorded driver traffic.

The most detailed work follows performance-state telemetry through the 615.71.09
driver and GSP firmware. Other studies cover firmware containers, bootloaders,
vBIOS tables and differences between GPU generations. Each finding links back
to the bytes and source version used to establish it.

## Findings

- **An Xid79 recovery restored PCI access but left early firmware boot incomplete.**
  The copied debug FWSEC image exposes progress writers and failure branches;
  a working no-reboot recovery remains unproven.
  [Read the boot investigation](research/2026-10-21-gfw-boot/README.md).
- **NVML can read a shared cache before issuing a control request.** The retained
  implementation has a five-attempt reader and accepts a valid timestamp without
  checking its age. [Read the dispatch analysis](research/2026-10-21-pstate-dispatch/README.md).
- **One firmware P-state path returns a table-entry field.** The recovered
  code traces that field to a tagged record in a serialized table. The source
  of the table's bytes and the GPU's runtime selection are still unknown.
  [Follow the value through the firmware](research/2026-10-21-record-producer/README.md).
- **Two nearby releases contain identical GA102 boot components.** The decoded
  PROD GSP boot image and descriptor match byte-for-byte in 615.71.09 and
  615.78.08. [See the comparison](research/2026-10-21-offline/README.md).
- **Recent GPU memory research offers useful offline analysis tools.** We
  reviewed GeForge, GDDRHammer and GPUBreach, checked their file utilities, and
  compared their legacy GSP queue assumptions with 615 source. They provide
  no demonstrated recovery for this boot failure.
  [Read the source review](research/2026-10-22-memory-research/README.md).

These findings describe particular binaries and code paths. They do not establish
complete firmware coverage or the physical origin of every reported value.
The [control-plane map](docs/control-plane.md) connects the results, and
[corrections](CORRECTIONS.md) records earlier claims that did not hold up.

## Use the tools

The analysis tools read copied files and synthetic fixtures. On Linux, the
included Bubblewrap wrapper runs them without GPU devices, network access or
host service sockets:

```sh
# Run the offline test suite.
bash scripts/run_cpu_only.sh bash tests/check.sh

# Inspect a copied firmware container.
bash scripts/run_cpu_only.sh python3 scripts/inventory_firmware.py firmware-store/copied-gsp.elf

# Decode the BIT directory and performance-table pointers in a copied vBIOS.
bash scripts/run_cpu_only.sh python3 scripts/parse_vbios_bit.py firmware-store/copied.rom --perf
```

The test suite needs Python 3, a C compiler and Capstone. Firmware emulation also
uses Unicorn. See [testing and reproduction](docs/testing.md) for dependencies
and commands. Firmware binaries and vendor source trees are kept outside Git;
the reports record their hashes and provenance.

## Repository guide

| Location | Contents |
|---|---|
| [research/](research/) | Reproducible analyses, raw disassembly, hashes and emulation results |
| [docs/control-plane.md](docs/control-plane.md) | The telemetry path recovered so far |
| [docs/sources.md](docs/sources.md) | NVIDIA, Linux and independent source references |
| [scripts/](scripts/) and [tests/](tests/) | File parsers, decoders, emulators and regression checks |
| `01-generations/` through `10-monitor/` | Earlier topic studies, captures and prototypes; consult the correction notices |
| [archive/](archive/) | Historical reports and superseded workflow notes |

Reverse engineering here uses copied artifacts, retained captures and CPU-only
execution. Live activity is restricted to the documented monitoring collector;
its default produces a plan without contacting a GPU. Custom hardware probes,
live tracing, settings changes and firmware operations are outside the project's
scope. The full rule is in [CONSTITUTION.md](CONSTITUTION.md).

For research contributions, include the artifact hash, source commit, address
domain, reproduction command and remaining uncertainty. The
[evidence protocol](EVIDENCE.md) describes the record format.

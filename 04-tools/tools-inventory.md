# Tools Inventory — NVIDIA Consumer GPU Firmware & Low-Level Control

Working catalog of tools for the lab (owner-hardware research only). 2026-10-15; driver
context: open KMD 615.71.09 on RTX 3090 (GA102). Rows ordered by workflow stage: source &
documentation → firmware images & parsers → userspace control → kernel tracing → MMIO/RE →
flash & recovery → virtualization/benches. Every mutating tool (flashers, pokers) is for the
test bench, never the production rig. Do not commit firmware binaries to the repo — store
URL + version + SHA-256 only (repo ground rule).

## TL;DR

- The two NVIDIA-maintained anchors are [open-gpu-kernel-modules](https://github.com/NVIDIA/open-gpu-kernel-modules) (UAPI headers, RM ioctl numbers, GSP plumbing) and [open-gpu-doc](https://github.com/NVIDIA/open-gpu-doc) (GA100/GA102/Turing/Volta register manuals, vBIOS table docs).
- GSP firmware (`gsp_ga10x.bin` / `gsp_tu10x.bin`) is parsed by [airlied/gsp-parse](https://github.com/airlied/gsp-parse) (headers → JSON/Rust) and extracted/booted by [NV-GSP-Bootloader](https://github.com/yunjie-deng/NV-GSP-Bootloader); the official container layout is documented in the open modules' `nouveau/` extractor + spreadsheet.
- A from-scratch RM ioctl client is entirely feasible — [cuda_ioctl_sniffer](https://github.com/geohot/cuda_ioctl_sniffer) proves the pattern — enabling the repo's planned `rmctl` prototype.
- vBIOS flashing: stock `nvflash` (TechPowerUp) vs community forks [nvflashk](https://github.com/notfromstatefarm/nvflashk) and [B47741/nvflash](https://github.com/B47741/nvflash) (board-ID/signature bypasses — destructive, bench only).
- Chip-off/bricked-card recovery: CH341A or Raspberry Pi SPI programmer with [flashrom](https://www.flashrom.org/).
- Observation stack: `nvidia-smi`/NVML/[pynvml](https://github.com/gpuopenanalytics/pynvml), bundled `nvidia-debugdump`, bpftrace/ftrace on `nvidia_ioctl`, and [gVisor's ioctl_sniffer](https://pkg.go.dev/gvisor.dev/gvisor/tools/ioctl_sniffer).
- Windows-side control surfaces: [GPU-Z](https://www.techpowerup.com/gpu-z/) and the now-official [NVIDIA/nvapi](https://github.com/NVIDIA/nvapi) SDK repo.
- Safe MMIO benches: `uio_pci_generic` or VFIO/QEMU on an unbound spare GPU; never the production card.
- nouveau + Nova (Rust) give an independent driver stack for cross-checking vendor behavior.

## Tool table

| Tool | What it does | Where to get it | Notes |
|---|---|---|---|
| open-gpu-kernel-modules | Source of nvidia.ko/modeset/uvm/drm kernel interface layers + full RM UAPI headers (`nv_escape.h`, `nvos.h`, `ctrl/`) | [NVIDIA/open-gpu-kernel-modules](https://github.com/NVIDIA/open-gpu-kernel-modules) | Repo is a per-release snapshot; main = 615.78.08, rig runs 615.71.09 — version-lock headers to installed driver. Turing+ support; Blackwell needs this stack |
| open-gpu-doc | Register manuals (GA100 ×17 units, GA102 ×7 units, Turing, Volta), vBIOS `BIOS-Information-Table`, `MemoryClockTable`, `MemoryTweakTable`, DCB, Devinit, Falcon-Security | [NVIDIA/open-gpu-doc](https://github.com/NVIDIA/open-gpu-doc) | No Ada/Blackwell register manuals published (verified 2026-10) |
| nouveau (nvkm) | Independent in-tree kernel driver; GSP firmware support since Linux 6.7; `nvkm/subdev/gsp/rm/{r535,r570}` RM abstraction | [nouveau.freedesktop.org](https://nouveau.freedesktop.org/) · [kernel tree](https://github.com/torvalds/linux/tree/master/drivers/gpu/drm/nouveau) | Debugfs under `/sys/kernel/debug/dri/<N>/` (e.g. `pstate`); great cross-reference for RM/GSP behavior |
| Nova (nova-core / nova-drm) | Rust rewrite for GSP GPUs (Turing+); nova-core in mainline since 6.15; 7.4 adds GPU-info ioctl, VRAM buddy allocator, BAR1 CPU access | [rust-for-linux.com/nova-gpu-driver](https://rust-for-linux.com/nova-gpu-driver) · [drm-rust-next](https://gitlab.freedesktop.org/drm/rust/kernel) | Planned Nova-Core-based VFIO driver for vGPUs; TODO list at docs.kernel.org/gpu/nova/core/todo.html |
| NVIDIA linux-firmware fork | GSP/other firmware images mirrored for redistribution | [NVIDIA/linux-firmware](https://github.com/NVIDIA/linux-firmware) | Cross-check image versions/hashes vs `/lib/firmware/nvidia/<ver>/` |
| nouveau firmware extractor | Extracts GSP/falcon binaries from open-modules sources; `nouveau_firmware_layout.ods` documents the `gsp*.bin` container | [open-gpu-kernel-modules/nouveau/](https://github.com/NVIDIA/open-gpu-kernel-modules/tree/main/nouveau) | Official (vendor) description of the firmware container — first stop for a parser |
| gsp-parse | Parses NVIDIA SDK headers, emits JSON of GSP-facing structs + Rust generator; for the "unstable ABI" GSP firmware interface | [airlied/gsp-parse](https://github.com/airlied/gsp-parse) | By Dave Airlie; pairs with nouveau GSP work |
| NV-GSP-Bootloader | Extracts bin/ELF from `gsp_ga10x.bin`, captures WPR metadata via live kprobe, emulates the GSP bootloader | [yunjie-deng/NV-GSP-Bootloader](https://github.com/yunjie-deng/NV-GSP-Bootloader) | Emulation runs on captured artifacts — no GPU needed; kprobe capture step is bench-only |
| envytools (nva, envydis) | Classic RE toolkit: `nva` register/ROM/VBIOS tools, docs, and envydis disassemblers incl. Falcon ISA | [envytools/envytools](https://github.com/envytools/envytools) | Pre-GSP lineage (PDAEMON/falcons); still the reference for falcon firmware |
| envytools documentation | HW docs: MMIO ranges, power/thermal/clock mgmt, PDAEMON MMIO access | [envytools.readthedocs.io](https://envytools.readthedocs.io/en/latest/index.html) | Use to annotate BAR0 unit maps during bench walks |
| devregs | Simple MMIO read/write CLI used across nouveau-era research | [GitHub search: devregs nvidia](https://github.com/search?q=devregs+nvidia) | Several forks; pick/audit code before running [VERIFY canonical repo] |
| nvflash (original) | NVIDIA vBIOS flasher (DOS/Windows/Linux); ROM backup + flash with board checks | [TechPowerUp download](https://www.techpowerup.com/download/nvidia-nvflash/) | Keep a factory ROM backup per card; refuses mismatches by design |
| nvflashk | Patched nvflash: flashes nearly any signed vBIOS (board-ID/signature checks relaxed, up to 4xxx+) | [notfromstatefarm/nvflashk](https://github.com/notfromstatefarm/nvflashk) | Destructive; bench + PSU headroom + recovery plan ([TechPowerUp thread](https://www.techpowerup.com/forums/threads/nvflashk-flash-any-bios-to-nvidia-gpus-safe-board-id-bypass-up-to-4xxx-series.312608/)) |
| B47741/nvflash | Alternative patched nvflash ("flash (almost) any vBIOS to (almost) any GPU") | [B47741/nvflash](https://github.com/B47741/nvflash) | Same warnings; verify checksums of any downloaded fork |
| GPU-Z | Windows GUI: clocks, sensors, vBIOS version, ROM dump/export | [TechPowerUp GPU-Z](https://www.techpowerup.com/gpu-z/) | Easiest cross-check of vBIOS version vs our `94.02.42.00.f4` |
| TechPowerUp vBIOS database | Searchable public vBIOS archive by PCI subsystem/IDs | [techpowerup.com/vgabios](https://www.techpowerup.com/vgabios/) | Compare candidate ROMs against rig's MSI GA102 (1462:3882); never flash on prod |
| nvidia-debugdump | Bundled diagnostic: dumps internal GPU/NVLOG state (binary, needs NVIDIA tools to read) | Bundled with driver · [README ch. 29](https://download.nvidia.com/XFree86/Linux-x86_64/565.77/README/nvidia-debugdump.html) | Invoked by `nvidia-bug-report.sh`; rides the root-only `NV_ESC_RM_LOCKLESS_DIAGNOSTIC` path |
| nvidia-smi | Official CLI over NVML: telemetry, XIDs, XML/CSV output | Bundled · [NVML docs](https://developer.nvidia.com/nvidia-system-management-interface) | Ground-truth capture format in repo `06-ground-truth/`; XML exposes `<gsp_firmware_version>` |
| NVML + nvidia-ml-py / pynvml | C API + Python bindings for the same telemetry surface | [pypi nvidia-ml-py](https://pypi.org/project/nvidia-ml-py/) · [gpuopenanalytics/pynvml](https://github.com/gpuopenanalytics/pynvml) | Scriptable passive monitoring of the production rig |
| NVAPI (official SDK repo) | Public NVAPI headers/libs (Windows control plane: clocks, power, sensors, infoROM) | [NVIDIA/nvapi](https://github.com/NVIDIA/nvapi) · [docs](https://docs.nvidia.com/nvapi/index.html) | Now vendor-published — replaces most community header forks |
| kdschlosser/nvapi (Python) | Python NVAPI port incl. reverse-engineered structs (e.g. `NV_GPU_CONNECTOR_INFO`) | [kdschlosser/nvapi](https://github.com/kdschlosser/nvapi) | Community RE; useful reference for undocumented NVAPI surface |
| bpftrace | eBPF one-liners: `kprobe:nvidia_ioctl` to log RM escapes per process; nouveau `nvkm_gsp*` tracing | [bpftrace/bpftrace](https://github.com/bpftrace/bpftrace) | Read-only observation; symbol names vary per build — enumerate via `/proc/kallsyms` first |
| ftrace / trace-cmd | Kernel function tracing of `nvidia_*`/`nvkm_*` call graphs | [kernel ftrace docs](https://www.kernel.org/doc/html/latest/trace/ftrace.html) | Low-overhead alternative to bpftrace for long captures |
| gVisor ioctl_sniffer | Profiles all NVIDIA ioctl traffic (RM alloc/control) of a GPU workload | [pkg.go.dev ioctl_sniffer](https://pkg.go.dev/gvisor.dev/gvisor/tools/ioctl_sniffer) | Userspace-side sniffer — no kernel module needed; good for mapping NVML→RM calls |
| cuda_ioctl_sniffer | Working raw RM client: `NVOS21/54` allocs+controls, pushbuffer kicks, BAR1 via sysfs | [geohot/cuda_ioctl_sniffer](https://github.com/geohot/cuda_ioctl_sniffer) | Reference implementation for the planned `rmctl`; compiles against open-modules headers |
| vgpu_unlock-rs | Interception layer for NVIDIA vGPU ioctls (documents NVOS struct layout + control patching) | [mbilker/vgpu_unlock-rs](https://github.com/mbilker/vgpu_unlock-rs) | Included as UAPI documentation/RE reference; respect license/ToS when studying |
| Fossies Doxygen (open KMD) | Cross-referenced source browser for open-gpu-kernel-modules (e.g. `escape.c`) | [fossies.org dox](https://fossies.org/dox/NVIDIA-open-gpu-kernel-modules-580.82.07/escape_8c.html) | Fast navigation without cloning |
| Elixir Bootlin | Cross-referenced Linux tree (nouveau, Nova, nvkm) | [elixir.bootlin.com](https://elixir.bootlin.com/linux/latest/source/drivers/gpu) | Track GSP/RM refactor locations across kernel versions |
| uio_pci_generic | Map BARs of an unbound PCI device into userspace | [kernel uio howto](https://www.kernel.org/doc/html/latest/driver-api/uio-howto.html) | Bench-only MMIO path: `resource0` = BAR0 (16 MB on GA102) |
| VFIO + QEMU | IOMMU-safe device assignment; GPU into VM as test bench; future Nova vGPU target | [kernel VFIO docs](https://www.kernel.org/doc/html/latest/userspace-api/vfio.html) · [QEMU](https://www.qemu.org/) · [ArchWiki passthrough](https://wiki.archlinux.org/title/PCI_passthrough_via_OVMF) | ROADMAP P4 environment for all mutating experiments |
| flashrom | SPI flash read/write/verify for BIOS/ROM chips; supports CH341A, linux_spi (Pi), many programmers | [flashrom.org](https://www.flashrom.org/) | Chip-off recovery path; verify against saved dump before any write |
| CH341A programmer | Cheap USB SPI programmer + SOIC8 clip for the card's vBIOS EEPROM | [guide (jensd.be)](https://jensd.be/980/linux/bios-or-spi-programming-on-windows-or-linux-using-a-ch341a) | Clip off-card only, chip unpowered; beware old 3.3 V/5 V CH341A revisions |
| Raspberry Pi (linux_spi) | GPIO bit-bang SPI programmer for flashrom; good for 1.8 V chips with level shifting | [flashrom](https://www.flashrom.org/) · [CH341A context](https://github.com/semaf/CH341-USB-EEPROM-Flash-BIOS-Programmer) | Dedicated bench Pi; never share with other duties during flashing |
| NVIDIA XID reference | Official decode of XID error codes (crash/hang triage) | [docs.nvidia.com XID errors](https://docs.nvidia.com/deploy/xid-errors/index.html) | Correlate bench experiments' failures with RM/GSP state |

## Creative techniques

- **Header-driven tooling**: compile a minimal `rmctl` directly against row-1 headers so command IDs, structs, and privilege flags can never drift from the installed driver version.
- **Sniff before you code**: run gVisor's `ioctl_sniffer` (or bpftrace on `nvidia_ioctl`) around `nvidia-smi -q` to harvest exactly which RM controls NVML uses, then reuse them in your own tooling.
- **Firmware pipeline**: `nouveau/` extractor → `gsp-parse` JSON → string-table diff of `gsp_ga10x.bin` across 615.71.09/615.78.08 gives a GSP-RPC changelog without powering anything extra.
- **Two-driver triangulation**: capture the same telemetry (clocks, power, fan, vBIOS strings) via NVML, nouveau debugfs on a bench boot, and raw RM controls — disagreements localize vendor-side gating.
- **Recovery-first flashing**: for any vBIOS experiment, prepare chip-off tooling (CH341A/Pi + flashrom) and a verified ROM backup *before* the first nvflashk run.

## Open questions

- [VERIFY] Maintenance status/official home of `nvflashk` (GitHub forks move; confirm the currently-trusted repo and its provenance before trusting any binary).
- [VERIFY] Canonical `devregs` repository URL (multiple historical forks).
- [VERIFY] Public tooling for the NVLOG binary produced by `nvidia-debugdump` (NVIDIA-internal today; is a community parser viable?).
- [VERIFY] bpftrace-safe GSP RPC symbols in 615-series builds (`/proc/kallsyms` enumeration on the rig needed before scripting).
- [VERIFY] Whether QEMU/VFIO vGPU on consumer GA102 can ride the open KMD path without vendor vGPU license blobs.
- [VERIFY] Current best GSP firmware emulator: NV-GSP-Bootloader vs anything newer in the nouveau/Nova ecosystem.

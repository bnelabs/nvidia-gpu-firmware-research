> HISTORICAL / SUPERSEDED. Not an authorized runbook. Claims may be retracted. Read current CONSTITUTION.md and CORRECTIONS.md at the repository root.

# TECHNIQUES — creative acquisition, analysis & control methods

Status: [SEED] idea, needs prototyping · [PROVEN] known prior art · [RIG] executable on the lab
rig today. Risk: 🟢 read-only · 🟡 needs unbound GPU/VM · 🔴 persistent/flash, brick risk.

**Standing rule: the production GPU is never the experiment target.** 🟢 items are its ceiling.

## T1 · Harvest GSP firmware straight from the driver stack — 🟢 [RIG→P2]
Since Turing, most resource-manager logic lives in `gsp.bin`, a RISC-V firmware image the
driver loads into the GPU. It ships unencrypted with every driver and installs under
`/lib/firmware/nvidia/<version>/gsp.bin` [VERIFY path per distro/version].
```bash
ls -l /lib/firmware/nvidia/*/gsp*.bin; sha256sum /lib/firmware/nvidia/*/gsp*.bin
# or extract without installing:
sh NVIDIA-Linux-x86_64-615.71.09.run -x        # .run = makeself archive
7z x <windows-driver>.exe                       # Windows package is extractable too
```
Power move: you get the *actual processor image* for every released driver — a time machine of
NVIDIA's control plane. Binaries stay out of git; record URL + sha256.

## T2 · Version-diff `gsp.bin` and vBIOS binaries — 🟢 [SEED→P2]
Collect N versions (T1), then diff (radare2 / binutils / python struct): changed regions mark
behavior changes (power mgmt, RPC handlers). Mine strings and embedded metadata/symbols
[VERIFY: community GSP parsers extract symbol-ish sections]. Same technique locates vBIOS
power/perf tables by diffing partner BIOSes of the same chip.

## T3 · open-gpu-kernel-modules as a protocol dictionary → `rmctl` — 🟢/🟡 [SEED→P3]
The open modules publish the *entire* RM control surface: `src/common/sdk/nvidia/inc/ctrl/*.h`
(NVOS classes 0x20xxxxx) plus the UAPI (`nv_ioctl.h`, `nv_escape.h`). Every NVML/NVAPI action
ends in one of these controls. A userspace tool that packs those structs and issues ioctls on
`/dev/nvidiactl` + `/dev/nvidia0` reaches NVML-or-better control (clocks, power, fan, thermal
policy, infoROM…) [VERIFY abilities/privilege model].

## T4 · Live-trace the driver: ftrace / kprobes / bpftrace — 🟢 [RIG]
Open KMD = traceable symbols. Record every RM control and GSP RPC in real time while
`nvidia-smi` acts — the cheapest protocol sniffer for this stack:
```bash
sudo bpftrace -l 'kprobe:nv*' | head -50
sudo bpftrace -e 'kprobe:nv* { @[func] = count(); }'   # [VERIFY exact symbol names on 615.x]
```
Read-only wrt the GPU; safe alongside inference (tracing adds negligible kernel overhead).

## T5 · GSP RPC visibility — 🟡 [SEED→P3]
RM↔GSP talk over shared-memory queues; message structs are public in open modules and
re-implemented by nouveau (nvkm GSP). Community RPC loggers/patches exist [VERIFY: e.g. GSP RPC
recorder by mstoeckl]. Long-term: userspace GSP RPC client on T3's structs.

## T6 · Registers from userspace — safely — 🔴/🟡 [SEED→P3]
open-gpu-doc publishes register manuals ONLY for Volta/Turing/Ampere (GA100 broadest = 17 units,
GA102 = 7-unit subset; **no Ada/Blackwell manuals** — verified against the open-gpu-doc tree
2026-10-15). For GSP/falcon registers, the per-arch `swref/published/*/dev_gsp.h` headers inside
open-gpu-kernel-modules (incl. rubin/gr100) are the real documentation. Raw BAR0 on the
*production* GPU is forbidden (RM owns the device). On an unbound spare card: unbind driver →
bind `uio_pci_generic` (or vfio-pci) → mmap `resource0` → poke per devregs-style definitions.
envytools lineage (nva, envydis Falcon disassembler) is the classic toolchain.

## T7 · vBIOS corpus mining & partner diffing — 🟢 [PROVEN method]
TechPowerUp vBIOS DB + board-partner update zips = thousands of ROMs. Diff two BIOSes for the
same chip on different boards to *auto-locate* power/perf tables instead of blind hex-editing.
Side project: a BIT-directory parser (NVIDIA's ROM table-of-contents).

## T8 · Flashing sandbox + recovery drill — 🔴 [P4, test bench only]
Practice on disposable hardware (VFIO/QEMU VM or spare card): nvflash + community forks
(nvflashk et al. [VERIFY current best fork]), multi-BIOS switches, and the recovery path:
read/write the SPI NOR with CH341A or Raspberry Pi + SOIC8 clip. Rule: never first-flash a
single-BIOS card or a laptop; always dump-before-flash.

## T9 · PCI config-space fingerprinting — 🟢 [RIG]
`lspci -xxx -s <bdf>` dumps the full 4 KiB config space: caps, power-management state,
strap-adjacent registers. Cheap, read-only, great cross-generation comparison data
(actual straps live in BAR0/fuses [VERIFY]).

## T10 · Sanctioned deep control: NVML → nvidia-smi, NvAPI on Windows — 🟢 [RIG]
`nvidia-smi -lgc/-lmc/-pl/-r`, `-q -d SUPPORTED_CLOCKS,PERFORMANCE,POWER`; pynvml for scripting;
NvAPI reaches deeper on Windows (OC Scanner, voltage offsets where the gen allows [VERIFY]).
Map every sanctioned action to its underlying RM control (T3) to know exactly what changed.

## T11 · Prior-art mining: the LHR saga & OC community — 🟢 [PROVEN]
The 2021–22 Lite-Hash-Rate story (vBIOS + driver + GSP interplay, community unlocks) is
crowd-sourced reverse engineering of exactly this stack. Overclocking forums documented
30-series power-table hex offsets. Harvest, cite, re-verify against current drivers.

## T12 · Ground-truth rig discipline — 🟢 [RIG]
The RTX 3090 here runs production inference. `scripts/capture_state.sh` is read-only; run it to
append a timestamped snapshot (nvidia-smi XML, driver params, GSP firmware hashes, lspci).
Mutating experiments wait for P4 on disposable hardware. Every capture gets a LOG.md entry.

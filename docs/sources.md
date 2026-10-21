# Sources

Findings use immutable source revisions wherever possible. The manifests beside
each analysis record file hashes, paths and commits. Public source provides
format definitions and comparisons; a matching name alone does not establish
the behavior of a closed firmware binary.

## NVIDIA

The [615.71.09 open kernel source](https://github.com/NVIDIA/open-gpu-kernel-modules/tree/61dcc93722ecb418bb5f2e00923f05b4b8051dd1)
is the primary comparison for the retained NVML and GSP RM artifacts. In
particular:

- [GPU object creation and internal RM API](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/61dcc93722ecb418bb5f2e00923f05b4b8051dd1/src/nvidia/src/kernel/gpu/gpu.c)
- [P-state control definitions](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/61dcc93722ecb418bb5f2e00923f05b4b8051dd1/src/common/sdk/nvidia/inc/ctrl/ctrl2080/ctrl2080perf.h)
- [User shared-data format](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/61dcc93722ecb418bb5f2e00923f05b4b8051dd1/src/common/sdk/nvidia/inc/class/cl00de.h)
- [NVOC runtime and method lookup](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/61dcc93722ecb418bb5f2e00923f05b4b8051dd1/src/nvidia/src/libraries/nvoc/src/runtime.c)

The nearby release comparison uses
[615.78.08 at `ca2d03e`](https://github.com/NVIDIA/open-gpu-kernel-modules/tree/ca2d03e6fafd4d4b56b383497d931c25b283bfcf).
That revision is not exact source for 615.71.09.

The vBIOS parser follows NVIDIA's
[BIOS Information Table specification](https://download.nvidia.com/open-gpu-doc/BIOS-Information-Table/1/BIOS-Information-Table.html).

## Linux and independent work

Linux comparisons are pinned to
[`7d0a66e`](https://github.com/torvalds/linux/tree/7d0a66e4bb9081d75c82ec4957c50034cb0ea449):

- [nouveau r535 GSP control transport](https://github.com/torvalds/linux/blob/7d0a66e4bb9081d75c82ec4957c50034cb0ea449/drivers/gpu/drm/nouveau/nvkm/subdev/gsp/rm/r535/ctrl.c)
- [nouveau vBIOS performance-table parser](https://github.com/torvalds/linux/blob/7d0a66e4bb9081d75c82ec4957c50034cb0ea449/drivers/gpu/drm/nouveau/nvkm/subdev/bios/perf.c)
- [Nova GSP source](https://github.com/torvalds/linux/blob/7d0a66e4bb9081d75c82ec4957c50034cb0ea449/drivers/gpu/nova-core/gsp.rs)

The independent [envytools power-table parser](https://github.com/envytools/envytools/blob/f102b82381f3f11cee113d16374c87091db039d9/nvbios/power.c)
is pinned to `f102b82381f3f11cee113d16374c87091db039d9`. Its vBIOS encodings
are compared separately from the private firmware's internal records.

For instruction decoding, the analyses use the
[RISC-V ISA reference](https://docs.riscv.org/reference/isa/v20260120/unpriv/rv32.html).
The ISA explains instruction behavior, not NVIDIA-specific object meanings.

The older [source collection](../archive/2026-10-21-workflow-notes/SOURCES.md)
contains additional literature leads. Its historical verification labels do not
replace the artifact-specific checks in the newer reports.

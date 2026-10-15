# SOURCES — master index (seed; wave-1 agents extend this)

## Primary (NVIDIA)
- https://github.com/NVIDIA/open-gpu-kernel-modules — open kernel modules; UAPI + RM control headers; GSP RPC structs
- https://github.com/NVIDIA/open-gpu-doc — hardware/register manuals (GA100/GA10x full; Ada/Blackwell partial)
- https://www.nvidia.com/en-us/drivers/ — driver packages (firmware warehouse: gsp.bin, nvflash, tools)

## Community / drivers
- https://gitlab.freedesktop.org/drm/nouveau — nouveau (nvkm GSP implementation)
- envytools (nva, envydis falcon disassembler) — classic RE toolchain [pin exact repo in wave 1]
- https://www.techpowerup.com/vgabios/ — vBIOS database (corpus for diffing)
- NvAPI open header projects [pin in wave 1]

## Tracing / tooling
- https://github.com/bpftrace/bpftrace — live kernel tracing of open KMD
- QEMU/VFIO — experiment isolation

## Status
Wave-1 research agents (2026-10-15) will append verified, per-topic source lists here.

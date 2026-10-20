# NVIDIA GPU control plane — evidence-bounded map
This replaces the earlier definitive/complete claim. See [CORRECTIONS.md](CORRECTIONS.md).
All further protocol recovery is offline.

## Components and demonstrated boundaries
| Component | What the repository can support | What remains unproven |
|---|---|---|
| Application / documented NVML | Public getter contracts; historical outputs/captures | Present health and universal board support |
| Host libnvidia-ml | Reported x86-64 call sites, strings, dispatch tables and arithmetic in SHA-256 283793c0c30dc32f87c0e9fc9b5326fe764bad156e61afa3e997684c47b29a95 | Reproducible disassembly excerpts for every claimed function attribution |
| Kernel RM | Public allocation/control/dispatch structures at source commit ca2d03e6fafd4d4b56b383497d931c25b283bfcf | Exact compatibility with installed 615.71.09 for each private command |
| Kernel ↔ GSP | Public transport/serialization code provides source-level routes | Exact private request to firmware consumer mapping for each claimed signal |
| GSP / FMC / engine firmware | Retained inventories and offline structural RE leads | Complete dispatch, policy, key provenance and all-generation behavior |

A function pointer in host code is still a userspace call until its implementation's
syscall/transport is demonstrated. sub_1117F0, off_2D1180 and globals 0x1268400 in prior
analysis belong to the host library artifact; do not label them RISC-V firmware addresses.
The slot JSON is a host-library candidate inventory, not a proven BoardObj wire schema.

## Corrected command identities
0x00000214 = NV0000_CTRL_CMD_GPU_GET_PROBED_IDS.
0x0000021b = NV0000_CTRL_CMD_GPU_GET_PCI_INFO.
Both are in the [pinned NVIDIA GPU discovery header](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/ca2d03e6fafd4d4b56b383497d931c25b283bfcf/src/common/sdk/nvidia/inc/ctrl/ctrl0000/ctrl0000gpu.h).
Their appearance during an NVML query does not make them the power-value carrier.
The prior opaque-limit-channel explanation is withdrawn pending an independently traced path.

## Contracts worth retaining
| Observation/domain | Current interpretation |
|---|---|
| RM currPstate, ctrl2080perf.h | One-hot mask: 1=P0, 4=P2, 256=P8; undefined/composite values remain raw |
| Public NVML nvmlPstates_t | Ordinal enum; do not run the RM mask decoder on it |
| PMUMON activeGpcClkFreqKHz | Field-specific KHz contract; invalid sentinel and sample bounds matter |
| 0x2080a61d retained 12-byte pattern | Raw candidate only; units, selector and physical meaning unresolved |
| NVML power API vs nvidia-smi | Respect each API's units; agreement through the same driver is a consistency check |
| BoardObj names / Tegra taxonomy | Useful static leads; no proof of a working GA102 sensor read path |

## Current tools
rmctl reads regular capture files or decodes an enum; sniffer2 decodes supplied record
buffers; fake_rm supplies synthetic bytes. None performs driver communication.
The fixed monitoring collector is the only live entry point; it has no experimental mode.
No statement here claims every arrow, table, function or unit is completely verified.

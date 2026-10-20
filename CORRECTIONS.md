# Corrections and retractions — 2026-10-21
These corrections override conflicting historical prose, tables and log entries.
They were made without accessing a GPU. The owner permits deep offline RE, not experiments
against physical hardware. See [CONSTITUTION.md](CONSTITUTION.md).

| Earlier claim | Current disposition | Evidence / next offline step |
|---|---|---|
| Read-only means harmless / zero impact | Retracted. Reads may wake hardware, contend or have device-specific effects. No custom hardware probes. | PCI utilities explicitly warn about some broad config reads; [upstream manual](https://github.com/pciutils/pciutils/blob/master/lspci.man). |
| lspci -xxx is a 4 KiB dump | Incorrect: conventional config dump; -xxxx is the extended 4096-byte mode. Neither belongs in this collector. | Same upstream manual. Historical filenames retained unchanged as evidence. |
| 0x214 enumerates BoardObj power objects | Retracted: NV0000_CTRL_CMD_GPU_GET_PROBED_IDS, a GPU discovery operation. | [Pinned NVIDIA header](https://github.com/NVIDIA/open-gpu-kernel-modules/blob/ca2d03e6fafd4d4b56b383497d931c25b283bfcf/src/common/sdk/nvidia/inc/ctrl/ctrl0000/ctrl0000gpu.h). |
| 0x21b detail records are rail/limit values or generic GPU state | Retracted: NV0000_CTRL_CMD_GPU_GET_PCI_INFO. Do not infer board-object enumeration from the discovery sequence. | Same pinned header. |
| sub_1117F0 / globals 0x1268400 are GSP firmware findings | Incorrect address-domain attribution. The cited analysis was of the host x86-64 libnvidia-ml artifact. | Library SHA-256 283793c0c30dc32f87c0e9fc9b5326fe764bad156e61afa3e997684c47b29a95; re-export disassembly offline for verification. |
| Every control-plane boundary, function and unit is fully verified | Retracted. A callback is not proof of the syscall/RPC/firmware consumer. | Retain evidence per boundary, list missing links; do not fill them with names. |
| RM raw 4 means P4 | Incorrect: the pinned RM one-hot enum encodes P2 as 4 and P8 as 256. | ctrl2080perf.h at ca2d03e. CPU-only decoder test. |
| NVML performance state is one-hot | Incorrect: the public nvmlPstates_t is an ordinal enum. Do not apply RM mask decoding to NVML output. | [NVIDIA device enums](https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlDeviceEnums.html). |
| 0x2080014a is the P-state source | Retracted in earlier work: the recorded +4 was an input selector, not a P-state measurement. | Retained pre/post trace; no new hardware call. |
| 0x2080a61d +4 = verified live power limit / per-rail power | Unresolved. Byte pattern and plausible magnitude do not prove units, selector, direction, physical quantity or safe call contract. | Decode the pinned library offline; do not call the control again. |
| Absence of nvmlDeviceGetPowerSamples proves no public power sampling | Invalid comparison. Public nvmlDeviceGetSamples supports power sampling types. Device support and cadence remain separate questions. | [NVIDIA queries](https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlDeviceQueries.html), [sampling enum](https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlDeviceStructs.html). |
| ApplicationsClocks plural / fan v1-v2 errors prove the public header is wrong | Unestablished. GetApplicationsClock singular is documented; wrong ctypes signatures invalidate conclusions about ABI/support. | Compare exact installed header/library versions offline; do not guess signatures live. |
| Clock VF offset is direct rail-voltage readback / aging detection | Incorrect inference. Clock offset APIs are public and expose configured offsets; they do not establish measured volts or degradation. | NVIDIA documented clock-offset APIs; causal health inference requires separate evidence. |
| Tegra BoardObj class numbers prove GA102 sensor exposure | Unproven cross-platform transfer. Names/strings/classes are RE leads, not a working GeForce wire contract. | Compare exact architecture/version implementations offline. |
| Fan percent is a tachometer RPM measurement | Incorrect. Keep requested/intended fan percent distinct from an explicitly supported RPM/tach path. | NVIDIA fan API contracts; collector preserves percent. |
| XID code determines a failed physical component | Unsupported. Error classes are triage context, not unique diagnoses. Prior hand-written code labels need rechecking. | [NVIDIA XID documentation](https://docs.nvidia.com/deploy/xid-errors/index.html). |
| Entropy proves AES-128-CBC and all key locations | Unsupported. Compression, packing and encryption can all raise entropy; public field definitions are not extracted key material. | Loader format, exact crypto consumer and reproducible offline artifact analysis required. |
| 24–48-byte UCODE_DESC is the larger LSF_UCODE_DESC carrying AES keys | Inconsistent size/type attribution; withdrawn. | Map the exact versioned descriptor before interpreting fields. |
| Static host-source search proves no GC6 vulnerability, reachability or persistence | Too strong. It describes an expected trust boundary under assumptions, not a complete firmware/hardware proof. | Offline audit of exact paths and assumptions; no live GC6 experiment. |
| VFIO/VM snapshots contain firmware damage or guarantee recovery | False for passed-through physical hardware. | Such a VM is not an offline sandbox; no hardware exception here. |
| Synthetic fixture agreement validates hardware semantics | False. Fixtures test software behavior only. | Keep synthetic and observed datasets separate. |
| The 10-monitor collector dry-run does not touch hardware | False in the concurrent worker version: it initialized NVML and sampled before returning. Replaced by the no-hardware plan wrapper. | No ctypes or automatic loop remains in the active collector. |
| Ignoring getter status and returning initialized zero is valid monitoring | False. Unsupported/failed results must stay missing/error, never normal readings. | Current collector retains raw N/A/errors and rejects failed/mismatched results. |
| Index 0 samples and all-GPU procfs metadata identify the same device | Unproven on multi-GPU hosts. | Current collection is selected and checked by a full known UUID. |
| No mutations / inference never disturbed / all generations supported | Historical worker reports, not independently verified facts. | A repo snapshot cannot audit unpushed operations, workload continuity or all SKUs. |

The old tracer stored a fixed 384-byte prefix for several variable-size controls. Treat
those files as possibly truncated unless their actual file length and provenance prove
otherwise. Raising a capture constant did not retroactively make old dumps complete.
The current decoder writes exactly the retained length and never contacts a GPU.

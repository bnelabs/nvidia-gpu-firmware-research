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

## Offline reproduction additions — 2026-10-21

| Earlier ambiguity | Reproduced correction | Evidence |
|---|---|---|
| `off_2D1180` is one unambiguous address, and the 55-qword copy duplicates the flat function table | The flat table is file offset `0x2d1180` / host ELF VA `0x2d2180`; the copy reads host ELF VA `0x2d1180` / file `0x2d0180`, a separate template. | [Raw exports and relocations](research/2026-10-21-offline/host-evidence.json). |
| ca2d03e is exact source for copied 615.71.09 userspace | ca2d03e identifies 615.78.08. Exact 615.71.09 source is 61dcc93722ecb418bb5f2e00923f05b4b8051dd1. | [Source hashes and commits](research/2026-10-21-offline/source-manifest.json). |
| Existing GA102 PROD 48-byte UCODE_DESC copy is an unpacked descriptor | It matches the 42-byte compressed record plus six storage-padding bytes; decoded size is 84 bytes. The 17,936-byte PROD image copy likewise contains padded compressed storage; decoded size is 24,576. Originals are unchanged. | [Validated nearby-release comparison](research/2026-10-21-offline/ga102-boot-comparison.json). |

The public P-state wrapper's static path, its file-template candidate and the
historical log are separate evidence. The log reports ordinal 8 but does not show
0x20802068 in its getter intervals. That contradiction is preserved, not replaced
by the candidate path or synthetic emulation. See the dated [first claim ledger](research/2026-10-21-offline/README.md)
and its [follow-up](research/2026-10-21-pstate-dispatch/README.md).

## P-state dispatch follow-up — 2026-10-21

| Earlier ambiguity / overinterpretation | Current disposition | Evidence |
|---|---|---|
| Constructor `+0x285e0` and wrapper `+0x28540` may be unrelated | Resolved: device base is global base `+0xa0 + index*0x93418`; both expressions address the same field. Store at `0x31b9e` restores a saved pointer, while `0x1528f0` performs template construction. | PD-01, raw instructions and retained IDA output in the [dispatch packet](research/2026-10-21-pstate-dispatch/README.md). |
| No `0x20802068` in the retained getter intervals conflicts with the canonical callback | The callback conditionally uses RUSD first, with a cached subscription and shared record `+0x8e8`. This explains a possible no-control path. Historical branch selection stays unresolved without raw pointer/shared-memory evidence. | PD-03–06 and PD-11; ten synthetic reader cases. |
| The compiled reader has the public macro's ten-attempt default, or a valid timestamp proves fresh data | Incorrect for this artifact: compiled helper tries five times; timestamp 1 is accepted without an age test. Raw error 10 leaves output unchanged. | `0xf1db0` raw instructions and CPU emulation; exact `cl00de.h` macro compared separately. |
| Complete syscall route and firmware consumer of the direct P-state control are unknown | Advanced: canonical host default route builds NVOS54 `0xc020462a`, 32 bytes; retained firmware metadata maps the control to `0x16be978`. Handler returns an object value after lookup; concrete indirect getter/value writers remain unknown. | PD-07–09; no actual ioctl or firmware service invoked. |
| Matching shared-memory and direct control fields proves a common physical sensor | Unproven. The RUSD writer and direct object's field writers have not been joined. Neither field is a demonstrated physical register read. | PD-09–10; next offline writer/callback trace. |
| 1,183 Subdevice method records constitute all GPU access or all are publicly callable | Unsupported. This is one retained class/component, with source-decoded routing/access flags; runtime permission, per-SKU availability and coverage of other classes are unresolved. | Raw NVOC inventory; public host table has a different count (656). |

Earlier packets remain unchanged as dated evidence; these dispositions supersede their
explicitly unresolved constructor, transport and firmware-method checkpoints.

## Firmware writer follow-up — 2026-10-21

| Earlier unknown / possible overinterpretation | Current disposition | Evidence |
|---|---|---|
| RUSD P-state record writer is unlocated; relation to direct command unresolved | Writer `0x143bde0` receives shared `+0x8e8`, supplies internal RM API callback command `0x20802068`, size 4, and publishes on success. This proves the semantic control contract; the callback's concrete dispatch target is still unknown. | PW-01–04 in the [writer packet](research/2026-10-21-pstate-writers/README.md); exact-source cl00de.h:142–146 independently states the command relationship. |
| Old nonzero payload bytes in the shared buffer represent an available sample | Unsupported without timestamp validity. Error/mask branches can zero the timestamp while preserving previous payload. Disabled-mask branches can also retain the prior record; host reader contains no age check. | PW-05–07; copied writer bytes fed to copied x86 reader with synthetic memory. |
| Matching writer/control identity proves a physical sensor/register or actual runtime handler | Unproven. RM callback target, concrete object getter and entry `+0x34` writers remain unresolved. Synthetic dispatch/getter/timestamp adapters are explicit fixture inputs. | PW-03/06/08; no physical measurement boundary or live verification. |

Earlier raw packets remain unchanged; the new writer evidence supersedes their
unlocated-writer checkpoint, without changing historical runtime uncertainty.

## Internal callback assignment follow-up — 2026-10-21

| Earlier unknown / possible overinterpretation | Current disposition | Evidence |
|---|---|---|
| Internal callback at GPU-object `+0x41c0` has no concrete copied-code assignment | Resolved for the retained initialization block: store at firmware `0x1aea7ce` assigns `0x14078cc`. The target performs internal-handle checks, method lookup and parameter-size validation. Actual runtime initialization/overrides remain unknown. | CO-01–05 in the [callback packet](research/2026-10-21-callback-origins/README.md), raw bytes and bounded execution. |
| Reaching P-state handler from the writer still requires substituting the RM routing target | Advanced: copied initializer and assigned callback now reach copied handler `0x16be978` through actual RTTI/table/search bytes. One context-swap service and instance object graph are still synthetic; entry getter is stopped before execution. | CO-04–05; explicit boundary receipt and 539 executed route instructions. |
| A zero-filled API template in the copied file proves other APIs are always null or unavailable | Unproven. The 240-byte retained template is zero-filled; its runtime initialization is not captured. Explicit per-object overrides are separate evidence. | Retained template bytes/hash, layout and initializer instructions. |
| Internal kernel context or lookup agreement proves an externally reachable bypass or physical sensor | Unsupported. This is an internal compiled path with handle/size checks. No reachability, complete policy or physical-value proof follows. | CO-03/07/08; remaining getter and entry-writer boundary retained. |

The second table-entry callback remains unresolved. Raw SD/ADDI displacement
candidates are not constructor identities or pointer-assignment proof.

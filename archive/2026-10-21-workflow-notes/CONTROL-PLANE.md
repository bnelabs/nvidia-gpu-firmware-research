# NVIDIA GPU control plane — evidence-bounded map
This replaces the earlier definitive/complete claim. See [CORRECTIONS.md](CORRECTIONS.md).
All further protocol recovery is offline.

## Components and demonstrated boundaries
| Component | What the repository can support | What remains unproven |
|---|---|---|
| Application / documented NVML | Public getter contracts; historical outputs/captures | Present health and universal board support |
| Host libnvidia-ml | Reported x86-64 call sites, strings, dispatch tables and arithmetic in SHA-256 283793c0c30dc32f87c0e9fc9b5326fe764bad156e61afa3e997684c47b29a95 | Reproducible disassembly excerpts for every claimed function attribution |
| Kernel RM | Public allocation/control/dispatch structures; exact 615.71.09 source at 61dcc93722ecb418bb5f2e00923f05b4b8051dd1 | Runtime branch selection and exact installed-binary correspondence for each control |
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

## Offline reconciliation — 2026-10-21

Re-exported instructions and raw relocation/table bytes are retained in
[the offline packet](research/2026-10-21-offline/README.md). The historical
`table_off=0x2d1180` is a **file offset**, corresponding to host ELF VA `0x2d2180`.
The 55-qword copy at `0x152a02` instead uses host ELF VA `0x2d1180` (file
`0x2d0180`), a separate mixed template. Do not join these tables by numeric
address alone. Runtime ASLR bias remains unknown.

The public P-state export reaches an indirect callback at host VA `0x9966b`.
The [follow-up dispatch packet](research/2026-10-21-pstate-dispatch/README.md)
resolves constructor base arithmetic: global `+0x285e0` equals device `+0x28540`
because the device base includes `+0xa0`. The canonical template resolves
`0x1218f0`, which conditionally tries the RUSD shared-memory reader before the
legacy four-byte `0x20802068` route. Static instructions and synthetic execution
recover the latter's 32-byte NVOS54 envelope (`0xc020462a`) and raw syscall path.
No transport helper or syscall was executed. The retained log is consistent with
RUSD but lacks raw mapped records and callback pointers; historical selection
remains unproven.

Pinned NVIDIA commit `ca2d03e` is release **615.78.08**. The exact **615.71.09**
source commit is `61dcc93722ecb418bb5f2e00923f05b4b8051dd1`. Generic source
forwarding routes are compared across these versions; they are not a runtime
observation of the installed driver.

## Retained firmware method boundary — 2026-10-21

Copied RM ELF SHA-256
`4ac95cbbe55b5e61572053d0c8a410b4de7693eaa2881d1878c76b6405426f2a`
contains a Subdevice NVOC table at **firmware VA `0x1c59658` / file `0xc59658`**:
1,183 sorted 32-byte records. All records, sizes, flags, raw bytes, mapped method
pointers and public literal annotations are in the
[inventory](research/2026-10-21-pstate-dispatch/gsp-subdevice-exports.json).
This is one component/class, not every GPU command or runtime permission.

`0x20802068 → firmware VA 0x16be978 → lookup 0x167de40 → indirect object getter
+0x38 → returned entry +0x34 → four-byte payload`. The last field is an object
value, not a proven hardware register. Internal RUSD `0x20800afe/0x20800aff`
map to firmware `0x1447738/0x1447ac8`; shared layout length 3,184 and P-state
record offset `0x8e8` agree with exact-source and host code.

The [writer packet](research/2026-10-21-pstate-writers/README.md) now locates refresh
`0x143c6ec → writer 0x143bde0 → internal RM API callback`, supplying command
`0x20802068`, four bytes. Success publishes the raw result through `0x1434cdc`
using an in-progress timestamp, payload copy and final timestamp. Failure zeroes
the timestamp while retaining old payload bytes. Callback addresses
`0x143d998/0x143d878` and the static path from the poll handler are recovered.
Their actual scheduler execution was not tested.

The [callback-origin packet](research/2026-10-21-callback-origins/README.md)
locates a copied initialization block assigning firmware `0x14078cc` to object
`+0x41c0`. Exact-source RM_API layout and the binary agree: API receiver `+0x4188`,
Control `+0x38`, private context `+0xe8`. The internal-handle path walks copied
RTTI/export metadata, checks parameter size and calls P-state handler `0x16be978`.
Synthetic execution follows that assigned callback through actual copied metadata
to lookup `0x167de40`; the former RM-routing adapter is removed from this path.
One opaque context-swap service is still stubbed, object instances are synthetic,
and actual runtime callback selection/replacement remains unobserved. Entry getter
`+0x38` and entry `+0x34` writers remain unresolved. There is no demonstrated
physical measurement boundary yet.
# Object/getter provenance checkpoint — 2026-10-21

The [object-origin packet](research/2026-10-21-object-origin/README.md) advances
the copied firmware path `0x16be978 → 0x167de40`. A child-creation block supplies
class ID `0xed0b65` (exact-source `Perf`) and output `GPU+0x2000`; `KernelPerf`
is a separate ID/output. One Perf table construction branch assigns getter
`0x1757ea0` at table `+0x38` and installs the table at `Perf+0x320`.

The getter returns a pointer-array entry. A copied constructor prefix transfers
`u32(tag-8 input record+0x0c)` through a temporary record into entry `+0x34`;
copied insertion/remapping/getter/handler reproduce that transfer on synthetic
objects. The tagged input producer, actual branch/selection, gate clearing and
later overrides/writers remain unknown. This is an object-value boundary,
not a demonstrated physical register or sensor read. See OO-01–08 and raw bytes.

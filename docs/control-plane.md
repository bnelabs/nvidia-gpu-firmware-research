# How performance-state telemetry reaches NVML

The recovered 615.71.09 code has two ways to obtain the current performance
state: read a shared-memory record, or issue an RM control request. This page
connects the host-library analysis to the firmware objects that supply the
record's value.

The addresses below belong to the retained binaries. Host-library addresses and
firmware addresses are separate domains; neither is a snapshot of live memory.

## Binaries and source

| Component | SHA-256 |
|---|---|
| `libnvidia-ml-615.71.09.so` | `283793c0c30dc32f87c0e9fc9b5326fe764bad156e61afa3e997684c47b29a95` |
| RM ELF extracted from `gsp_ga10x`, 615.71.09 | `4ac95cbbe55b5e61572053d0c8a410b4de7693eaa2881d1878c76b6405426f2a` |

The exact NVIDIA source comparison uses commit
`61dcc93722ecb418bb5f2e00923f05b4b8051dd1`. The RM ELF is not exclusive to GA102.
The [source guide](sources.md) lists the pinned NVIDIA, Linux and independent
references. [Corrections](../CORRECTIONS.md) explains the earlier address and
command misidentifications.

## Host library

The public getter reaches an indirect callback through the per-device context.
The recovered initialization explains how that context is populated; it also
separates two previously confused 55-qword tables. File offset `0x2d1180`
corresponds to host ELF VA `0x2d2180`. Host ELF VA `0x2d1180` refers to a different
initialization template at file offset `0x2d0180`.

The canonical callback at host VA `0x1218f0` tries the shared-data route first
when its architecture and subscription conditions allow it. Reader `0xf1db0`
uses the record at shared mapping `+0x8e8` and checks its timestamp and sequence.
It tries five times. It accepts timestamp `1` without an age check, and a failed
read leaves the caller's output unchanged.

The fallback sends RM command `0x20802068` with a four-byte parameter. The
default host dispatcher builds the 32-byte NVOS54 request with ioctl number
`0xc020462a`. The request construction and call sites are retained; no ioctl was
executed during this analysis.

See the [host/table analysis](../research/2026-10-21-offline/README.md) and
[dispatch analysis](../research/2026-10-21-pstate-dispatch/README.md) for raw
instructions, file mappings, source layouts and synthetic cases.

## Firmware

The copied Subdevice export table contains 1,183 method records. Its entry for
`0x20802068` names firmware handler `0x16be978`, with a four-byte parameter.
These are packaged method records, not a list of commands available to every
caller or GPU.

| Step | Recovered behavior | Analysis |
|---|---|---|
| Shared-data refresh | Writer `0x143bde0` requests `0x20802068` and publishes the result at shared `+0x8e8`. Failure can invalidate the timestamp while retaining old payload bytes. | [Writer](../research/2026-10-21-pstate-writers/README.md) |
| Internal dispatch | An initialization block assigns callback `0x14078cc`. It checks internal handles and parameter size, walks class metadata and reaches the copied handler. | [Callback](../research/2026-10-21-callback-origins/README.md) |
| Object selection | A creation block requests class ID `0xed0b65`, named `Perf` in exact public source, with output at GPU object `+0x2000`. `KernelPerf` is a separate class. | [Object origin](../research/2026-10-21-object-origin/README.md) |
| Table lookup | One construction branch installs a table at `Perf+0x320` and assigns getter `0x1757ea0` at table `+0x38`. The getter returns a remapped pointer-array entry. | [Object origin](../research/2026-10-21-object-origin/README.md) |
| Returned value | Handler `0x16be978` loads entry `+0x34`. One entry constructor copies that word from an input record tagged `8`, through a temporary record. | [Entry writer](../research/2026-10-21-object-origin/README.md) |

The bounded emulators execute these copied blocks with synthetic objects and
explicit unresolved-service replacements. Their reports identify each replacement
and stopping point. No physical register read has been demonstrated for the
returned word.

The [record-producer analysis](../research/2026-10-21-record-producer/README.md)
locates the tagged record in a serialized buffer with a 20-byte header and
556-byte stride. Its getter returns a pointer into that buffer for a present
index. The earlier acquisition path constructs a memory sub-descriptor; the
actual transfer and source storage are still unresolved.

## Encodings and open questions

The RM contract uses one-hot P-state masks: raw `4` represents P2, and raw `256`
represents P8. Public NVML returns an ordinal. Keep those representations
separate when decoding retained data.

The copied host conversion returns invalid ordinal `32` for a non-one-hot mask.
In the bounded firmware constructor/consumer experiment, raw `3` is copied
unchanged. That does not establish that such an input is reachable after all
upstream and later checks.

The remaining questions are where the tagged input record originates, how the
current table index and availability gate are selected, and whether other
construction paths replace these functions. Historical text logs contain no
runtime object or shared-record snapshot that resolves those questions.

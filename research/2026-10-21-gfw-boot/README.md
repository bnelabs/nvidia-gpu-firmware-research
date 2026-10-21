# The GPU responds on PCIe, but its early firmware boot is incomplete

The GPU has **not** been recovered for inference. Earlier authorized recovery
restored PCI visibility after a hung driver removal, but reinitialization still
failed. This packet investigates that remaining failure from retained logs,
copied source and firmware files. No additional live GPU operations were used.

The earlier telemetry research did not deliver an Xid79 reset implementation.
Its control routing and shared-memory findings cannot initialize firmware that
has not reached the driver's boot prerequisite.

## What the retained failure proves

[boot-failure-excerpt.log](boot-failure-excerpt.log) preserves the exact retained error and line numbers.
At 20:34:57+03 the driver reported GFW boot progress `0x1`, error `0x55`, and
VBIOS version `94.02.42.00.F4`. The exact 615.71.09 source checks early GFW boot
before `_kgspBootGspRm`. In this path, the Falcon halt wait returned success,
but the progress check did not report completion (`0xff`). This distinguishes
an incomplete early boot from a demonstrated crash of the runtime GSP-RM image.
It does not identify the physical fault, prove a power cycle necessary, or
establish the writer of the particular observed value.

The register address is GPU PRI `0x118234`, not a host pointer, ROM file offset
or firmware instruction address. The progress field is bits 7:0. The driver
also checks level-0 read permission at GPU PRI `0x118128`. Header definitions
and the exact source hashes/commit are in `boot-comparison-sources.json`.

## A new usable firmware artifact

A public ROM candidate advertises the same VBIOS version and PCI/subsystem IDs
as the failed card. This is **not proof of installed-byte identity**. The file
was downloaded as data and has never been flashed, loaded onto a GPU or booted.

| Artifact | SHA-256 |
| --- | --- |
| Candidate ROM, 999,424 bytes | `6dd01dee331f4d0faf5dbd8bc58e31dd58eb88c7d403c7f7ae13e412927e8711` |
| Production FWSEC IMEM, 55,808 bytes | `cf60d4e90156f106a850f40d02890577c8c55c773c8931949cc31feca0806b2b` |
| Debug FWSEC IMEM, 55,808 bytes, stored form | `a84efa34649c843d6075fbbeec3ee958a3a02df25ed8c0a34ba679f1775f6fb1` |
| Debug FWSEC IMEM after offline AES decode | `dee558dc5bbe329bd7ff4d20bc7d7bd0d47d91c1c8d301e759dc6d66348d7ecb` |

NVIDIA's private option-ROM chain matters. There are two type-`0xe0` images;
the public loader chooses the first. Falcon pointers require the expansion
adjustment, not simple addition to that image's start. For this wrapped file:
`target_file_offset = 194048 - 65024 + raw_pointer`. That resolves the production
descriptor at file 308720 and debug descriptor at 249668. The version-3
descriptor is 1196 bytes, including three 384-byte signatures. Descriptor,
IMEM and DMEM bounds/hashes are retained in the [candidate-fwsec-corrected.json](candidate-fwsec-corrected.json) and [candidate-fwsec-debug.json](candidate-fwsec-debug.json).

**Correction:** the clear descriptor `ENCRYPTED` bit was insufficient evidence
that its IMEM payload was plaintext. The original direct disassembly produced
untrustworthy instruction output and is retained in the local incident archive as `fwsec-fuc6.dis`. The
committed parser explicitly leaves payload encoding unresolved from that bit.

A public GA100 research report supplied a debug-key hypothesis. Applying its
reported AES-128-ECB key to the copied GA102 debug IMEM produced coherent Falcon
instructions, stack checks, register-access helpers, and references matching
the NVIDIA boot-progress definitions. Re-encryption reproduces the input bytes.
The raw key-source revision, document hash and short excerpt are retained in
`debug-key-source.json`; no leaked source was obtained. This establishes a
reproducible decode of this debug artifact, **not** a production-key recovery,
signature authentication or permission to run the debug image on hardware.

The decoder is envytools commit
`f102b82381f3f11cee113d16374c87091db039d9`, built locally from only its utility,
assembly-expression and disassembler components. It ran with no GPU devices,
sysfs, network or hardware services inside an unshared bwrap namespace. The
selected decoder is `envydis -m falcon -V fuc6 -F crypt -i -n`. The complete
linear decode has 61 unknown instructions, first at IMEM VA `0xd713`; the
trailer is not being promoted into a code map. The selected routines below
contain no unknown instructions.

## Actual boot-progress writers in the decoded debug image

These are **Falcon IMEM VAs in the decoded debug candidate**, not production
runtime addresses. `fwsec-boot-excerpts.dis` includes the raw bytes. Helpers
`0x1117` and `0x1171` respectively place the address argument in Falcon IO
`I[0x1c100]` and use the corresponding transaction/data ports for a read/write.
They are inferred register-access helpers from their instructions, not symbols
recovered from a debug symbol table. Their IO addresses and the GPU PRI operand
are separate address domains.

| Basic block [start, end) | Narrow demonstrated effect through those helpers |
| --- | --- |
| `0x1338..0x134e` | Clear the low byte of the value at PRI operand `0x118234` |
| `0x4e87..0x4ea0` | Replace the low byte with `0x1` |
| `0x577a..0x5793` | Replace the low byte with `0x2` |
| `0x4bdc..0x4bf5` | Replace the low byte with `0x3` |
| `0x5899..0x58b2` | Replace the low byte with `0x9` |
| `0x592e..0x5941` | OR the low byte with `0xff`, the driver's completion value |

This table is not a claim that all branches follow the listed order. The
routine at `0x4d5c` contains the `0x1`, `0x2`, `0x9` and completion blocks.
After writing `0x1`, it checks other state and has failure exits before it can
write `0x2`. For example, instructions at `0x4ea0..0x4eba` inspect PRI operand
`0x137090` bit 17; a selected branch calls `0x45b`, whose copied instructions
inspect PRI operand `0x825800` bits 0, 1 and 2 and can return raw codes
`0x2e9`, `0x2ef`, or `0x2f0`. These addresses/codes remain raw; no unsupported
register names, physical diagnosis or recovery writes are assigned to them.

Consequently, a low byte of `0x1` is not by itself a unique error code. These
debug-image exits show why the retained host log cannot determine a single
failed prerequisite. The debug routine also uses Falcon data-space addresses
around `D[0x1000000]`, supporting that the mapper's command output offset is
not a ROM-file offset. Its runtime backing remains unresolved.

## Verification and comparisons

* Six actual NVIDIA source-gate cases ran with synthetic register reads and
  halt outcomes (`replay.c`, `copied-functions.inc`, `replay.json`). The mapped
  early-probe branch is excluded. A completion value cannot substitute for
  initialization; the synthetic all-ones case also illustrates the predicate's
  limits when supplied unrealistic success inputs.
* A bounded interpreter executed the **copied bytes** of the six debug-image
  basic blocks against five input values each: 30 cases passed, preserving
  upper bits and producing the expected low byte. Unknown opcodes are rejected.
  `0x1117`/`0x1171` calls are explicit synthetic adapters. Their bodies, hardware
  effects and the full boot routine are not emulated (`fwsec-progress-replay.json`).
* The exact installed-release NVIDIA source is commit
  `61dcc93722ecb418bb5f2e00923f05b4b8051dd1`. Its GA102 loader separates
  boot-ROM authentication, HS firmware execution and runtime GSP-RM startup.
* Pinned Linux/nouveau source at
  `7d0a66e4bb9081d75c82ec4957c50034cb0ea449` and Linux nova's Ampere FWSEC
  documentation independently describe the early secure-boot/FRTS lifecycle.
  Their differing lifecycle code is not evidence that switching this server
  to nouveau/nova would recover the card. No driver switch was attempted.
* The public GA100 reports disagree in places about encryption/key indexes
  and reset domains. Only the locally reproduced debug-key decode is promoted
  here. Their assertions about live resets, faults, or GA100 behavior are not
  transferred to this GA102 card.

## What we can and cannot do now

We can inspect an early-boot component that was previously opaque, identify its
progress writers and failure branches, and test isolated logic without touching
the GPU. We have not proved debug/production code equivalence, recovered the
production plaintext/key, identified the outage's failed prerequisite, or built
a working no-reboot reinitialization sequence. Writing `0xff` or deleting the
driver check would falsely report completion and is not a repair.

The next offline task is to trace the failure exits between the copied debug
routine's `0x1` and `0x2` writes, and compare the same FWSEC component in another
nearby GA102 ROM. Retained error data should be used where available; absent
register state must remain absent. A new live intervention needs an identified
initialization mechanism and evidence that it applies to this fault.

The server remains in the previously recorded maintenance state: NVIDIA modules
unloaded and GPU inference services stopped; the CPU/tool harness remains
available. This audit changed no driver, firmware or hardware settings. Existing
uncommitted work in both repositories was left intact. The host was not rebooted.


## Reproduce from copied files

Firmware binaries remain outside Git. The ROM URL and SHA-256 are recorded in
[msi-3090-F4-candidate.source.json](msi-3090-F4-candidate.source.json). Place that
exact file under `firmware-store/gfw-boot/msi-3090-F4-candidate.rom`, then run:

```sh
bash scripts/run_cpu_only.sh bash research/2026-10-21-gfw-boot/reproduce.sh
```

The script rejects a different ROM, checks every retained parser field, extracts
the debug IMEM using the parsed table pointer, decodes it in CPU memory, and
reproduces both replay outputs byte-for-byte. It requires Python 3, OpenSSL and a
C compiler. The six basic blocks also retain their raw instruction bytes in
`fwsec-progress-replay.json`. The full exploratory disassembly, original failed
decode, downloaded ROM and initial parser remain in the separate local incident
archive; they are not production tools or an automated recovery service.

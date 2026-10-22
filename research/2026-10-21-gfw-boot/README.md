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

The follow-ups below trace more failure exits, restart state and a ROM table
consumer, and compare four GA102 variants. Absent register state remains absent.
An additional intervention still needs an identified initialization mechanism
that applies to this fault.

The last recorded server state was maintenance: NVIDIA modules
unloaded and GPU inference services stopped; the CPU/tool harness remains
available. No fresh hardware check was performed for this audit. It changed no
driver, firmware or hardware settings. Existing
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
reproduces the replay outputs byte-for-byte. It requires Python 3, OpenSSL and a
C compiler. The six basic blocks also retain their raw instruction bytes in
`fwsec-progress-replay.json`. The full exploratory disassembly, original failed
decode, downloaded ROM and initial parser remain in the separate local incident
archive; they are not production tools or an automated recovery service.


## Follow-up: the first three checks and four ROM variants

The copied debug bytes now execute through the first checks after the `0x1`
write, including their conditional error-publication path. Twelve synthetic
cases in [early-gates-replay.json](early-gates-replay.json) cover these paths.
Every one of the 808 executed instruction boundaries/byte sequences agrees
with the retained envytools listing. Reads, writes, entry state, stack and
canary are fixtures; this is not an execution trace from the card.

| Copied debug code | Condition | Raw result in the modeled path |
| --- | --- | --- |
| `0x4ea0..0x4eba` | PRI operand `0x137090`, bit 17 clear | `0xb3` |
| `0x45b..0x4ac` | PRI operand `0x825800`, bit 0 set | `0x2e9` |
| Same helper | bit 0 clear, bit 1 set | `0x2ef` |
| Same helper | bits 0–1 clear, bit 2 set | `0x2f0` |
| `0x3f1c..0x3f7d` | PRI `0x137808` bit 0 set and `0x137810` bit 4 set | `0x2ee` |

These are firmware raw codes, not assigned `NV_STATUS` meanings. The helper
at `0x3d1a` inspects PRI operands `0x22410` and `0x1070`; its result controls
whether the error is written to PRI operand `0x200bc` at `0x58dd..0x58e7`.
Our fixtures show both error publication and suppression for the same earlier
failure. The replay stops at the next boot precondition (`0x4ec5`) or error
tail (`0x58ed`). It does not execute the remainder of initialization.

No identified retained values select one of those failure branches. The current
NVIDIA GA102 headers do not establish names for all of these fields. Envytools'
older GF100 clock-domain map and Hopper/Blackwell names at `0x200bc` are not
substitutes for GA102 evidence. None of these operands is a proposed live
read/write recipe.

The retained unload log also shows a more specific failure than the short
FWSEC error line: **the IMEM transfer hit a queue-not-full timeout, mode 0**.
[teardown-dma-excerpt.log](teardown-dma-excerpt.log) and
[early-gates-sources.json](early-gates-sources.json) preserve the exact evidence.
The source returns before PKC setup and `StartCpu` for that invocation. It
therefore does not show the requested FWSEC-SB program executing and returning
one of the raw codes above. Queue checks occur before and within the transfer;
the amount transferred is unknown. This unload event precedes the later reset
and `0x1` startup error. A causal connection remains unproven.

[version-comparison.json](version-comparison.json) compares four copied ROMs.
Their versions are decoded from BIT BIOSDATA bytes, rather than assumed from
filenames: `94.02.42.00.F4`, `.0B`, `.0F` and `.44`. Each legacy image carries PCI
device ID `0x2204`. All four have byte-identical FWSEC descriptors, stored IMEM
and stored DMEM, separately for debug and production. Decoded debug IMEM also
matches. The production plaintext/key remains unknown; debug/production
semantic equivalence does not follow from these comparisons.

These are different board-vendor variants within the same VBIOS version family.
OEM suffixes do not establish release chronology. Other ROM components and
runtime board parameters can differ. The three EVGA files were retained before
this investigation; their hashes are known, but original download URLs remain
unresolved. Their firmware is not a replacement for this card's VBIOS.

The regular reproduction command now checks the twelve early-gate cases too.
With all four exact ROM files copied under `firmware-store/gfw-boot`, reproduce
the separate comparison with:

```sh
bash scripts/run_cpu_only.sh python3 research/2026-10-21-gfw-boot/compare_fwsec.py firmware-store/gfw-boot
```

## Restart dependencies and a concrete boot table — 2026-10-22

The copied debug firmware has restart prerequisites and a separate step-state
word. The driver also has reset cleanup that the reviewed recovery adapter does
not perform explicitly. Neither finding identifies the card's missing state.

[restart-state-replay.json](restart-state-replay.json) executes copied bytes for
23 synthetic cases. At IMEM `0x4dd9`, PRI operand `0x118c6c` bit 0 selects whether
to preserve the step word at PRI `0x11823c`. When set, the firmware requires
`0x100ce0 == 0`, the high half of `0x1180f4 == 0`, and `0x1fa800` bit 5 set.
The accepted branch writes `0x8a000` to the step word at `0x4e20`; rejection
selects raw `0xb7`. Further entry checks can select `0xba`, `0xb8` or `0xbb`.
These are raw debug-firmware codes, not host `NV_STATUS` names.

Following the previously mapped checks, Falcon IO `I[0x10200]` bit 20 or PRI
`0x820434` bit 0 must be set, otherwise raw `0x213` is selected. Another
conditional path checks PRI `0x1728 & 0x2f800000` and PRI `0x1724` bit 27,
selecting raw `0x41b` and `0x2aa` on their respective failures. No retained
values establish which path the card took.

Step state is distinct from progress at PRI `0x118234`. At IMEM `0x500f`, bits
1:0 of the step word select the body for 0, bypass it for 2, or reach a trap
boundary for 1/3. Bits 23:22 select different callees for 0 and 2. Thus value 2
does not universally skip initialization. Trap handling, reset survival and
production equivalence remain unresolved. `0x8a000` is an observed firmware
operand, not a proposed live write.

[boot-dependencies.json](boot-dependencies.json) verifies 957 instruction
encodings. Its conservative graph retains 653 instructions on potential routes
from `0x4ec5` to the `0x2` block at `0x577a`. Calls are assumed to return;
traps/returns/exits terminate; branches may take either direction. Structural
mandatory calls under those assumptions do not prove feasible or successful boot.

### A digest-matched ROM record and its consumer

The parser chain leads to a table at ROM file `0x75d0`. Record ID `0x41` is row
51 at file `0x80ac`, with a 129-byte payload. Searching every possible 129-byte
window finds exactly one SHA-256 match for row bytes 20–51: file `0x86b48`,
digest `35939c300c4216c6a523643b01255a5e6023aa6a84a24b2f43414085c30181b6`.
That is first type-`0xe0` image start `0x2f600` plus record offset `0x57548`.
Applying the Falcon-ucode pointer adjustment here selects the wrong bytes.
This corroborates one file mapping, not signature authenticity or installed bytes.

The payload is byte `0x40` followed by 128 zero bytes: 64 zero halfwords.
Copied consumer `0x3f7d` requests this record, bounds its size, invokes additional
validation calls, then copies the count/list around Falcon data addresses
`D[0x2f12]`/`D[0x2f14]`. The header halfword at `+0x28` is `0x2204`.
Main `0x51a7..0x51db` compares it with the high halfword of PRI operand `0x88000`.
A match bypasses the fallback list check. A mismatch conditionally uses that
list, depending on unresolved getter `0x16fa`; an unmatched enabled fallback
reaches the raw `0x4c` error boundary.

[boot-record-41.json](boot-record-41.json) preserves the raw bytes, pointer
arithmetic and seven copied-consumer cases. Supplying reported card ID `0x2204`
as a synthetic register value takes the primary match. The hash/signature engine,
full parser, real table publication and getter do not execute in this model;
their success is not substituted. Official names for this record remain unknown.

All four retained ROM variants have identical record bytes and payload hashes
([comparison](version-comparison.json)). Those bytes provide no evidence for a
variant-specific mismatch in this candidate. They cannot exclude a different
installed image or another failure. Exact NVIDIA source corroborates `RFRD` and
the PCI configuration-map region, not this record's schema. [Raw consumers](boot-record-excerpts.dis)
and [source pins](boot-record-sources.json) preserve that distinction.

### Reset cleanup comes after the failed prerequisite

Exact 615.71.09 source parses FWSEC before its GFW readiness gate, but
`kgspInitRm_IMPL` has no explicit FWSEC-SB retry at that gate. Normal runtime
bootstrap follows it. FWSEC-SB exists in teardown; that does not prove it can
safely restart this failed boot. The retained teardown DMA timeout occurred
before `StartCpu`, so that invocation does not demonstrate FWSEC-SB execution.

The vendor FLR function calls `gpuWaitForGfwBootComplete_HAL` before
`kbifClearDownstreamReadCounter_HAL`. Its error branch skips cleanup despite a
nearby comment saying to clear regardless of success. [Seven cases using the
unmodified source function](flr-source-replay.json) reproduce this ordering with
synthetic callbacks. This is not proof our rejected Linux FLR attempt ran that code.

Generated HAL dispatch proves GA102 selects the GA100-named cleanup. It uses
PCI **configuration offset** `0x84c`, field bit 9, not a BAR0 address or firmware
VA. The reviewed adapter at `ms7d25-gpu-recovery` commit `1983fff` has no explicit
equivalent stage. Linux's core bridge reset uses a platform hook and waits;
every platform override, quirk and installed kernel patch has not been audited.
The five reviewed driver function bodies match between 615.71.09 and 615.78.08.

The vendor ordering expects boot completion **before** counter cleanup. No
retained counter value or causal evidence shows that clearing it would repair
the earlier GFW failure. This is an unresolved dependency, not a reset recipe.
[reset-dependencies.json](reset-dependencies.json) records commits, hashes,
GA102 dispatch and limits. To reproduce this separate source comparison, place
the exact source files specified there under ignored `vendor/reset-audit`, then:

```sh
bash scripts/run_cpu_only.sh python3 research/2026-10-21-gfw-boot/audit_reset_dependencies.py vendor/reset-audit
```

The regular reproduction command now checks the restart, table-consumer and
FLR cases and conservative graph too. All register values, getter results,
entry objects and hardware callbacks in these models are synthetic.

### The table restores saved state; it does not supply boot defaults

Following that table exposed an important distinction. `0x5be3` selects a table
and count; `0x5c9a` constructs its register addresses. The copied constructor
prefix for selector 1 produces these first eight PRI operands:
`0x118fd0`, `0x823800`, `0x80`, `0x1200a0`, `0x137f34`, `0x20324`, `0x2082c`,
`0x20820`. Later predicates can append rows; the prefix is not the full table.
These are raw operands, not inferred official register names or live-write targets.

Rows have stride 12. Routine `0x5ab2` reads each register and saves its original
value at row `+4` (`0x5b2f..0x5b33`), performs a modifying write/readback, and
marks row `+9` active at `0x5bbc`. Main loads selector 1 at `0x5737` before
calling `0x59fe`, which restores saved values for active rows. A matching
readback clears the active byte. A mismatch writes the address and observed
value through PRI operands `0x146c`/`0x1470`, then reaches a trap at `0x5a83`.

[saved-registers-replay.json](saved-registers-replay.json) executes that
constructor prefix and three separated restore cases: match, mismatch and
inactive row. Between write and readback fragments the device response is an
explicit synthetic input. Missing saved-value memory is rejected, not filled
with a guessed default. [Raw instructions](saved-registers-excerpts.dis) also
retain the save/modify routine, selector and remaining constructor branches.
The full save/modify/restore cycle and hardware trap handling are not emulated.

This is tangible saved-state handling, but it does not recover the card's saved
values or a cold-start sequence. Treating these addresses as a table of fixed
initialization values would be wrong. Saved data, active flags and the card's
execution of these branches remain unknown.

## The final call before progress `0x2`

The next trace reaches another firmware component and a specific completion
condition. In the copied debug code, the selected loader branch waits for a
secondary core to halt. This advances the software dependency map; it does not
show that this was the failed prerequisite on the card.

At `0x4653`, step-word bits 25:24 select execution for 0, a bypass for 2, or a
trap boundary for 1/3. Helper `0x279a` reads PRI `0x118238` twice, extracting
bits 19:8 from the first read and 31:20 from the second. A field of `0xfff`
clears a presence byte; a zero field leaves its caller-initialized zero intact.
With two nonzero, non-`0xfff` fields, it supplies three words:
`first << 12`, `(first << 12) - 0x200`, and `second << 12`, then sets presence.
These arithmetic operations do not establish physical address meanings. A
synthetic two-snapshot case demonstrates that the two fields need not come
from one atomic read.

When presence is false, the caller updates low scratch bits at PRI `0x1418`.
Otherwise it uses further scratch conditions and may invoke `0x43a8(1)`.
The selector-1 branch places raw `0x40` in a local argument record and chooses
raw mode `0xaa`. Its later branch selects wait `0x669d`, whose helper `0x663a`
checks a core-selection register and then a HALTED field:

| Copied PRI operand | Source-backed meaning in this constructed engine descriptor |
| --- | --- |
| `0x10b668`, bit 4 | `BCR_CTRL.CORE_SELECT`, Falcon = 0, RISC-V = 1 |
| `0x10a100`, bit 4 | Selected Falcon `CPUCTL.HALTED` |
| `0x10b388`, bit 4 | Selected RISC-V `CPUCTL.HALTED` |

The copied descriptor constructor `0x615f(1)` supplies bases `0x10a000` and
`0x10b000`; exact GA102 headers corroborate the offsets and fields. The wait
loops while HALTED is clear. No timer check occurs inside these two copied
routines; that does not exclude an outer watchdog or other unmodeled behavior.
Synthetic never-halted input exhausts the interpreter budget, not an invented
firmware timeout status.

The nearby timed wait at `0x4532..0x456c` is a **different branch**, selected by
raw mode `0x55`. It polls PRI `0x205e4` bit 9 and compares a wrapping 32-bit
Falcon-IO counter delta against raw `0x08000000`. A delta greater than that
threshold selects raw `0xbc`; equality is accepted. The check can reject a late
ready bit before testing it. Counter frequency and time units are unknown.
Selector 1 chooses `0xaa`, so proximity in the same loader is not evidence
that this timed poll explains the selected call or the retained failure.

[last-stage-replay.json](last-stage-replay.json) retains 22 call/branch cases,
six alternate-wait cases and three rejected incomplete/stalled fixtures.
The full loader does not execute. Its result is supplied only in explicitly
separated continuation cases. Those cases establish a diagnostic limit: the
caller marks step bits 25:24 as 2 even when the supplied loader result is an
error, then returns that error. A marker of 2 alone is not proof of success.

### The loader's copied PRE_OS component

Loader `0x43a8` requests record `0x2f`. In the candidate ROM, that is row 44,
file `0x7f40`; its offset and SHA-256 resolve a 33,520-byte payload at file
`0x34c54`. Independently, the BIT entry with application 1 / target 1 resolves
to the same file location using its own pointer adjustment. Envytools names
those IDs `PRE_OS` and `PMU`; pinned nouveau source corroborates the older
PRE_OS convention and PMU base. This is a matched copied component, not a
newly inferred FWSEC application name.

The payload uses a 48-byte legacy descriptor, followed by 32,004 IMEM bytes and
1,468 DMEM bytes. Entry/IMEM/DMEM bases are zero; the interface offset is `0xec`.
Its IMEM SHA-256 is
`45ed86ec62e8ceba8fb402e472f5a3ceea206c37c22772e2ef922e78bf89c6fc`.
It is separate from the decoded debug FWSEC image and has never been loaded
onto hardware by this research. The public NVIDIA FWSEC parser's comment that
it does not use v1 does not imply that all other VBIOS applications use v3.

[preos-comparison.json](preos-comparison.json) compares all four retained GA102
variants. Their legacy descriptors and IMEM match exactly. Compared with MSI
F4, each EVGA variant differs in 16 DMEM bytes between offsets `0x594` and
`0x5b7`; EVGA `.0B` and `.0F` match each other, while `.44` differs from them.
Copied reader prefixes at PRE_OS IMEM `0x2b0` and `0x46b` consume those data
locations. The report retains raw differences and register results, without
assigning voltage, fan, clock or other physical meanings to plausible values.

The new PRE_OS decode also exposes a candidate completion-bit producer. At
PRE_OS IMEM `0x136..0x14e`, code clears bit 9 of **D[0x140205e4]** and checks
readback. After an unexecuted IO predicate, `0x15c..0x169` sets bit 9 there.
Eleven bounded cases in [preos-component.json](preos-component.json) cover
those operations and an entry wait on **D[0x14001724]** bit 29. That entry wait
precedes unexecuted initialization callbacks.

The low operand/bit corresponds to the alternate FWSEC poll, but a primary
GA102 definition establishing the `0x140...` aperture mapping was not obtained.
The replay keeps these large Falcon data operands separate from GPU PRI;
it does not silently alias them or infer host access. Full callback execution,
actual completion and the physical mapping remain unresolved.

[Raw FWSEC](last-stage-excerpts.dis), [raw PRE_OS](preos-excerpts.dis), and
[source commits, hashes and compatibility limits](last-stage-sources.json)
accompany these interpretations. Nouveau's inspected GA102 chip table omits
a PMU constructor, so its older GM200 code is a comparison, not an asserted
GA102 recovery backend. The retained host GSP halt-success/progress-1 result
does not demonstrate an ongoing nested PMU wait or identify one of our cases.

The regular reproduction command checks both new replays and their raw
instruction encodings. With all four exact ROMs present, reproduce the separate
component comparison with:

```sh
bash scripts/run_cpu_only.sh python3 research/2026-10-21-gfw-boot/inspect_preos.py --compare firmware-store/gfw-boot
```

### Argument publication and PRE_OS exit

The copied interface at PRE_OS D[`0xec`] has header `01 04 08 09`: nine
eight-byte entries. ID `0x0e`, version 1, points to D[`0x1c`]. Its twelve
original bytes are `01000c000200010016000000`. The FWSEC interface finder
`0x686c`, record check `0x6371` and loader `0x43a8` retain the lookup/read
instructions; the new replay parses the file rather than pretending those PIO
reads ran. Selector 1's copied stores at FWSEC `0x44af` produce
`01000c000200000040000000`: clear bit 0 of the halfword at record `+6`, and
write `0x40` to word `+8`. These are two separate changes.

Copied call setup passes destination `0x1c`, size 12 and the local record to
writer `0x6b04`. The writer checks nonnull pointers, four-byte alignment and
destination/size/span against `(PRI[engine_base+0x108] >> 9 & 0x1ff) << 8`.
Its selected port control is `engine_base+0x1c0`, value `0x0100001c`, followed
by three words through `engine_base+0x1c4`. Exact GA102 headers name those
DMEMC/DMEMD offsets and write auto-increment bit 24. Generic nouveau Falcon
source uses the same transfer pattern. The GA102 header inspected here does
not name HWCFG bits 17:9; the capacity arithmetic comes from the copied code.
Envytools' older data-port description covers fewer address bits than GA102's
DMEMC definition; their agreement at this low destination does not settle
the full address width.

The transfer also runs FWSEC `0x66de` and `0x673a`. Actual helper `0x1014`
emits Falcon IO writes and loops while I[`0x1c000`] bits 14:12 equal 1.
The later status check can trap at `0x6786`; a completed per-word poll is
therefore not proof the whole writer succeeded. The CPU replay supplies
capacity and bus responses explicitly, retains all port events, reconstructs
only a file buffer using documented auto-increment, and rejects absent
capacity/status or a stalled transport. It does not emulate a physical bus.

In PRE_OS, `0x169` tests **record `+6` bit 0**, not word `+8`. Clearing it
selects exit-callback dispatch at `0x1d5`; keeping it set selects recurring
work, which can also leave through a separate request bit at D[`0x14001404`].
The same flag test at `0x1fe` lets the cleared case skip an additional register
cleanup path. Synthetic counterexamples keep `0x40` with flag 1, and keep
`0x16` with flag 0: the branch follows the flag in both cases.

Word `+8` does have a proven consumer. Last initialization callback `0x5d51`
tests bit 6. `0x40` selects call `0x1484`; a zero return then selects `0x5c8f`.
The original `0x16` skips that call. Separate continuation cases preserve
synthetic service results and the callback's conditional upper-half status
publication. Neither callee is replaced with an asserted successful operation.
No command name or physical function is assigned to this bit yet.

Copied tables contain ten initialization, five recurring and eight exit
callbacks. Dispatch replays stop at init `0x6c85` and exit `0x5e92` after
executing two trivial exit callbacks. Entry's D[`0x14001724`] bit-29 wait,
other callbacks and the IO predicate still have to complete. After unexecuted
exit callbacks, copied return fragments extract the upper-half status from
D[`0x14001404`] and reach startup cleanup `0x7a14`.

Inspection of the **whole cleanup** matters: it contains its own Falcon
`exit` at `0x7a85`, before its trailing `ret`. Its integer-register-clearing
tail executes separately in the model and stops before that exit. Crypto,
IO and `cauth` operations before the tail remain unexecuted. Returning from
cleanup to startup `0x79fd` and then entry's `exit` at `0xc` is not the normal
copied path and is not supplied as a successful synthetic return.

[Replay and raw cases](preos-arguments-replay.json), [FWSEC instructions](preos-arguments-fwsec.dis),
[PRE_OS instructions](preos-arguments-preos.dis) and [pinned source comparisons](preos-arguments-sources.json)
are included in the regular reproduction command. This resolves the intended
argument/exit mechanism, not the outage's failed prerequisite or a recovery.

Next: trace PRE_OS `0x1484` and then `0x5c8f`, selected by word `+8` bit 6.
Keep their data acquisition, validation and execution boundaries explicit.
Installed-byte identity and debug/production equivalence remain unresolved.

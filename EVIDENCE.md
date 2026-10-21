# Evidence and comparison protocol
The constitutional safety rule has priority over completeness. Missing evidence remains
missing; it is never a reason to probe an uncertain interface on the owner's GPU.

## Claim record
For each finding store:
- ID and narrow question, competing explanations, and status.
- Artifact origin/version, SHA-256 and byte length; original bytes remain unchanged.
- Chip, board, driver, firmware, OS and privilege context if known; otherwise UNKNOWN.
- Component and address space: host-library VA, firmware VA, file offset or transport ID.
- Source repository and immutable commit, exact path/range, instruction/table excerpt
  sufficient to reproduce the interpretation, parser/tool version and command.
- Raw value, decoded type, byte order, units, input selectors, flags, sentinels, API/syscall
  status and capture length. Never interpret unchanged input bytes as returned data.
- Corroborating and conflicting sources, compatibility limits and next offline discriminator.

Status is one of observed-bytes, source-decoded, independently-corroborated, hypothesis,
unresolved or retracted. Binary strings and decompiler guesses start as leads. A host
forwarding stub does not establish the firmware implementation.

## Comparisons
Start with the same component and architecture across neighboring releases. Normalize
relocations, compiler changes and container metadata before claiming behavioral change.
Compare the exact board/SKU and configuration before attributing differences to silicon.

Use NVIDIA headers/driver source/manuals first, then Linux/nouveau/nova implementations
and reproducible independent RE. Keep third-party descriptions as leads when their
artifacts are absent. Two frontends sharing NVML are not independent physical validation.

For cross-generation work provide a compatibility matrix, not a universal inference.
Fields: artifact hashes, architecture, board, OS, driver, firmware, GSP mode, documented
API presence, proven wire schema and unknowns. Signature labels and strings do not prove
consumer SKU support, launch timing or a populated signed image.

## Capture integrity
Retained captures in 06-ground-truth are historical. Compute hashes offline when using
them and record exact files/lengths. A manually transcribed JSON fixture is not a full raw
trace. Never fabricate missing selectors, pairing, timestamps or statuses.
Old configspace-4k filenames are labels, not proof of a 4 KiB read.

## Stopping and reporting
One narrow question per packet. Define a cheapest offline discriminator and stopping rule.
After two unsuccessful approaches without new distinguishing evidence, reassess; continue
another useful offline angle. An unresolved result with a precise missing link is valid.
Updates state artifact, evidence gained, uncertainty and one next action.

## Recorded offline packet

[2026-10-21 control-plane and GA102 boot ledger](research/2026-10-21-offline/README.md)
contains CP-01 through CP-08, raw host disassembly/relocations, retained-log hashes,
source commit/hash manifests, bounded CPU emulation, nearby-release boot comparison,
descriptor bytes/fields/regions, contradictions and unresolved links. Status is
assigned per claim. Synthetic inputs and static routes do not become measurements.

[2026-10-21 P-state dispatch and retained GSP table](research/2026-10-21-pstate-dispatch/README.md)
adds PD-01 through PD-11: retained REA/IDA pseudocode checked against raw bytes,
constructor base reconciliation, shared-memory reader and retry semantics, a
synthetic NVOS54 boundary, 1,183 raw firmware method records, direct firmware
handler/lookup and RUSD setup handlers. Exact 615.71.09 source and independently
implemented nouveau transport are compared with compatibility limits stated.
Seven deterministic analysis JSON files replayed byte-for-byte in CPU-only
namespaces; 38 Python tests and the C/CLI gate passed. Stubbed firmware getter,
historical text-log limits, missing record writer and physical-value origin are
explicit. This does not certify complete access, runtime reachability or health.

[2026-10-21 firmware P-state writer](research/2026-10-21-pstate-writers/README.md)
adds PW-01 through PW-08: callback pointer chain, shared-record helper, exact
internal control arguments and publisher/invalidation instructions. Eight
synthetic writer cases feed their actual output bytes into copied x86 reader
code. Ten analysis JSON files replay byte-for-byte; 41 Python tests plus the C/CLI
gate pass. The internal RM dispatch target, entry getter and timestamp source are
explicit synthetic boundaries, not measured GPU values. Unrelated displacement
scan candidates stay unpromoted; physical-value provenance remains unresolved.

[2026-10-21 callback origins](research/2026-10-21-callback-origins/README.md)
adds CO-01 through CO-08: a raw callback assignment, exact-source compiled RM_API
layout, default-security enum correspondence and copied metadata dispatch. The
initialized callback reaches the P-state handler/lookup with synthetic objects,
one opaque context swap and a stop before the unresolved entry getter. The copied
search matches 1,183 existing records and rejects 18 absent IDs; these are pure
CPU lookups, not control invocations. Ten analysis JSON files replay byte-for-byte;
41 Python tests and the C/CLI gate pass. Actual runtime callback selection, later
overrides, table construction and entry `+0x34` writers remain unknown.

[2026-10-21 object and entry origins](research/2026-10-21-object-origin/README.md)
adds OO-01–08: exact-source class-ID discrimination for GPU `+0x2000`, copied
class/cast metadata, a conditional table construction chain assigning getter
`0x1757ea0`, and one entry `+0x34` writer from a tag-8 input record `+0x0c`.
The copied constructor prefix, array insertion/remapping and handler/getter
execute on synthetic objects with an explicit CPU heap allocator. Five raw-word
cases and two negative cases check transfer/error behavior. Seven deterministic
JSON products replay byte-for-byte; 41 Python tests, C/CLI and offline-record
checks pass. Exact NVIDIA source, pinned nouveau/Nova and independent envytools
formats are compared without equating their schemas. The earlier record producer,
current-index policy, runtime gate/branch selection and all alternate writers
remain unknown; there is no physical measurement or exhaustive access proof.

[2026-10-21 serialized record producer](research/2026-10-21-record-producer/README.md)
adds RP-01–07: copied schema setup establishes a 20-byte header, 556-byte stride
and selector 6. The parsed object's getter returns a present record directly
from that buffer; the copied constructor transfers its `+0x0c` word into entry
`+0x34`. A sparse-mask fixture checks two present records and one absent index.
The acquisition callback creates a memory sub-descriptor; its transfer worker
and actual source storage remain unresolved. Seven JSON products replay exactly;
41 Python tests and C/CLI/offline-record checks pass without GPU access.

## Xid79 boot investigation

[Early firmware boot](research/2026-10-21-gfw-boot/README.md) records the retained
`0x1` failure, exact-release source gate, copied candidate-ROM FWSEC inventory,
public debug-key decode and bounded progress-writer replay. Candidate versus
installed bytes, debug versus production code, and synthetic versus hardware
behavior remain separate. This is not a successful recovery procedure.

The same packet's follow-up reproduces three early checks and conditional raw
error publication in copied debug code (12 fixtures). Four GA102 VBIOS variants
have identical FWSEC components; other ROM data and installed identity remain
unproven. Retained teardown evidence locates a separate DMA queue timeout before
firmware execution. See the packet for boundaries and source hashes.

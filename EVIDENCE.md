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

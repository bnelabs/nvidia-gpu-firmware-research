# What GeForge, GDDRHammer and GPUBreach contribute

These repositories add useful memory-analysis tools and a GSP protocol lead.
They do not demonstrate recovery from our retained GA102 GFW_BOOT failure.
Their main experiments require an operational CUDA/driver environment and
deliberately disturb memory. None was run on hardware here.

The selected source corpus contains 26 files, with Git blob IDs, SHA-256,
byte lengths and immutable URLs in [sources.json](sources.json). Original
sources remain under ignored `vendor/memory-research/`; attack code is not
added to the active tools. This is a scoped review, not a complete audit or
independent reproduction of the papers' hardware results.

| Repository and pinned commit | Useful material retained | Applicability limit |
| --- | --- | --- |
| [GeForge](https://github.com/stefan1wan/GeForge/tree/d3d113a5fcb6b1a7154d18467cf3b4e7174e1d62) | File-based 2 MiB PA/VA translation, alias extraction, candidate alignment, board-layout schema | Reported boards are RTX 3060 and A6000 with GDDR6. Allocation addresses, bank layouts and fingerprints are not our board's measurements. |
| [GDDRHammer](https://github.com/heelsec/GDDRHammer/tree/30673e5433440fcc39dd27833563a29326b61add) | Retained-log row/byte/bit/direction parsing and stable-window analysis | A6000/Samsung GDDR6 setup and chosen timing constants are not validated for our RTX 3090. Its rowhammer/profiling routines are hardware operations. |
| [GPUBreach](https://github.com/sith-lab/gpubreach/tree/237c5744eea98021e3a5ae4c986c83e3ed5830bd) | Copied page-walk formats, address-domain/aperture distinctions, legacy GSP queue/checksum lead | Reference driver is 580.95.05 and GPU is A6000. Dumpers, modifiers, patched-driver setup and exploitation paths were inspected only. |

NVIDIA specifies [RTX 3090 as 24 GB GDDR6X](https://www.nvidia.com/en-eu/geforce/graphics-cards/30-series/rtx-3090/).
Its [GA102 whitepaper](https://www.nvidia.com/content/PDF/nvidia-ampere-ga-102-gpu-architecture-whitepaper-v2.pdf)
identifies A6000 as GA102 with 48 GB GDDR6. Shared silicon architecture does
not prove identical DRAM geometry, refresh timing, allocation placement,
vulnerability, register state or firmware behavior.

## File-only utility checks

[review.py](review.py) runs five reviewed Python utilities against synthetic
files/values inside the CPU-only wrapper. It does not invoke upstream setup,
CUDA programs, smoke dispatchers, page-table acquisition or live profiling.
[review.json](review.json) retains the results and their limits:

- A supplied 2 MiB mapping translates its first/last byte and rejects an
  unmapped bucket or a VA outside the supplied window. This is useful for
  **existing captures**, not a way to obtain physical addresses.
- GeForge's mapping extractor retains multiple VAs for one PA in an alias
  set, while its default exported map keeps the first VA. Preserve both;
  aliasing alone does not prove corruption.
- GeForge's anchor aligner picks the first highest score. A synthetic input
  has two equally matching candidates, but it prints one inferred base PA
  without a tie warning. That address cannot be promoted to unique evidence.
- GDDRHammer's parser counts a record with missing bank as complete, because
  its completeness predicate checks only row/byte/bit/direction. Preserve the
  missing field and the address domain rather than adopting that label.
- GDDRHammer's delay helper returns a numeric fallback when no stable window
  exists. Its comment says index plus 2000 while the code adds 1000. Retain
  the failed-window outcome; neither constants nor fallback are calibration
  evidence for our GPU.

These observations qualify how we can reuse the utilities. They are not
claims that the papers' experiments failed, nor measurements of our card.
The CUDA allocator header also labels its addresses as *expected* placement;
those constants are not measured runtime physical addresses.

## GPUBreach's GSP layout must be versioned

The most relevant protocol lead is its queue helper. Its comments include
conflicting draft structure descriptions; compare the actual NVIDIA source
instead of copying guessed offsets. Pinned NVIDIA 580.95.05 commit
`2b436058a616676ec888ef3814d1db6b2220f2eb` defines the legacy element with
checksum at `+0x20`, sequence at `+0x24`, element count at `+0x28`, and an
eight-byte-aligned RPC member at `+0x30`.

Exact 615.71.09 (`61dcc93722ecb418bb5f2e00923f05b4b8051dd1`) and nearby
615.78.08 (`ca2d03e6fafd4d4b56b383497d931c25b283bfcf`) have byte-identical
`message_queue_priv.h` with a different element:

| Member / build condition | Offset in the copied 615 definition |
| --- | --- |
| MCTP magic / total transfer size | `0x00` / `0x04` |
| MCTP / NVDM header words | `0x08` / `0x0c` |
| NVDM size / payload, no CC, no HWASAN | `0x10` / `0x18` |
| Authentication tag / encrypted NVDM size / payload, CC, no HWASAN | `0x10` / `0x20` / `0x28` |
| Optional HWASAN metadata padding | Adds 8 bytes before the union |

The CPU review compiles the copied structures with integer aliases and a
synthetic RPC placeholder, reporting member offsets in both HWASAN variants.
It does not synthesize queue messages or checksums. CC's size/payload members
are encrypted on the wire; these offsets do not make them readable plaintext.
The file's encryption layout is expressly not ABI stable.

The legacy checksum, sequence and element-count members do **not** describe
this 615 element. Do not reuse GPUBreach's write offsets, inferred IOVAs,
ring sizes, payload templates or assumptions about accepted messages.
This layout difference is not proof of a security fix, safe receiver,
installed binary behavior or a cause of Xid79. Runtime transport/build mode
and any relationship to firmware consumers still need evidence.

Our retained failure occurs before runtime GSP-RM startup. These runtime
memory techniques supply no demonstrated control path around that boot gate.
The recovery priority remains the PRE_OS bit-6-selected callees in the
[boot investigation](../2026-10-21-gfw-boot/README.md).

## Reproduction

With the exact manifest files retained at their listed paths:

```sh
bash scripts/run_cpu_only.sh bash research/2026-10-22-memory-research/reproduce.sh
```

Python 3 and a C compiler are sufficient. The review checks every source hash
before importing the five file utilities or compiling extracted structures.
If rebuilding the corpus, retrieve the immutable file URLs in the manifest as
data and verify their hashes; do not run any upstream installer or dispatcher.

Next protocol task: compare the 615 MCTP/NVDM receive bounds and dispatch
against retained firmware metadata using files and synthetic frames only.
Do not treat an offline decoder as a live queue client or recovery tool.

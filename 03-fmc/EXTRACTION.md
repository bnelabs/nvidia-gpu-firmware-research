# FMC/Booter extraction — offline findings and limits
Earlier extraction notes are retained in archive/2026-10-21-pre-constitution. Counts and
sizes are historical reports until reproduced from hash-keyed input files and exact
archive descriptors. Do not equate every UCODE_IMAGE or GspRmBoot name with one boot role.

A 24–48-byte descriptor cannot be identified as the larger key-bearing LSF_UCODE_DESC
merely because a related header defines that type. Resolve the exact versioned layout,
offsets, consumer and image boundaries before decoding. Field declarations are not
extracted keys.

High entropy alone cannot identify encryption, AES mode, key size or absence of plaintext;
compression and packing are alternatives. Public-source search can constrain a candidate
host path, but does not prove all key material is unreachable or every software research
path requires decapping. Keep unsupported crypto/key claims unresolved.

Permitted work: decode existing bindata arrays and containers, verify hashes/bounds,
decompile copied boot images, compare loaders/versions and emulate isolated code offline.
Prohibited: firmware swaps, debug/fuse reads, GPU-resident extraction, hardware probing
or attempting a boot on the owner's GPU. Unknown encrypted content stays unknown.

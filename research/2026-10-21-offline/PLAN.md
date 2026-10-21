# Offline packet scope

1. **P-state boundary.** Does the copied 615.71.09 host library actually connect
   the public getter to the claimed private control and firmware implementation?
   Alternatives: direct RM, host callback/cache, clock remap, and an unresolved
   transport. Cheapest discriminator: export disassembly, ELF relocations, the
   retained interleaved log, and exact driver dispatch. Stop at any unresolved
   indirect target; keep source routes separate from observed execution.
2. **Nearby GA102 boot versions.** Did the PROD boot component or descriptor change
   between NVIDIA 615.71.09 and 615.78.08? Alternatives: payload change, packaging
   change, or exact equality. Cheapest discriminator: unpack the declared bindata
   storage, validate gzip CRC/size, compare exact bytes and descriptor-bounded code.
   Stop before interpreting opaque manifest/crypto data without a consumer.

All execution uses the CPU-only filesystem/network/device namespace in
`scripts/run_cpu_only.sh`. No target library is loaded into a native process, and
no firmware is booted. Synthetic emulation checks a host conversion routine only.
Hardware-dependent conclusions stay unknown. REA reported the local path unavailable;
that provider path was stopped without privilege changes or remote runtime access.

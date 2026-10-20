# P-state findings — encoding correction and scope
The public RM one-hot enum and the public NVML ordinal enum are different contracts.
RM raw 4=P2 and 256=P8; public NVML P2 is ordinal 2. The old P4/P2 discrepancy was a
decoder error. The 0x2080014a +4 attribution was an input-selector error and is retracted.

Historical library RE reports a clock-remapped fallback on some paths. Treat that as a
version-specific host-library finding needing retained disassembly, not proof of a
physical/virtual discrepancy or an all-generation firmware rule.

No new trace or direct ABI probe is authorized. Reproduce the path offline from the
hash-pinned library and compare source. sniffer2 is now an offline record decoder only.

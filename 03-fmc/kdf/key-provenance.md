# Key provenance — bounded offline assessment
The older all-keys-on-GPU / hardware-attack-required conclusion exceeded its evidence.
A public struct containing prdKeys, dbgKeys or kdf does not prove that the analyzed GSP
artifact uses that layout, where real keys originate, or what a closed verifier does.
Absence of a reference in a source subset is not proof of global absence.

For each candidate identify the exact source commit, component, structure size and field
consumer, then compare it with the extracted descriptor bytes and code. Distinguish
signatures, public keys, encrypted payloads, key-slot identifiers, salts and secret keys.
Record alternative explanations and unsupported links. No secret-key extraction is claimed.

Continue via static decompilation and CPU-only emulation of existing artifacts. No fuse
read, debug-part interaction, GPU-resident code, hardware attack or firmware change is
authorized. The practical constraint is the owner's safety rule, not an assertion that
all remaining scientific questions are impossible.

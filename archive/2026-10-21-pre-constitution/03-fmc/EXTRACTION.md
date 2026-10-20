> HISTORICAL / SUPERSEDED. Not an authorized runbook. Claims may be retracted. Read current CONSTITUTION.md and CORRECTIONS.md at the repository root.

# FMC/Booter firmware extraction and analysis

## What was extracted

All FMC (GSP-FMC/secure ACR) and Boot images from the r615 open-gpu-kernel-modules g_bindata_kgspGetBinArchive* C files, decoded from the NvU64 array format.

### ConcatenatedFMC (Hopper+ FMC, the HS validator code)
- GH100: 421,888 B
- GB100: 434,176 B
- GB202: 478,456 B
- GR100: 429,456 B

### GspRmBoot (the Booter, loaded by SEC2)
- TU102: 816 B (tiny loader stub)
- GA100: 816 B (tiny loader stub)
- GA102: 17,936 B (real Booter, Ampere)
- AD102: 30,240 B (real Booter, Ada)
- GH100: 167,936 B (FMC-class image, Hopper+)
- GB100-GR100: 188-290 KB (FMC-class images)

### UCODE_DESC blobs (24-48 B)
Falcon ucode descriptor: LSF_UCODE_DESC (prdKeys[2][16], dbgKeys[2][16], falconId, version, depMap, kdf[16]) per rmlsfm.h. Contains AES key slots.

## Encryption analysis

All UCODE_IMAGE blobs are AES-encrypted LS payloads:
- Entropy 7.90-7.96 across all regions (max 8.0) = uniformly encrypted
- No plaintext falcon headers visible (stored under encryption)
- GH100 Booter has 1.5 percent trailing zeros (alignment padding)
- LS encryption = AES-128-CBC with prd/dbg key slots from LSF_UCODE_DESC

## Validator feasibility conclusion (REVISED 2026-10-20 after key-provenance analysis)

The original report stated both layers (AES + signature) must be broken. That assumed
AND-gating. Re-evaluation after the key provenance analysis (03-fmc/kdf/key-provenance.md):

**Finding: the AES layer does NOT reduce to the signature layer.** The two layers verify
independently: AES keys are fused on-GPU (never host-readable), while RSA/ECDSA signatures
are verified by the FSP/SEC2 hardware verifier. There is no host-side decryption path that
requires signature forgery, and there is no signature-forgery path that yields plaintext.

### Hypothesis A: KDF strong (default, supported by all static evidence)
- All key material fused on-GPU; host readable surface = descriptor metadata only
- Both layers require hardware access
- Rating: **HARDWARE-ATTACK REQUIRED** (evidence strength: HIGH - source-pinned)

### Hypothesis B: KDF weak (requires observations to confirm/deny)
- If any dbgKeys slot on a debug-fused part were extractable from its own vBIOS
  (they are not, per the current evidence - the vBIOS carries descriptors, not keys),
  or if a dev-part leak exposed a fused key, host-side decryption of LS payloads
  would fall WITHOUT any signature forgery
- Rating: **UNPROVEN** (evidence strength: LOW - no positive evidence of weak keys)

### Observations needed to distinguish A from B
1. A live fuse read of FUSE_OPT_SECURE_GSP_DEBUG_DIS state on a dev part
   (not host-reachable on GeForce; needs nvswitch/debug tooling)
2. A debug-fused part: compare its vBIOS falcon-ucode descriptors against a retail
   part for key-sized payloads (none found in retail vBIOS today)
3. Chip-decap of the falcon key-slot region (hardware attack)
4. Falcon-emulator runs of the KDF with candidate inputs (research-lab only)

### Practical conclusion for custom firmware
- Modifying and re-signing GSP-RM: requires the signature key (NVIDIA-held) AND
  the fused AES key slots - both layers, both hardware-gated
- Loading a modified .fwimage from the host: possible (host has zero enforcement)
  but the GPU rejects it at FMC/GSP boot (signature + AES both fail)
- The reachable attack surface remains: GSP RPC protocol (runtime), vBIOS BIT tables
  (pre-boot), and driver-side handling - not the signed payload chain

**Bottom line: the validator 0-day path is not host-side-feasible under the KDF-strong
hypothesis (static evidence supports it); it converges to a hardware attack.
The AND-gating assumption was WRONG - the layers are independent - but both happen
to be hardware-gated, so the conclusion (hardware required) is unchanged.
Evidence-strength: HIGH for the structural claim, MEDIUM for the absence of weak keys.

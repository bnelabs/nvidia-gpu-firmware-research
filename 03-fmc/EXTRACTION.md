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

## Validator 0-day feasibility conclusion

The FMC/Booter images are AES-encrypted with keys in the falcon security model. Decryption keys are either: in UCODE_DESC blobs (fused on-GPU), derived via KDF from fused root keys, or per-generation.

**Feasibility rating: HARDWARE-ATTACK REQUIRED for full static analysis.**
Without fused AES keys, the FMC/Booter validator code cannot be decrypted from the host side. The validator 0-day path requires: fused key access (chip decap), a KDF vulnerability, or debug-fused hardware. The signature check (RSA-3072/ECDSA P-384) is cryptographically sound against forgery.

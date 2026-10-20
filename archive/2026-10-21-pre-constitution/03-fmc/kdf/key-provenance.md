> HISTORICAL / SUPERSEDED. Not an authorized runbook. Claims may be retracted. Read current CONSTITUTION.md and CORRECTIONS.md at the repository root.

# KDF / AES key provenance analysis (host-side, static)

Question: how are prdKeys, dbgKeys, and kdf[16] populated for the GSP falcon LS decryption?

## Finding: the host driver NEVER touches GSP AES keys

The rmlsfm.h LSF_UCODE_DESC structure (prdKeys[2][16], dbgKeys[2][16], kdf[16] at
rmlsfm.h:235-245) is referenced by exactly two translation units in the entire r615 tree:
soe_lr10.c and soe_ls10.c (nvswitch SOE, data-center path). grep -rln 'rmlsfm.h' src = 3 files.
No GSP, falcon, or ACR source file includes it.

## Evidence table

| Input | Source | Host-readable? | Evidence |
|---|---|---|---|
| prdKeys[2][16] (prod AES keys) | Falcon hardware key slots (fused/OTP, on-GPU) | NO - never in driver memory | rmlsfm.h included only by soe_*.c (nvswitch); no GSP/falcon code references prdKeys |
| dbgKeys[2][16] (debug AES keys) | Same hardware key slots, debug variant (FUSE_OPT_SECURE_GSP_DEBUG_DIS selects) | NO - not in driver; only reachable on debug-fused parts | Same rmlsfm.h scoping evidence |
| kdf[16] (key-derivation salt) | On-GPU KDF (falcon HW), seeded from fused material | NO - the struct field is a definition, never filled by host | LSF_UCODE_DESC defined at rmlsfm.h:231-245, zero references in GSP code |
| FALCON_UCODE_DESC (vBIOS BIT) | vBIOS BIT type-0xE0 falcon-ucode table, parsed by kernel_gsp_fwsec.c | YES (descriptor only: flags, sizes, offsets) - NO KEYS | kernel_gsp_fwsec.c:137-171 (struct), :125-127 (app ids 0x85/0x45); flags field has ENCRYPTED bit 2:2 but no key bytes |
| UCODE_DESC bindata blobs (24-48 B) | g_bindata archives; subset of FALCON_UCODE_DESC (header+sizes) | YES - but contains no keys (too small; LSF_UCODE_DESC is 184 B) | extracted 03-fmc/extracted/*UCODE_DESC*.bin = 24-48 B vs LSF_UCODE_DESC 184 B |
| MessageQueue encryption (bEncryptionEnabled) | gpuIsCCFeatureEnabled(pGpu) - RPC queue AES, key on-GPU | NO - flag host-readable, keys on-GPU | kernel_gsp.c:6166-6167, message_queue_cpu.c:80 |
| SEC2/Booter (pre-Hopper) key material | In vBIOS FWSEC image (AES-encrypted itself); keys inside encrypted blob | NO (circular: to get keys you must already decrypt) | FWSEC loaded from vBIOS type-0xE0, runs HS on GSP falcon (kernel_gsp_fwsec.c) |

## Conclusion

For the GSP falcon, ALL AES key material is on-GPU: fused key slots, OTP, or
HW-KDF output. The host driver's only key-adjacent role is the MESSAGE_QUEUE_INIT_FLAG_ENCRYPTION
flag, which toggles the RPC queue cipher but never touches key bytes.
The vBIOS descriptor carries an ENCRYPTED flag (bit 2:2) but zero key material.

Therefore: host-side decryption-for-analysis requires either (a) capturing key
material from a live GPU via a GPU-resident HS component (not host-reachable),
(b) hardware probing of the falcon key slots, or (c) a debug-fused part
whose dbgKeys are somehow extractable from its own vBIOS (circular - the vBIOS
does not carry them).

The KDF inputs are NOT host-readable. The KDF-strong hypothesis stands by default.

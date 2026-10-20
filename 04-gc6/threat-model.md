# GC6 exit trust-chain shortcut - threat model

**Attacker model first.** The question: can the GC6-exit signature skip (rmlsfm.h:96-97: since we dont check signatures in GC6 exit, we need to hardcode the WPR offset) be used by any attacker to run unverified GSP code?

## (a) Host kernel privileges required?

**Yes - kernel-context PM resume.** The GC6_EXIT boot mode is selected in the host kernel driver power-management resume path, gpu_suspend.c:228 (IS_GPU_GC6_STATE_EXITING -> bootMode = KGSP_BOOT_MODE_GC6_EXIT), invoked from gpuResume. No userland or ioctl path reaches kgspBootstrap with GC6_EXIT: the only call sites are kernel suspend/resume (kernel_gsp_tu102.c:359 + gpu_suspend.c:228). An attacker must already be running kernel code on the host.

**Does it grant anything the attacker did not already have?** No. The signature skip creates no new capability: an attacker with host-kernel execution can already load kernel modules, patch the driver in memory, or DMA. The GC6 skip adds nothing beyond what kernel privilege already grants.

## (b) Persistence across driver reload / reboot?

**No.** GC6 is a runtime power state preserving GPU auxiliary power but not host state across reboot. On the next NORMAL boot the full chain re-verifies: FWSEC-FRTS runs, scrubber runs, Booter Load receives the real WPR meta descriptor and re-checks signatures (kernel_gsp_tu102.c:398-440: NORMAL mode executes FRTS + full init; GC6_EXIT passes boot args = 0 and reuses the WPR as left). A reboot always returns to verified state.

## (c) Guest VM or userland reachability?

**No.** Three boundaries block it:
1. The GC6_EXIT decision is host-kernel-only (gpu_suspend.c:228); guests see only PCI PM states.
2. The trusted state reused at GC6 exit lives inside WPR2 - a hardware write-protected region whose bounds are programmed by FWSEC-FRTS via NV_PFB_PRI_MMU_WPR2_ADDR_LO/HI (kernel_gsp_frts_tu102.c:506-517). Host kernel code cannot write WPR2-protected memory by design; a guest cannot either (MMIO trapped/mediated by the host driver).
3. Userland has no interface to trigger GC6 exit or to write GPU memory inside WPR2.

## Attacker-model verdict

The only attacker who can reach the GC6-exit path is one with host-kernel code execution - who gains nothing (a) and cannot persist anything across reboot (b), because the WPR2 hardware protection (c) prevents modifying the trusted state during the GC6 window in the first place.

Every claim file:line-cited. No cross-boundary escalation, no persistence, no new capability.

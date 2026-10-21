static NvBool
_gpuIsGfwBootCompleted_TU102
(
    OBJGPU  *pGpu,
    NvU8    *pgc6VirtAddr,
    NvU32   *gfwBootProgressVal
)
{
    NvU32 regVal;

    if (pgc6VirtAddr != NULL)
    {
        regVal = MEM_RD32(pgc6VirtAddr +
                          (NV_PGC6_AON_SECURE_SCRATCH_GROUP_05_PRIV_LEVEL_MASK -
                           DEVICE_BASE(NV_PGC6)));
    }
    else
    {
        regVal = GPU_REG_RD32(pGpu, NV_PGC6_AON_SECURE_SCRATCH_GROUP_05_PRIV_LEVEL_MASK);
    }

    //
    // Before reading the actual GFW_BOOT status register,
    // we want to check that FWSEC has lowered its PLM first.
    // If not then obviously it has not completed.
    //
    if (!FLD_TEST_DRF(_PGC6, _AON_SECURE_SCRATCH_GROUP_05_PRIV_LEVEL_MASK,
                      _READ_PROTECTION_LEVEL0, _ENABLE, regVal))
    {
        *gfwBootProgressVal = 0x0;
        return NV_FALSE;
    }

    if (pgc6VirtAddr != NULL)
    {
        regVal = MEM_RD32(pgc6VirtAddr +
                          (NV_PGC6_AON_SECURE_SCRATCH_GROUP_05_0_GFW_BOOT -
                           DEVICE_BASE(NV_PGC6)));
    }
    else
    {
        regVal = GPU_REG_RD32(pGpu, NV_PGC6_AON_SECURE_SCRATCH_GROUP_05_0_GFW_BOOT);
    }

    *gfwBootProgressVal = DRF_VAL(_PGC6, _AON_SECURE_SCRATCH_GROUP_05_0_GFW_BOOT,
                                  _PROGRESS, regVal);

    return FLD_TEST_DRF(_PGC6, _AON_SECURE_SCRATCH_GROUP_05_0_GFW_BOOT,
                        _PROGRESS, _COMPLETED, regVal);
}

#define FWSECLIC_PROG_START_TIMEOUT             50000    // 50ms
#define FWSECLIC_PROG_COMPLETE_TIMEOUT          2000000  // 2s
#define GPU_GFW_BOOT_COMPLETION_TIMEOUT_US      (FWSECLIC_PROG_START_TIMEOUT + \
                                                 FWSECLIC_PROG_COMPLETE_TIMEOUT)
NV_STATUS
gpuWaitForGfwBootComplete_TU102
(
    OBJGPU    *pGpu
)
{
    NvU32        timeoutUs = GPU_GFW_BOOT_COMPLETION_TIMEOUT_US;
    NvU32        gfwBootProgressVal = 0;
    NV_STATUS    status = NV_OK;
    KernelGsp    *pKernelGsp = GPU_GET_KERNEL_GSP(pGpu);
    KernelFalcon *pKernelFalcon = staticCast(pKernelGsp, KernelFalcon);
    NvBool       bGfwBootCompleted = NV_FALSE;

    timeoutUs = gpuScaleTimeout(pGpu, timeoutUs);

    status = kflcnWaitForHalt_HAL(pGpu, pKernelFalcon, timeoutUs, GPU_TIMEOUT_FLAGS_OSTIMER);

    // Get GFW boot progress irrespective of falcon halt status
    bGfwBootCompleted = _gpuIsGfwBootCompleted_TU102(pGpu, NULL, &gfwBootProgressVal);

    if (status != NV_OK)
    {
        NV_PRINTF(LEVEL_ERROR, "GSP failed to halt with GFW_BOOT: (progress 0x%x)\n", gfwBootProgressVal);
        return status;
    }

    if (!bGfwBootCompleted)
    {
        NV_PRINTF(LEVEL_ERROR, "failed to wait for GFW_BOOT: (progress 0x%x)\n", gfwBootProgressVal);
        return NV_ERR_NOT_READY;
    }

    return NV_OK;
}

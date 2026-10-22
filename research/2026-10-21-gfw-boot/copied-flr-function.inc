/*
 * SPDX-FileCopyrightText: Copyright (c) 2017-2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
 * SPDX-License-Identifier: MIT
 *
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 * DEALINGS IN THE SOFTWARE.
 */
NV_STATUS
kbifDoFunctionLevelReset_TU102
(
    OBJGPU    *pGpu,
    KernelBif *pKernelBif
)
{
    NvU32      domain     = gpuGetDomain(pGpu);
    NvU8       bus        = gpuGetBus(pGpu);
    NvU8       device     = gpuGetDevice(pGpu);
    void      *handle     = NULL;
    NV_STATUS  status     = NV_OK;
    NvU32      tempRegVal;
    NvU16      vendorId;
    NvU16      deviceId;
    // 'i'th bit set to 1 indicates NV_MSIX_TABLE_VECTOR_CONTROL(i) is masked
    NvU32      msixVectorMask = 0;
    NvBool     bMSIXEnabled;

    //
    // From the experimental data: We need to get the handle before asserting FLR
    // GPU is always at function 0
    //
    handle = osPciInitHandle(domain, bus, device, 0, &vendorId, &deviceId);

    pKernelBif->bPreparingFunctionLevelReset = NV_TRUE;

    status = kbifSavePcieConfigRegisters_HAL(pGpu, pKernelBif);
    if (status != NV_OK)
    {
        DBG_BREAKPOINT();
        NV_PRINTF(LEVEL_ERROR, "Config registers save failed!\n");
        goto bifDoFunctionLevelReset_TU102_exit;
    }

    bMSIXEnabled = kbifIsMSIXEnabledInHW_HAL(pGpu, pKernelBif);
    if (bMSIXEnabled)
    {
        msixVectorMask = _kbifSaveMSIXVectorControlMasks(pGpu, pKernelBif);
    }

    pKernelBif->bPreparingFunctionLevelReset = NV_FALSE;
    if (pKernelBif->getProperty(pKernelBif, PDB_PROP_KBIF_FLR_PRE_CONDITIONING_REQUIRED))
    {
        //
        // SW WARs required for Function Level Reset -
        // Clear Bus Master Enable bit in command register so that no more requests to sysmem are made by Fn0
        // Executing these WARs after save config space so that restore config space does not restore-
        // incorrect command register
        // For other WARs which are executed in kbifPrepareForFullChipReset_HAL, gpu re-init sequence after FLR makes
        // sure to revert these WARs
        //
        if (kbifStopSysMemRequests_HAL(pGpu, pKernelBif, NV_TRUE) != NV_OK)
        {
            NV_PRINTF(LEVEL_ERROR, "BIF Stop Sys Mem requests failed.\n");
            DBG_BREAKPOINT();
        }
        // Wait for number of sysmem transactions pending to go to 0
        if (kbifWaitForTransactionsComplete_HAL(pGpu, pKernelBif) != NV_OK)
        {
            NV_PRINTF(LEVEL_ERROR,
                      "BIF Wait for Transactions complete failed.\n");
            DBG_BREAKPOINT();
        }
    }

    // Trigger FLR now
    kbifTriggerFlr_HAL(pGpu, pKernelBif);

    pKernelBif->bInFunctionLevelReset = NV_TRUE;

    {
        // Wait for 100 ms before attempting to read PCI config space
        osDelayUs(100000);
    }

    status = kbifRestorePcieConfigRegisters_HAL(pGpu, pKernelBif);
    if (status != NV_OK)
    {
        DBG_BREAKPOINT();
        NV_PRINTF(LEVEL_ERROR, "Config registers restore failed!\n");
        goto bifDoFunctionLevelReset_TU102_exit;
    }

    // As of GA10X, miata rom cannot be run on simulation.
    if (IS_SILICON(pGpu) || IS_EMULATION(pGpu))
    {
        // On emulation VBIOS boot can take long so add prints for better visibility
        if (IS_EMULATION(pGpu))
        {
            NV_PRINTF(LEVEL_ERROR, "Entering secure boot completion wait.\n");
        }

        if (IS_GSP_CLIENT(pGpu))
        {
            status = gpuWaitForGfwBootComplete_HAL(pGpu);
        }
        else
        {
            status = NV_ERR_NOT_SUPPORTED;
        }
        if (status != NV_OK)
        {
            DBG_BREAKPOINT();
            NV_PRINTF(LEVEL_ERROR, "VBIOS boot failed!!\n");
            goto bifDoFunctionLevelReset_TU102_exit;
        }
        if (IS_EMULATION(pGpu))
        {
            NV_PRINTF(LEVEL_ERROR,
                      "Exited secure boot completion wait with status = NV_OK.\n");
        }
    }

    if (bMSIXEnabled)
    {
        // TODO-NM: Check if this needed for other NVPM flows like GC6
        _kbifRestoreMSIXVectorControlMasks(pGpu, pKernelBif, msixVectorMask);
    }

    //
    // After FLR 'outstanding downstream read counter' does not reflect the
    // correct value until cleared. We clear this counter without checking if
    // FLR succeeded or not. This is considering that we will attempt SBR after
    // FLR fails and if we don't clear this counter here, it will not reflect
    // the correct value after SBR (SBR does not clear it).
    //
    kbifClearDownstreamReadCounter_HAL(pGpu, pKernelBif);

    // Re-init handle as well since gpu is reset
    handle = osPciInitHandle(domain, bus, device, 0, &vendorId, &deviceId);
    tempRegVal = osPciReadDword(handle, NV_XVE_ID);
    if (!FLD_TEST_DRF(_XVE, _ID, _VENDOR, _NVIDIA, tempRegVal))
    {
        status = NV_ERR_GENERIC;
        goto bifDoFunctionLevelReset_TU102_exit;
    }

bifDoFunctionLevelReset_TU102_exit:
    pKernelBif->bPreparingFunctionLevelReset = NV_FALSE;
    pKernelBif->bInFunctionLevelReset        = NV_FALSE;
    return status;
}

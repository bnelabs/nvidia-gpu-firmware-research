#include <stddef.h>
#include <stdio.h>
#include "class/cl00de.h"
#include "ctrl/ctrl00de.h"
#include "nvos.h"
#include "ctrl/ctrl2080/ctrl2080internal.h"
int main(void)
{
    printf("{\"NV00DE_SHARED_DATA_size\":%zu,\"perfCurrentPstate_offset\":%zu,"
           "\"RUSD_PERF_CURRENT_PSTATE_size\":%zu,\"currentPstate_offset\":%zu,"
           "\"lastModifiedTimestamp_offset\":%zu,\"request_data_poll_size\":%zu,"
           "\"poll_perf_mask\":%u,\"NVOS54_size\":%zu,\"NVOS54_cmd_offset\":%zu,"
           "\"NVOS54_params_offset\":%zu,\"NVOS54_paramsSize_offset\":%zu,"
           "\"NVOS54_status_offset\":%zu,\"internal_poll_params_size\":%zu}\n",
           sizeof(NV00DE_SHARED_DATA), offsetof(NV00DE_SHARED_DATA, perfCurrentPstate),
           sizeof(RUSD_PERF_CURRENT_PSTATE), offsetof(RUSD_PERF_CURRENT_PSTATE, currentPstate),
           offsetof(RUSD_PERF_CURRENT_PSTATE, lastModifiedTimestamp),
           sizeof(NV00DE_CTRL_REQUEST_DATA_POLL_PARAMS), NV00DE_RUSD_POLL_PERF,
           sizeof(NVOS54_PARAMETERS), offsetof(NVOS54_PARAMETERS, cmd),
           offsetof(NVOS54_PARAMETERS, params), offsetof(NVOS54_PARAMETERS, paramsSize),
           offsetof(NVOS54_PARAMETERS, status),
           sizeof(NV2080_CTRL_INTERNAL_USER_SHARED_DATA_SET_DATA_POLL_PARAMS));
    return 0;
}

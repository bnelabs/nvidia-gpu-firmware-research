/* nvos54_shim.h — minimal standalone NVOS54/NVOS64 + alloc-param shims for offline tests.
 * Mirrors the pinned open-gpu-kernel-modules layouts (commit ca2d03e) without pulling
 * the full SDK include tree; verified against nvos.h/cl0000.h/cl0080.h/cl2080.h. */
#ifndef NVOS54_SHIM_H
#define NVOS54_SHIM_H

#include <stdint.h>
#include <sys/ioctl.h>

typedef uint32_t NvU32;
typedef uint64_t NvU64;
typedef uint32_t NvHandle;
typedef void *NvP64;

#define NV_ALIGN8 __attribute__((aligned(8)))

typedef struct {                     /* nvos.h NVOS64_PARAMETERS (48 B) */
    NvU32    hRoot;
    NvU32    hObjectParent;
    NvU32    hObjectNew;
    NvU32    hClass;
    NvP64    pAllocParms  NV_ALIGN8;
    NvP64    pRightsRequested NV_ALIGN8;
    NvU32    paramsSize;
    NvU32    flags;
    NvU32    status;
} NVOS64_PARAMETERS;

typedef struct {                     /* nvos.h NVOS54_PARAMETERS (32 B) */
    NvU32    hClient;
    NvU32    hObject;
    NvU32    cmd;
    NvU32    flags;
    NvP64    params       NV_ALIGN8;
    NvU32    paramsSize;
    NvU32    status;
} NVOS54_PARAMETERS;

typedef struct {                     /* cl0000.h NV0000_ALLOC_PARAMETERS */
    NvHandle hClient;
    NvU32    processID;
    char     processName[64];
    NvP64    pOsPidInfo   NV_ALIGN8;
} NV0000_ALLOC_PARAMETERS;

typedef struct {                     /* cl0080.h NV0080_ALLOC_PARAMETERS */
    NvU32    deviceId;
    NvHandle hClientShare;
    NvHandle hTargetClient;
    NvHandle hTargetDevice;
    NvU32     flags;
    NvU64    vaSpaceSize  NV_ALIGN8;
    NvU64    vaStartInternal NV_ALIGN8;
    NvU64    vaLimitInternal NV_ALIGN8;
    NvU32    vaMode;
} NV0080_ALLOC_PARAMETERS;

typedef struct {                     /* cl2080.h NV2080_ALLOC_PARAMETERS */
    NvU32    hSubDevice;
} NV2080_ALLOC_PARAMETERS;

#endif

/*
 * rmctl v0.1 — userspace NVIDIA RM-control probe (READ-ONLY)
 * -----------------------------------------------------------
 * Builds against the PUBLIC open-gpu-kernel-modules headers (vendor/).
 * Smoke test only: NV2080_CTRL_CMD_GSP_GET_FEATURES (0x20803601) — a pure
 * read of GSP capability bits + firmware build string. Equivalent in kind
 * to what `nvidia-smi -q` does internally; mutates nothing.
 *
 * Recipe (all verified in source, see 07-prototype/rmctl-notes.md):
 *   /dev/nvidiactl, /dev/nvidia0
 *   NV_ESC_RM_ALLOC=0x2B, NV_ESC_RM_CONTROL=0x2A, NV_ESC_RM_FREE=0x29
 *     (src/nvidia/arch/nvalloc/unix/include/nv_escape.h:31-34)
 *   NVOS21_PARAMETERS (alloc), NVOS54_PARAMETERS (control)  (nvos.h)
 *   classes: NV01_ROOT=0x0, NV01_DEVICE_0=0x80, NV20_SUBDEVICE_0=0x2080
 *
 * Build:
 *   ./build.sh   (adds -I vendor/open-gpu-kernel-modules/... include paths)
 *
 * SAFETY RULES
 *   - This binary implements ONLY the read-only probe below. Never add
 *     mutating controls (power/clock/fan) without the P4 test-bench rule.
 *   - On the production rig, read-only probes are permitted (nvidia-smi class).
 */
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <sys/ioctl.h>

#include "pstate_decode.h"
#include "nvtypes.h"
#include "nvos.h"
#include "class/cl0000.h"
#include "class/cl0080.h"
#include "class/cl2080.h"
#include "ctrl/ctrl2080/ctrl2080gsp.h"
#include "ctrl/ctrl2080/ctrl2080clk.h"
#include "ctrl/ctrl2080/ctrl2080perf.h"

/* escape numbers (nv_escape.h) + ioctl encoding — the kernel validates
 * _IOC_TYPE==NV_IOCTL_MAGIC('F') and the exact _IOC_SIZE per escape
 * (nv.c nv_ioctls_table + rm_validate_ioctls; empirically confirmed via
 * strace of nvidia-smi/NVML: ALLOC uses NVOS64 (48 B), CONTROL NVOS54 (32 B)) */
#define RCTL_MAGIC             'F'
#define RCTL_ESC_ALLOC         0x2B
#define RCTL_ESC_CONTROL       0x2A
#define RCTL_ESC_FREE          0x29
#define RCTL_ESC_CHECK_VERSION 0xD2   /* NV_IOCTL_BASE + 10 */
#define RCTL_IOCTL(esc, type)   _IOWR(RCTL_MAGIC, esc, type)

/* nv_ioctl_rm_api_version_t (nv-ioctl.h): cmd, reply, versionString[64] */
typedef struct {
    NvU32 cmd;
    NvU32 reply;
    char  versionString[64];
} rctl_api_version_t;

static int rm_alloc(int fd, NvHandle hRoot, NvHandle hParent, NvV32 cls,
                    void *params, NvU32 paramsSize, NvHandle *out)
{
    NVOS64_PARAMETERS a;
    memset(&a, 0, sizeof(a));
    a.hRoot             = hRoot;
    a.hObjectParent     = hParent;
    a.hObjectNew        = 0;          /* 0 = RM generates the handle */
    a.hClass            = cls;
    a.pAllocParms       = params;     /* NvP64 == void* on 64-bit */
    a.pRightsRequested  = NULL;       /* no RS_ACCESS_MASK rights requested */
    a.paramsSize        = paramsSize;
    a.flags             = NVOS64_FLAGS_NONE;
    if (ioctl(fd, RCTL_IOCTL(RCTL_ESC_ALLOC, NVOS64_PARAMETERS), &a) != 0) {
        perror("ioctl(NV_ESC_RM_ALLOC)");
        return -1;
    }
    if (a.status != 0) {
        fprintf(stderr, "RM_ALLOC class=0x%x status=0x%x (see nvstatuscodes.h)\n", cls, a.status);
        return -1;
    }
    *out = a.hObjectNew;
    return 0;
}

static int rm_free(int fd, NvHandle hRoot, NvHandle hObject)
{
    NVOS00_PARAMETERS f;
    memset(&f, 0, sizeof(f));
    f.hRoot = hRoot;
    f.hObjectOld = hObject;
    return ioctl(fd, RCTL_IOCTL(RCTL_ESC_FREE, NVOS00_PARAMETERS), &f);
}

int main(void)
{
    int ctl = -1, dev = -1;
    NvHandle hClient = 0, hDevice = 0, hSub = 0;
    int rc = 1;

    ctl = open("/dev/nvidiactl", O_RDWR);
    if (ctl < 0) { perror("open(/dev/nvidiactl)"); return 1; }
    dev = open("/dev/nvidia0", O_RDWR);
    if (dev < 0) { perror("open(/dev/nvidia0)"); goto out; }

    /* 0) API version handshake — QUERY ('2') makes RM return its version string */
    rctl_api_version_t ver;
    memset(&ver, 0, sizeof(ver));
    ver.cmd = '2'; /* NV_RM_API_VERSION_CMD_QUERY */
    if (ioctl(ctl, RCTL_IOCTL(RCTL_ESC_CHECK_VERSION, rctl_api_version_t), &ver) != 0) {
        perror("ioctl(CHECK_VERSION_STR)");
    } else {
        printf("rmctl probe\n  rm api version        : %s (reply=%d)\n", ver.versionString, ver.reply);
    }

    /* 1) root client */
    NV0000_ALLOC_PARAMETERS ap;
    memset(&ap, 0, sizeof(ap));
    if (rm_alloc(ctl, 0, 0, NV01_ROOT, &ap, sizeof(ap), &hClient) != 0) goto out;

    /* 2) device object — allocated on the CTL fd; NV0080.deviceId selects the GPU
     *    (empirical: NVML issues ALLOC on nvidiactl; deviceId=0 = first GPU) */
    NV0080_ALLOC_PARAMETERS dp;
    memset(&dp, 0, sizeof(dp));
    dp.deviceId      = 0;
    dp.hClientShare  = hClient;
    dp.hTargetClient = hClient;
    dp.hTargetDevice = 0;
    dp.vaMode        = NV_DEVICE_ALLOCATION_VAMODE_OPTIONAL_MULTIPLE_VASPACES; /* 0 */
    if (rm_alloc(ctl, hClient, hClient, NV01_DEVICE_0, &dp, sizeof(dp), &hDevice) != 0) goto out;

    /* 3) subdevice object (also on ctl fd, parent = device) */
    NV2080_ALLOC_PARAMETERS sp;
    memset(&sp, 0, sizeof(sp));
    if (rm_alloc(ctl, hClient, hDevice, NV20_SUBDEVICE_0, &sp, sizeof(sp), &hSub) != 0) goto out;

    /* 4) READ-ONLY probe: GSP features + firmware build string */
    NV2080_CTRL_GSP_GET_FEATURES_PARAMS feat;
    memset(&feat, 0, sizeof(feat));
    NVOS54_PARAMETERS c;
    memset(&c, 0, sizeof(c));
    c.hClient    = hClient;
    c.hObject    = hSub;
    c.cmd        = NV2080_CTRL_CMD_GSP_GET_FEATURES;   /* 0x20803601 */
    c.flags      = NVOS54_FLAGS_NONE;
    c.params     = &feat;
    c.paramsSize = sizeof(feat);

    if (ioctl(ctl, RCTL_IOCTL(RCTL_ESC_CONTROL, NVOS54_PARAMETERS), &c) != 0) {
        perror("ioctl(NV_ESC_RM_CONTROL)");
        goto out;
    }
    if (c.status != 0) {
        fprintf(stderr, "RM_CONTROL 0x20803601 status=0x%x\n", c.status);
        goto out;
    }

    printf("  client/device/subdevice : 0x%x / 0x%x / 0x%x\n", hClient, hDevice, hSub);
    printf("  gsp.bValid              : %d\n", feat.bValid);
    printf("  gsp.bDefaultGspRmGpu    : %d\n", feat.bDefaultGspRmGpu);
    printf("  gsp.gspFeatures         : 0x%08x\n", feat.gspFeatures);
    printf("  gsp.firmwareVersion     : %s\n", feat.firmwareVersion);

    /* 5) READ-ONLY probe #2: PMUMON clock-domain samples (PMU monitoring queue;
     *    in the OPEN SDK headers — CLK/FAN/VOLT families are NOT, they live in
     *    the closed gsp.bin GSP RM per userspace-control.md's tree-wide grep) */
    {
        static NV2080_CTRL_CLK_PMUMON_CLK_DOMAINS_GET_SAMPLES_PARAMS pm;
        memset(&pm, 0, sizeof(pm));
        NVOS54_PARAMETERS c2;
        memset(&c2, 0, sizeof(c2));
        c2.hClient    = hClient;
        c2.hObject    = hSub;
        c2.cmd        = NV2080_CTRL_CMD_CLK_PMUMON_CLK_DOMAINS_GET_SAMPLES; /* 0x20801037 */
        c2.flags      = NVOS54_FLAGS_NONE;
        c2.params     = &pm;
        c2.paramsSize = sizeof(pm);
        if (ioctl(ctl, RCTL_IOCTL(RCTL_ESC_CONTROL, NVOS54_PARAMETERS), &c2) != 0)
            perror("ioctl(PMUMON_GET_SAMPLES)");
        else if (c2.status != 0)
            fprintf(stderr, "PMUMON_GET_SAMPLES status=0x%x\n", c2.status);
        else
            printf("  pmumon.samplesReturned  : %u (last gpcClk=%u KHz)\n",
                   pm.super.numSamples,
                   pm.super.numSamples ? pm.samples[pm.super.numSamples - 1].activeGpcClkFreqKHz : 0);
    }
    /* 6) READ-ONLY probe #3: current P-state (open SDK: ctrl2080perf.h) */
    {
        NV2080_CTRL_PERF_GET_CURRENT_PSTATE_PARAMS ps;
        memset(&ps, 0, sizeof(ps));
        NVOS54_PARAMETERS c3;
        memset(&c3, 0, sizeof(c3));
        c3.hClient    = hClient;
        c3.hObject    = hSub;
        c3.cmd        = NV2080_CTRL_CMD_PERF_GET_CURRENT_PSTATE; /* 0x20802068 */
        c3.flags      = NVOS54_FLAGS_NONE;
        c3.params     = &ps;
        c3.paramsSize = sizeof(ps);
        if (ioctl(ctl, RCTL_IOCTL(RCTL_ESC_CONTROL, NVOS54_PARAMETERS), &c3) != 0)
            perror("ioctl(PERF_GET_CURRENT_PSTATE)");
        else if (c3.status != 0)
            fprintf(stderr, "PERF_GET_CURRENT_PSTATE status=0x%x\n", c3.status);
        else {
            int ordinal = rm_pstate_ordinal(ps.currPstate);
            if (ordinal >= 0)
                printf("  perf.currPstate         : 0x%x (P%d)\n", ps.currPstate, ordinal);
            else
                printf("  perf.currPstate         : 0x%x (undefined/unsupported encoding)\n", ps.currPstate);
        }
    }
    /* 0x2080014a is an identity query, not a P-state source. The previous
     * probe printed an input selector as P-state and embedded a host UUID.
     * Removed pending a validated NVML P-state response contract. */
    /* 8) READ-ONLY probe #5: CLOSED control 0x2080a61d — 12B power response
     *    (sniffer-verified: u32 mW @+4, e.g. 370000 = 370 W on this board). */
    {
        unsigned char pw[12];
        memset(pw, 0, sizeof(pw));
        NVOS54_PARAMETERS c5;
        memset(&c5, 0, sizeof(c5));
        c5.hClient    = hClient;
        c5.hObject    = hSub;
        c5.cmd        = 0x2080a61d;
        c5.flags      = NVOS54_FLAGS_NONE;
        c5.params     = pw;
        c5.paramsSize = sizeof(pw);
        if (ioctl(ctl, RCTL_IOCTL(RCTL_ESC_CONTROL, NVOS54_PARAMETERS), &c5) != 0)
            perror("ioctl(0x2080a61d)");
        else if (c5.status != 0)
            fprintf(stderr, "0x2080a61d status=0x%x\n", c5.status);
        else {
            unsigned mw;
            memcpy(&mw, pw + 4, 4);
            printf("  power candidate (+4)    : %u mW (%u.%03u W)  raw=%02x%02x%02x%02x %02x%02x%02x%02x %02x%02x%02x%02x\n",
                   mw, mw / 1000, mw % 1000,
                   pw[0], pw[1], pw[2], pw[3], pw[4], pw[5], pw[6], pw[7],
                   pw[8], pw[9], pw[10], pw[11]);
        }
    }
    rc = 0;

out:
    if (hSub)     rm_free(ctl, hClient, hSub);
    if (hDevice)  rm_free(ctl, hClient, hDevice);
    if (hClient)  rm_free(ctl, hClient, hClient);
    if (dev >= 0) close(dev);
    if (ctl >= 0) close(ctl);
    return rc;
}

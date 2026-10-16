/* fake_rm_multi.c — changing-outputs test: 3 PMUMON calls in one process against the
 * fake backend, expecting last-sample KHz 210000/211000/212000 (deterministic increments)
 * and stale-input rejection when the super metadata is deliberately modified. */
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include "nvos.h"
#include "class/cl0000.h"
#include "class/cl0080.h"
#include "class/cl2080.h"
#include "ctrl/ctrl2080/ctrl2080clk.h"

#define PSZ sizeof(NV2080_CTRL_CLK_PMUMON_CLK_DOMAINS_GET_SAMPLES_PARAMS)
/* freq offset via struct: samples[249].activeGpcClkFreqKHz */

static int ctl = -1;
static unsigned hClient, hDev, hSub;

static int alloc_chain(void)
{
    NVOS64_PARAMETERS a = {0};
    NV0000_ALLOC_PARAMETERS ap = {0};
    a.hRoot = 0; a.hObjectParent = 0; a.hClass = 0x0;
    a.pAllocParms = &ap; a.paramsSize = sizeof(ap);
    if (ioctl(ctl, _IOWR('F', 0x2b, NVOS64_PARAMETERS), &a)) return -1;
    if (a.status) return -1;
    hClient = a.hObjectNew;

    NV0080_ALLOC_PARAMETERS dp = {0};
    dp.deviceId = 0; dp.hClientShare = hClient; dp.hTargetClient = hClient;
    NVOS64_PARAMETERS d = {0};
    d.hRoot = hClient; d.hObjectParent = hClient; d.hClass = 0x80;
    d.pAllocParms = &dp; d.paramsSize = sizeof(dp);
    if (ioctl(ctl, _IOWR('F', 0x2b, NVOS64_PARAMETERS), &d)) return -1;
    if (d.status) return -1;
    hDev = d.hObjectNew;

    NV2080_ALLOC_PARAMETERS sp = {0};
    NVOS64_PARAMETERS s = {0};
    s.hRoot = hClient; s.hObjectParent = hDev; s.hClass = 0x2080;
    s.pAllocParms = &sp; s.paramsSize = sizeof(sp);
    if (ioctl(ctl, _IOWR('F', 0x2b, NVOS64_PARAMETERS), &s)) return -1;
    if (s.status) return -1;
    hSub = s.hObjectNew;
    return 0;
}

static unsigned pmumon_call(int mutate_super)
{
    static NV2080_CTRL_CLK_PMUMON_CLK_DOMAINS_GET_SAMPLES_PARAMS pm;
    static int first = 1;
    if (first) { memset(&pm, 0, sizeof(pm)); first = 0; }
    if (mutate_super)
        ((unsigned char *)&pm)[0] = 0xFF; /* corrupt super metadata */

    NVOS54_PARAMETERS c = {0};
    c.hClient = hClient; c.hObject = hSub; c.cmd = 0x20801037;
    c.flags = 0; c.params = &pm; c.paramsSize = sizeof(pm);
    if (ioctl(ctl, _IOWR('F', 0x2a, NVOS54_PARAMETERS), &c)) return 0xFFFFFFFF;
    if (c.status) return 0xFFFFFF00 | c.status;
    unsigned n, last;
    memcpy(&n, &pm.super.numSamples, 4);
    memcpy(&last, &pm.samples[249].activeGpcClkFreqKHz, 4);
    printf("n=%u last=%u\n", n, last);
    return last;
}

int main(void)
{
    ctl = open("/dev/nvidiactl", O_RDWR);
    if (ctl < 0) { perror("open"); return 1; }
    if (alloc_chain()) { fprintf(stderr, "alloc chain failed\n"); return 1; }

    unsigned a = pmumon_call(0);
    unsigned b = pmumon_call(0);
    unsigned c = pmumon_call(0);
    printf("seq: %u %u %u\n", a, b, c);
    if (!(a == 210249 && b == 211249 && c == 212249)) {
        fprintf(stderr, "FAIL changing outputs\n");
        return 1;
    }
    /* stale-input rejection: corrupt super → expect status byte 0x56 in the mask */
    unsigned bad = pmumon_call(1);
    if ((bad & 0xFFFFFF00) != 0xFFFFFF00 || (bad & 0xFF) != 0x56) {
        fprintf(stderr, "FAIL stale-input rejection (got 0x%x)\n", bad);
        return 1;
    }
    printf("stale-input rejected with 0x56\n");
    return 0;
}

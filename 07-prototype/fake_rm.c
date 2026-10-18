/* fake_rm.c — deterministic offline RM-UAPI backend (packet 1, lead-reviewed design).
 *
 * Uses VENDOR struct definitions (pinned open-gpu-kernel-modules headers) with
 * compile-time ABI assertions — no second handwritten ABI.
 *
 * Isolation (REVIEW finding 5): open/openat of "/dev/nvidia*" is intercepted and
 * served from a fixture descriptor pool; ioctls on fixture descriptors are handled
 * inside the fixture or FAIL CLOSED (never forwarded to a real device). Test runs
 * therefore perform zero real NVIDIA device access, provable by strace (no
 * /dev/nvidia openat, no ioctl on real NVIDIA fds).
 *
 * Env knobs: FAKE_FAIL=1 (syscall failure), FAKE_STATUS=0xNN (RM rejection),
 * FAKE_PSTATE=0xNN (PSTATE payload), FAKE_PMUMON_N=<n> (sample count override),
 * FAKE_SENTINEL=1 (mark last clock invalid), FAKE_DEBUG=1 (dispatch trace).
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/stat.h>

#include "nvos.h"
#include "class/cl0000.h"
#include "class/cl0080.h"
#include "class/cl2080.h"
#include "ctrl/ctrl2080/ctrl2080gsp.h"
#include "ctrl/ctrl2080/ctrl2080clk.h"
#include "ctrl/ctrl2080/ctrl2080perf.h"
#include <stddef.h>

/* ---- compile-time ABI assertions against pinned vendor headers ---- */
_Static_assert(sizeof(NVOS54_PARAMETERS) == 32, "NVOS54 size");
_Static_assert(offsetof(NVOS54_PARAMETERS, status) == 28, "NVOS54 status offset");
_Static_assert(sizeof(NVOS64_PARAMETERS) == 48, "NVOS64 size");
_Static_assert(offsetof(NVOS64_PARAMETERS, status) == 40, "NVOS64 status offset");
_Static_assert(offsetof(NVOS54_PARAMETERS, params) == 16, "NVOS54 params offset");
_Static_assert(sizeof(NV2080_CTRL_GSP_GET_FEATURES_PARAMS) == 72, "GET_FEATURES size");
_Static_assert(sizeof(NV2080_CTRL_CLK_PMUMON_CLK_DOMAINS_GET_SAMPLES_PARAMS) == 6024,
               "PMUMON params size");

static int fake_fds[1024];          /* fd -> 1 if served by the fixture */
static unsigned next_handle = 0x1000;
static unsigned pmumon_calls = 0;
static unsigned char super_copy[sizeof(NV2080_CTRL_PMUMON_GET_SAMPLES_SUPER)];
static int super_seen = 0;
static int (*real_ioctl)(int, unsigned long, void *);
static int (*real_open)(const char *, int, ...);

static unsigned env_hex(const char *name, unsigned dflt)
{
    const char *v = getenv(name);
    return v ? (unsigned)strtoul(v, NULL, 0) : dflt;
}

static void trace(const char *fmt, ...)
{
    if (!getenv("FAKE_DEBUG")) return;
    va_list ap; va_start(ap, fmt);
    vfprintf(stderr, fmt, ap);
    fputc('\n', stderr);
    va_end(ap);
}

static int is_fake_fd(int fd)
{
    return fd >= 0 && fd < 1024 && fake_fds[fd];
}

static int pool_fake_fd(void)
{
    if (!real_open)
        real_open = (int (*)(const char *, int, ...))dlsym(RTLD_NEXT, "open");
    int fd = real_open("/dev/null", O_RDWR);
    if (fd >= 0 && fd < 1024)
        fake_fds[fd] = 1;
    return fd;
}

/* --- intercepted open: /dev/nvidia* never reaches the kernel --- */
int open(const char *path, int flags, ...)
{
    if (!strncmp(path, "/dev/nvidia", 11)) {
        trace("[fake] open(%s) -> fixture fd", path);
        return pool_fake_fd();
    }
    if (!real_open)
        real_open = (int (*)(const char *, int, ...))dlsym(RTLD_NEXT, "open");
    return real_open(path, flags);
}

int open64(const char *path, int flags, ...)
{
    return open(path, flags);
}

/* --- control dispatch: return RM status (ioctl itself always succeeds) --- */
static unsigned dispatch_control(unsigned cmd, void *params, unsigned psize)
{
    unsigned forced = env_hex("FAKE_STATUS", 0);
    if (forced)
        return forced;

    switch (cmd) {
    case 0x20803601: { /* GSP GET_FEATURES */
        if (psize < sizeof(NV2080_CTRL_GSP_GET_FEATURES_PARAMS))
            return 0x56; /* undersized */
        NV2080_CTRL_GSP_GET_FEATURES_PARAMS *p = params;
        p->gspFeatures = 1;
        p->bValid = 1;
        p->bDefaultGspRmGpu = 1;
        strcpy(p->firmwareVersion, "615.71.09-fake");
        return 0;
    }
    case 0x20801037: { /* PMUMON clock-domain samples */
        if (psize < sizeof(NV2080_CTRL_CLK_PMUMON_CLK_DOMAINS_GET_SAMPLES_PARAMS))
            return 0x56; /* REVIEW finding 2: reject undersized before any access */
        NV2080_CTRL_CLK_PMUMON_CLK_DOMAINS_GET_SAMPLES_PARAMS *p = params;
        /* stale-input check: incoming super must match what the LAST call left
         * (super fields are in/out; the fixture fills them, callers pass back). */
        if (super_seen && memcmp(&p->super, super_copy, sizeof(super_copy)) != 0)
            return 0x56; /* stale/modified metadata rejected */
        pmumon_calls++;
        unsigned requested = env_hex("FAKE_PMUMON_N", 250);
        if (requested > 250) requested = 250;
        p->super.numSamples = requested;
        for (unsigned i = 0; i < requested; i++) {
            p->samples[i].activeGpcClkFreqKHz =
                210000u + 1000u * (pmumon_calls - 1) + i;
        }
        if (getenv("FAKE_SENTINEL"))
            p->samples[requested - 1].activeGpcClkFreqKHz = 0xFFFFFFFFu;
        memcpy(super_copy, &p->super, sizeof(super_copy)); /* post-call state */
        super_seen = 1;
        return 0;
    }
    case 0x20802068: { /* PSTATE one-hot */
        if (psize < sizeof(NV2080_CTRL_PERF_GET_CURRENT_PSTATE_PARAMS))
            return 0x56;
        NV2080_CTRL_PERF_GET_CURRENT_PSTATE_PARAMS *p = params;
        p->currPstate = env_hex("FAKE_PSTATE", 0x100); /* P8 default */
        return 0;
    }
    case 0x2080a61d: { /* power fixture: u32 mW @+4 (hypothesis, not hardware) */
        if (psize < 12) return 0x56;
        unsigned char *b = params;
        b[0] = 0x01; b[1] = 0xfe; b[2] = 0x00; b[3] = 0x00;
        unsigned mw = 370000;
        memcpy(b + 4, &mw, 4);
        return 0;
    }
    default:
        return 0x56; /* not part of this fixture: fail closed */
    }
}

static int fake_ioctl(int fd, unsigned long cmd, void *arg)
{
    if (getenv("FAKE_FAIL")) { errno = ENOTTY; return -1; } /* syscall-failure mode */
    unsigned magic = (cmd >> 8) & 0xff, nr = cmd & 0xff, size = (cmd >> 16) & 0x3fff;

    if (!is_fake_fd(fd))
        goto forward; /* only fixture descriptors are emulated */

    if (magic != 'F') { trace("[fake] non-'F' ioctl fail-closed"); errno = EINVAL; return -1; }

    if (nr == 0xd2 && size == 72) { /* version check */
        char *p = arg;
        memset(p, 0, 72);
        p[0] = '2'; p[4] = 1;
        strcpy(p + 8, "615.71.09-fake");
        return 0;
    }
    if (nr == 0x2b && size == 48) { /* NVOS64 alloc */
        NVOS64_PARAMETERS *a = arg;
        switch (a->hClass) {
        case 0x0:    a->hObjectNew = ++next_handle; break;
        case 0x80:   a->hObjectNew = ++next_handle; break;
        case 0x2080: a->hObjectNew = ++next_handle; break;
        default:     a->status = 0x56; return 0;
        }
        a->status = 0;
        return 0;
    }
    if (nr == 0x29) { /* FREE: succeeds on fixture handles */
        if (size >= 12) { unsigned st = 0; memcpy((unsigned char *)arg + 8, &st, 4); }
        return 0;
    }
    if (nr == 0x2a && size == 32) { /* NVOS54 control */
        NVOS54_PARAMETERS *c = arg;
        c->status = dispatch_control(c->cmd, c->params, c->paramsSize);
        return 0;
    }
    trace("[fake] unhandled escape nr=0x%02x fail-closed", nr);
    errno = EINVAL;
    return -1; /* fail closed on fixture descriptors */

forward:
    if (!real_ioctl) real_ioctl = dlsym(RTLD_NEXT, "ioctl");
    return real_ioctl(fd, cmd, arg);
}

int ioctl(int fd, unsigned long cmd, ...)
{
    va_list ap;
    va_start(ap, cmd);
    void *arg = va_arg(ap, void *);
    va_end(ap);
    return fake_ioctl(fd, cmd, arg);
}

__attribute__((constructor)) static void fake_init(void)
{
    memset(fake_fds, 0, sizeof(fake_fds));
}

/* fake_rm.c — deterministic offline RM-UAPI backend (LD_PRELOAD).
 *
 * Emulates the ioctl surface rmctl uses: version check (0xD2), NVOS64 alloc (0x2B),
 * NVOS54 control (0x2A) for the probe command set. NOT a hardware model — a fixture.
 *
 * Env knobs (all optional):
 *   FAKE_FAIL=1        every emulated ioctl returns -1/ENOTTY (syscall-failure mode)
 *   FAKE_STATUS=0xNN   every control returns this RM status (RM-failure mode)
 *   FAKE_PSTATE=0xNN   GET_CURRENT_PSTATE payload (default 0x100 = P8)
 *
 * Determinism: handles and payloads are fixed; PMUMON's last-sample KHz increments by
 * 1000 per call *within a process* (changing-outputs mode). The PMUMON `super`
 * metadata must be passed back unmodified on later calls (stale-input check) —
 * a modified super yields RM status 0x56.
 *
 * Any ioctl that is not part of the emulated surface is forwarded to the real ioctl.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <sys/ioctl.h>

static int (*real_ioctl)(int, unsigned long, void *);
static unsigned pmumon_calls = 0;
__attribute__((constructor)) static void fake_loaded(void)
{
    if (getenv("FAKE_DEBUG")) fprintf(stderr, "[fake] backend loaded\n");
}
static unsigned char super_copy[16];
static int super_seen = 0;

static unsigned env_hex(const char *name, unsigned dflt)
{
    const char *v = getenv(name);
    return v ? (unsigned)strtoul(v, NULL, 0) : dflt;
}

static int fake_ioctl(int fd, unsigned long cmd, void *arg)
{
    if (getenv("FAKE_FAIL")) {
        errno = ENOTTY;
        return -1;
    }
    unsigned magic = (cmd >> 8) & 0xff, nr = cmd & 0xff, size = (cmd >> 16) & 0x3fff;
    if (magic != 'F')
        goto forward;

    if (nr == 0xd2 && size == 72) { /* version check */
        char *p = arg;
        memset(p, 0, 72);
        p[0] = '2'; /* QUERY */
        p[4] = 1;   /* reply RECOGNIZED */
        strcpy(p + 8, "615.71.09-fake");
        return 0;
    }
    if (nr == 0x2b && size == 48) { /* NVOS64 alloc */
        unsigned cls, newh;
        memcpy(&cls, (unsigned char *)arg + 12, 4);
        if (cls == 0x0) newh = 0x1000;
        else if (cls == 0x80) newh = 0x2000;
        else if (cls == 0x2080) newh = 0x3000;
        else { unsigned st = 0x56; memcpy((unsigned char *)arg + 44, &st, 4); return 0; }
        memcpy((unsigned char *)arg + 8, &newh, 4);
        return 0;
    }
    if (nr == 0x2a && size == 32) { /* NVOS54 control */
        unsigned cmd_id, psize, st = 0;
        unsigned long params;
        unsigned char *a = arg;
        memcpy(&cmd_id, a + 8, 4);
        memcpy(&params, a + 16, 8);
        memcpy(&psize, a + 24, 4);
        unsigned forced = env_hex("FAKE_STATUS", 0);
        if (forced) { memcpy(a + 28, &forced, 4); return 0; }

        if (cmd_id == 0x20803601 && psize >= 24) { /* GSP GET_FEATURES */
            unsigned feat = 1, valid = 1, dflt = 1;
            memcpy((void *)(uintptr_t)params + 0, &feat, 4);
            memcpy((void *)(uintptr_t)params + 4, &valid, 1);
            memcpy((void *)(uintptr_t)params + 5, &dflt, 1);
            strcpy((char *)(uintptr_t)params + 8, "615.71.09-fake");
        } else if (cmd_id == 0x20801037 && psize >= 16) { /* PMUMON samples */
            /* stale-input check: super must round-trip unmodified */
            if (super_seen && memcmp((const void *)(uintptr_t)params, super_copy, 16) != 0) {
                st = 0x56;
            } else {
                if (!super_seen) { memcpy(super_copy, (const void *)(uintptr_t)params, 16); super_seen = 1; }
                pmumon_calls++;
                unsigned n = 250, last = 210000u + 1000u * (pmumon_calls - 1);
                memcpy((void *)(uintptr_t)params + 16, &n, 4);
                /* samples[249].activeGpcClkFreqKHz: sample struct stride 24 B,
                 * freq field at +20 (per ctrl2080clk.h) → 16 + 8 + 249*24 + 20 */
                unsigned off = 16 + 8 + 249 * 24 + 20;
                memcpy((unsigned char *)(uintptr_t)params + off, &last, 4);
            }
        } else if (cmd_id == 0x2080014a && psize >= 268) { /* identity/UUID getter */
            /* round-trip: selector + length + UUID echo (deterministic fixture) */
            unsigned len16 = 16;
            memcpy((void *)(uintptr_t)params + 8, &len16, 4);
            memcpy((void *)(uintptr_t)params + 12,
                   "\x8a\x9c\x05\xb3\xfe\xa1\x4d\x89\x51\x13\xb5\x6a\xcb\xb1\xeb\xa9", 16);
        } else if (cmd_id == 0x2080a61d && psize >= 12) { /* power: u32 mW @+4 */
            unsigned char pw12[12] = {0x01, 0xfe, 0x00, 0x00};
            unsigned mw = 370000;
            memcpy(pw12 + 4, &mw, 4);
            memcpy((void *)(uintptr_t)params, pw12, 12);
        } else if (cmd_id == 0x20802068 && psize >= 4) { /* PSTATE */
            unsigned ps = env_hex("FAKE_PSTATE", 0x100);
            memcpy((void *)(uintptr_t)params, &ps, 4);
        } else {
            st = 0x56; /* unknown control in this fixture */
        }
        memcpy(a + 28, &st, 4);
        return 0;
    }
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

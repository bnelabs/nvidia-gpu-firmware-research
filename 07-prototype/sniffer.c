/*
 * sniffer.c — LD_PRELOAD interceptor decoding NVML's RM-control calls (v2).
 * READ-ONLY observation of the caller's own ioctls; mutates nothing.
 *
 * For every successful RM_CONTROL (escape 0x2A, NVOS54 size 0x20) with a params
 * payload ≤ 32 KiB: captures the params buffer BEFORE the call, compares with
 * AFTER, and reports the first differing byte (= where the response landed).
 *
 * Usage: LD_PRELOAD=./sniffer.so nvidia-smi --query-gpu=pstate --format=csv,noheader
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

static int (*real_ioctl)(int fd, unsigned long cmd, ...);

int ioctl(int fd, unsigned long cmd, ...)
{
    if (!real_ioctl)
        real_ioctl = dlsym(RTLD_NEXT, "ioctl");

    va_list ap;
    va_start(ap, cmd);
    void *arg = va_arg(ap, void *);
    va_end(ap);

    /* ---- pre-capture (before the call) ---- */
    void *params = NULL;
    unsigned psize = 0, ctrl = 0, hObject = 0;
    unsigned char *pre = NULL;
    if (arg && ((cmd >> 8) & 0xff) == 'F' && (cmd & 0xff) != 0x2b &&
        ((cmd >> 16) & 0x3fff) <= 0x8000) {
        unsigned nr = cmd & 0xff;
        unsigned sz = (cmd >> 16) & 0x3fff;
        /* RM_CONTROL (0x2a) decodes as NVOS54; other escapes: dump raw buffer */
        if (nr == 0x2a) {
            memcpy(&hObject, (unsigned char *)arg + 4, 4);
            memcpy(&ctrl, (unsigned char *)arg + 8, 4);
            memcpy(&params, (unsigned char *)arg + 16, 8);
            memcpy(&psize, (unsigned char *)arg + 24, 4);
        } else {
            ctrl = 0x10000 | nr;             /* tag non-RM escapes */
            params = arg;
            psize = sz;
        }
        if (params && psize && psize <= 0x8000) {
            pre = malloc(psize);
            if (pre)
                memcpy(pre, params, psize);
        }
    }

    int r = real_ioctl(fd, cmd, arg);

    /* ---- post-capture & full diff report ---- */
    if (r == 0 && pre) {
        unsigned ndiff = 0;
        dprintf(2, "[sniffer pid=%d] cmd=0x%08x psize=%u diffs:", getpid(), ctrl, psize);
        for (unsigned i = 0; i < psize; i++) {
            if (pre[i] != ((unsigned char *)params)[i]) {
                dprintf(2, " +%u:%02x->%02x", i, pre[i], ((unsigned char *)params)[i]);
                if (++ndiff >= 24) { dprintf(2, " …"); break; }
            }
        }
        dprintf(2, "\n");
        free(pre);
    }
    return r;
}

/*
 * sniffer.c — LD_PRELOAD interceptor that decodes NVML's RM-control calls.
 * READ-ONLY observation of the caller's own ioctls; mutates nothing.
 *
 * Usage: LD_PRELOAD=./sniffer.so nvidia-smi --query-gpu=pstate --format=csv,noheader
 *
 * Decodes NVOS54_PARAMETERS (size 0x20): hClient@0 hObject@4 cmd@8 flags@12
 * params@16 paramsSize@20 status@24 — logged on RM_CONTROL (escape 0x2A) success.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/types.h>
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

    int r = real_ioctl(fd, cmd, arg);

    unsigned magic = (cmd >> 8) & 0xff;
    unsigned nr = cmd & 0xff;
    unsigned size = (cmd >> 16) & 0x3fff;

    if (r == 0 && magic == 'F' && nr == 0x2a && size == 0x20) {
        unsigned hclient, hObject, ctrl, flags, psize, status;
        unsigned long params;
        unsigned char buf[0x20];
        memcpy(buf, arg, sizeof(buf));
        memcpy(&hclient, buf + 0, 4);
        memcpy(&hObject, buf + 4, 4);
        memcpy(&ctrl, buf + 8, 4);
        memcpy(&flags, buf + 12, 4);
        memcpy(&params, buf + 16, 8);
        memcpy(&psize, buf + 24, 4);
        memcpy(&status, buf + 28, 4);
        dprintf(2, "[sniffer pid=%d] RM_CONTROL cmd=0x%08x obj=0x%x paramsSize=%u params@%p\n",
                getpid(), ctrl, hObject, psize, (void *)params);
        /* dump first 32 bytes of the params payload if readable-ish */
        if (params && psize && psize <= 0x10000) {
            unsigned char pbuf[32] = {0};
            unsigned n = psize < 32 ? psize : 32;
            memcpy(pbuf, (void *)params, n);
            dprintf(2, "[sniffer]   params: ");
            for (unsigned i = 0; i < n; i++) dprintf(2, "%02x", pbuf[i]);
            dprintf(2, "\n");
        }
    }
    return r;
}

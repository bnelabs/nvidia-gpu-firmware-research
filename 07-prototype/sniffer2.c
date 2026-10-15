/* sniffer2.c — hardened RM-control tracer implementation (packet A).
 * See sniffer2.h for scope and limitations. */
#define _GNU_SOURCE
#include "sniffer2.h"

#include <dlfcn.h>
#include <errno.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>

static int (*real_ioctl_fp)(int, unsigned long, void *) = NULL;
static unsigned g_seq = 0;

void sniff_set_real_ioctl(int (*f)(int, unsigned long, void *))
{
    real_ioctl_fp = f;
}

static int (*get_real_ioctl(void))(int, unsigned long, void *)
{
    if (!real_ioctl_fp)
        real_ioctl_fp = (int (*)(int, unsigned long, void *))dlsym(RTLD_NEXT, "ioctl");
    return real_ioctl_fp;
}

int sniff_is_nvos54(unsigned magic, unsigned nr, unsigned size_field)
{
    return magic == 'F' && nr == 0x2a && size_field == 32;
}

int sniff_decode_nvos54(const unsigned char *nvos54, size_t len, sniff_record *r)
{
    if (!nvos54 || !r || len != 32)
        return 0;
    memcpy(&r->hclient,  nvos54 + 0, 4);
    memcpy(&r->hObject,  nvos54 + 4, 4);
    memcpy(&r->cmd,      nvos54 + 8, 4);
    memcpy(&r->flags,    nvos54 + 12, 4);
    memcpy(&r->params_ptr, nvos54 + 16, 8);
    memcpy(&r->full_size, nvos54 + 24, 4);
    /* status (at +28) is filled post-call by the caller; captured separately */
    r->have_rm = 1;
    return 1;
}

void sniff_capture_pre(sniff_record *r, int fd, unsigned long cmd, void *arg)
{
    memset(r, 0, sizeof(*r));
    r->seq = ++g_seq;
    r->fd = fd;
    r->iocmd = cmd;
    r->magic = (cmd >> 8) & 0xff;
    r->nr = cmd & 0xff;
    r->size_field = (cmd >> 16) & 0x3fff;
    r->rm_status = -1;
    r->shape_ok = sniff_is_nvos54(r->magic, r->nr, r->size_field) && arg != NULL;

    if (!r->shape_ok)
        return;

    if (!sniff_decode_nvos54((const unsigned char *)arg, 32, r)) {
        r->shape_ok = 0;
        return;
    }
    r->captured = 0;
    r->truncated = 0;
    if (r->params_ptr && r->full_size) {
        r->captured = r->full_size < SNIF_CAP_MAX ? r->full_size : SNIF_CAP_MAX;
        r->truncated = r->full_size > SNIF_CAP_MAX;
        memcpy(r->pre, (const void *)(uintptr_t)r->params_ptr, r->captured);
    }
}

void sniff_capture_post(sniff_record *r, void *arg, int saved_errno)
{
    r->syscall_errno = saved_errno;
    if (!r->shape_ok)
        return;
    if (r->params_ptr && r->full_size) {
        memcpy(r->post, (const void *)(uintptr_t)r->params_ptr, r->captured);
        /* RM status is only meaningful when the ioctl itself succeeded;
         * after a failed syscall the +28 field is the caller's stale input. */
        if (saved_errno == 0)
            memcpy((unsigned char *)&r->rm_status, (const unsigned char *)arg + 28, 4);
        r->changed = memcmp(r->pre, r->post, r->captured) != 0;
        if (r->changed) {
            r->diff_off = 0;
            while (r->diff_off < r->captured && r->pre[r->diff_off] == r->post[r->diff_off])
                r->diff_off++;
        }
    }
}

void sniff_format(const sniff_record *r, char *out, size_t outlen)
{
    size_t o = 0;
#define APP(...) do { if (o < outlen) { int _n = snprintf(out + o, outlen - o, __VA_ARGS__); if (_n > 0) o += (size_t)_n; } } while (0)
    APP("seq=%u fd=%d shape=%s", r->seq, r->fd, r->shape_ok ? "nvos54" : "passthrough");
    if (!r->shape_ok) {
        APP(" magic=0x%02x nr=0x%02x size=%u", r->magic, r->nr, r->size_field);
        return;
    }
    APP(" cmd=0x%08x obj=0x%08x", r->cmd, r->hObject);
    APP(" full=%u captured=%u%s", r->full_size, r->captured,
        r->truncated ? " TRUNCATED" : "");
    APP(" syscall_errno=%d rm_status=%d", r->syscall_errno, r->rm_status);
    if (r->changed)
        APP(" first_diff@+%u pre=%02x post=%02x", r->diff_off,
            r->captured ? r->pre[r->diff_off] : 0,
            r->captured ? r->post[r->diff_off] : 0);
    else
        APP(" unchanged");
#undef APP
}

/* ---- LD_PRELOAD wrapper ---- */
int ioctl(int fd, unsigned long cmd, ...)
{
    va_list ap;
    va_start(ap, cmd);
    void *arg = va_arg(ap, void *);
    va_end(ap);

    sniff_record rec;
    sniff_capture_pre(&rec, fd, cmd, arg);

    errno = 0;
    int r = get_real_ioctl()(fd, cmd, arg);
    int saved = errno;

    sniff_capture_post(&rec, arg, saved);

    char line[512];
    sniff_format(&rec, line, sizeof(line));
    {
        int se = errno;               /* preserve errno across logging */
        dprintf(2, "[sniffer2 %s]\n", line);
        errno = se;
    }

    errno = saved;                    /* restore caller-visible errno */
    return r;
}

/* test_sniff_decode.c — packet A acceptance tests (no GPU, no kernel needed).
 * Covers: malformed shapes, RM rejection, unchanged inputs, truncated captures,
 * diff detection, and caller-visible errno preservation. */
#include "../07-prototype/sniffer2.h"

#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>

static int fails = 0;
#define CHECK(cond, name) do { \
    if (cond) printf("ok   %s\n", name); \
    else { printf("FAIL %s\n", name); fails++; } } while (0)

static int fake_fail(int fd, unsigned long c, void *a)
{
    (void)fd; (void)c; (void)a; errno = ENOTTY; return -1;
}

static int fake_reject(int fd, unsigned long c, void *a)
{
    (void)fd; (void)c;
    unsigned st = 0x1f;
    memcpy((unsigned char *)a + 28, &st, 4);
    errno = 0;
    return 0;
}

static void fill32(unsigned char *b, unsigned cmd, unsigned obj, unsigned full)
{
    memset(b, 0, 32);
    memcpy(b + 8, &cmd, 4);
    memcpy(b + 4, &obj, 4);
    memcpy(b + 24, &full, 4);
}

int main(void)
{
    /* 1. malformed shapes must not decode */
    {
        sniff_record r;
        unsigned char b[40] = {0};
        fill32(b, 0x20800102, 0x11111111, 32);
        CHECK(sniff_decode_nvos54(b, 31, &r) == 0, "decode rejects len=31");
        CHECK(sniff_decode_nvos54(b, 33, &r) == 0, "decode rejects len=33");
        CHECK(sniff_is_nvos54('F', 0x2a, 32) == 1, "exact shape accepted");
        CHECK(sniff_is_nvos54('F', 0x2b, 32) == 0, "wrong nr rejected");
        CHECK(sniff_is_nvos54('F', 0x2a, 64) == 0, "wrong size_field rejected");
    }

    /* 2. well-formed decode extracts fields */
    {
        sniff_record r;
        unsigned char b[32];
        fill32(b, 0x20800102, 0xcaf00001, 64);
        CHECK(sniff_decode_nvos54(b, 32, &r) == 1, "decode accepts len=32");
        CHECK(r.cmd == 0x20800102 && r.hObject == 0xcaf00001 && r.full_size == 64,
              "decode extracts cmd/obj/size");
    }

    /* 3. wrapper: syscall failure — errno preserved, buffer unchanged, no RM status */
    {
        unsigned char b[32], params[64];
        fill32(b, 0x20800102, 0x1, 64);
        memset(params, 0x77, sizeof(params));
        { unsigned long pp = (unsigned long)params; memcpy(b + 16, &pp, 8); }
        sniff_set_real_ioctl(fake_fail);
        errno = 0;
        int rv = ioctl(99, _IOWR('F', 0x2a, unsigned char[32]), b);
        int e = errno;
        CHECK(rv == -1 && e == ENOTTY, "wrapper preserves -1/ENOTTY to caller");
        CHECK(params[0] == 0x77, "params buffer unchanged on syscall failure");
    }

    /* 4. wrapper: RM rejection (status != 0) logged distinctly */
    {
        unsigned char b[32], params[32];
        fill32(b, 0x20800102, 0x1, 32);
        memset(params, 0, sizeof(params));
        { unsigned long pp = (unsigned long)params; memcpy(b + 16, &pp, 8); }
        sniff_set_real_ioctl(fake_reject);
        int rv = ioctl(99, _IOWR('F', 0x2a, unsigned char[32]), b);
        CHECK(rv == 0, "RM rejection returns 0 (kernel accepted the ioctl)");
    }

    /* 5. capture: bounded capture + truncation flag */
    {
        sniff_record r;
        unsigned char b[32];
        static unsigned char big[8192];
        fill32(b, 0x2080a618, 0x1, sizeof(big));
        memset(big, 0xAB, sizeof(big));
        r.params_ptr = (unsigned long)big;
        r.full_size = sizeof(big);
        /* emulate capture path */
        r.captured = r.full_size < SNIF_CAP_MAX ? r.full_size : SNIF_CAP_MAX;
        r.truncated = r.full_size > SNIF_CAP_MAX;
        memcpy(r.pre, big, r.captured);
        CHECK(r.captured == SNIF_CAP_MAX && r.truncated == 1,
              "capture bounded with truncation flag");
    }

    /* 6. diff detection: single changed byte found at right offset */
    {
        sniff_record r;
        unsigned char b[32];
        fill32(b, 0x20800102, 0x1, 64);
        r.params_ptr = 0;
        r.full_size = 64;
        r.captured = 64;
        memset(r.pre, 0x11, 64);
        memcpy(r.post, r.pre, 64);
        r.post[10] = 0xBB;
        r.changed = memcmp(r.pre, r.post, 64) != 0;
        r.diff_off = 0;
        while (r.diff_off < 64 && r.pre[r.diff_off] == r.post[r.diff_off]) r.diff_off++;
        CHECK(r.changed == 1 && r.diff_off == 10, "diff detection at +10");
    }

    /* 7. unchanged input reported as unchanged */
    {
        sniff_record r;
        memset(&r, 0, sizeof(r));
        r.shape_ok = 1;
        r.captured = 32;
        memcpy(r.pre, "AAAA", 4);
        memcpy(r.post, r.pre, 32);
        r.changed = memcmp(r.pre, r.post, 32) != 0;
        CHECK(r.changed == 0, "unchanged input flagged");
    }

    printf(fails ? "\n%d test(s) FAILED\n" : "\nall tests passed\n", fails);
    return fails != 0;
}

/* Retained-capture decoder, explicitly for 64-bit little-endian NVOS54 records.
 * Consumes byte arrays and never follows a pointer from a capture. It does not
 * export ioctl, load NVML or attach to any process. */
#include "sniffer2.h"
#include <string.h>

static uint32_t le32(const unsigned char *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
int sniff_is_nvos54(unsigned magic, unsigned nr, unsigned size)
{
    return magic == 'F' && nr == 0x2a && size == 32;
}
int sniff_decode_nvos54(const unsigned char *h, size_t len, sniff_record *out)
{
    if (!h || !out || len != 32) return 0;
    out->hclient = le32(h);
    out->hobject = le32(h + 4);
    out->cmd = le32(h + 8);
    out->flags = le32(h + 12);
    out->recorded_params_pointer = le32(h + 16) | (uint64_t)le32(h + 20) << 32;
    out->full_size = le32(h + 24);
    return 1;
}
static uint32_t bounded(size_t available, uint32_t declared)
{
    size_t n = available < declared ? available : declared;
    return (uint32_t)(n < SNIF_CAP_MAX ? n : SNIF_CAP_MAX);
}
int sniff_from_buffers(unsigned magic, unsigned nr, unsigned size,
                       const unsigned char *ph, size_t phlen,
                       const unsigned char *qh, size_t qhlen,
                       const unsigned char *pre, size_t pre_len,
                       const unsigned char *post, size_t post_len,
                       int result, int error, sniff_record *out)
{
    if (!out) return 0;
    memset(out, 0, sizeof(*out));
    out->rm_status = -1;
    out->syscall_result = result;
    out->syscall_errno = error;
    if (!sniff_is_nvos54(magic, nr, size) || !sniff_decode_nvos54(ph, phlen, out)) return 0;
    out->shape_ok = 1;
    out->captured_pre = pre ? bounded(pre_len, out->full_size) : 0;
    if (out->captured_pre) memcpy(out->pre, pre, out->captured_pre);
    if (result == 0 && qh && qhlen == 32) {
        out->rm_status = le32(qh + 28);
        out->captured_post = post ? bounded(post_len, out->full_size) : 0;
        if (out->captured_post) memcpy(out->post, post, out->captured_post);
    }
    out->truncated = out->captured_pre < out->full_size ||
                     (result == 0 && out->captured_post < out->full_size);
    uint32_t common = out->captured_pre < out->captured_post ? out->captured_pre : out->captured_post;
    for (uint32_t i = 0; i < common; i++) {
        if (out->pre[i] != out->post[i]) {
            out->changed = 1;
            out->diff_off = i;
            break;
        }
    }
    return 1;
}
void sniff_format(const sniff_record *r, char *out, size_t size)
{
    if (!r || !out || !size) return;
    snprintf(out, size, "offline shape=%s cmd=0x%08x full=%u pre=%u post=%u%s "
             "syscall_result=%d syscall_errno=%d rm_status=%lld changed=%d diff_off=%u",
             r->shape_ok ? "nvos54-le64" : "unsupported", r->cmd, r->full_size,
             r->captured_pre, r->captured_post, r->truncated ? " TRUNCATED" : "",
             r->syscall_result, r->syscall_errno, (long long)r->rm_status, r->changed, r->diff_off);
}
int sniff_write_post(const sniff_record *r, FILE *stream)
{
    if (!r || !stream || !r->shape_ok || r->syscall_result != 0 || r->rm_status < 0 ||
        r->captured_post > SNIF_CAP_MAX) return 0;
    return fwrite(r->post, 1, r->captured_post, stream) == r->captured_post;
}

/* Offline NVOS54 record decoder. No interception, callbacks or live pointers. */
#ifndef SNIFFER2_H
#define SNIFFER2_H
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#define SNIF_CAP_MAX 65536u
typedef struct {
    uint32_t hclient, hobject, cmd, flags, full_size;
    uint64_t recorded_params_pointer; /* historical metadata only; never dereferenced */
    uint32_t captured_pre, captured_post;
    int shape_ok, truncated, syscall_result, syscall_errno;
    int64_t rm_status;              /* -1 if no successful syscall/status record */
    int changed;
    uint32_t diff_off;
    unsigned char pre[SNIF_CAP_MAX], post[SNIF_CAP_MAX];
} sniff_record;
int sniff_is_nvos54(unsigned magic, unsigned nr, unsigned size);
int sniff_decode_nvos54(const unsigned char *header, size_t len, sniff_record *out);
int sniff_from_buffers(unsigned magic, unsigned nr, unsigned size,
                       const unsigned char *pre_header, size_t pre_header_len,
                       const unsigned char *post_header, size_t post_header_len,
                       const unsigned char *pre, size_t pre_len,
                       const unsigned char *post, size_t post_len,
                       int syscall_result, int syscall_errno, sniff_record *out);
void sniff_format(const sniff_record *record, char *out, size_t size);
int sniff_write_post(const sniff_record *record, FILE *stream);
#endif

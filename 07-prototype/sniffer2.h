/* sniffer2.h — hardened LD_PRELOAD RM-control tracer (packet A).
 *
 * Scope/limitations (64-bit Linux, NVIDIA open-KMD UAPI only):
 *  - Decodes ONLY exact-shaped RM_CONTROL calls: ioctl magic 'F', nr 0x2A,
 *    _IOC_SIZE == 32 (NVOS54_PARAMETERS). Anything else is passed through
 *    untouched and recorded as shape_ok=0 with no struct dereference.
 *  - The params buffer is captured bounded (SNIF_CAP_MAX); full size and
 *    truncation are recorded. Input/output direction of RM_CONTROL buffers is
 *    INOUT by API contract; pre/post captures are kept for diffing.
 *  - Syscall errno and the embedded RM status are logged separately.
 *  - Caller-buffer validity is assumed as any libc wrapper must; invalid user
 *    pointers would fault in the caller's context (documented limitation).
 *  - Forwards every ioctl unmodified: loading this library does NOT make a
 *    workload read-only.
 */
#ifndef SNIFFER2_H
#define SNIFFER2_H

#include <stddef.h>

#define SNIF_CAP_MAX 4096

typedef struct {
    unsigned seq;
    int fd;
    unsigned long iocmd;
    unsigned magic, nr, size_field;
    int shape_ok;            /* exact NVOS54 shape seen */
    int have_rm;             /* NVOS54 fields decoded */
    unsigned hclient, hObject, cmd, flags;
    unsigned long params_ptr;
    unsigned full_size, captured;
    int truncated;
    int syscall_errno;       /* errno after the real ioctl */
    int rm_status;           /* NVOS54 status post-call (-1 if not captured) */
    int changed;             /* params buffer changed across the call */
    unsigned diff_off;       /* first differing byte (valid if changed) */
    unsigned char pre[SNIF_CAP_MAX], post[SNIF_CAP_MAX];
} sniff_record;

/* Returns 1 if (magic,nr,size_field) is an exact NVOS54 RM_CONTROL shape. */
int sniff_is_nvos54(unsigned magic, unsigned nr, unsigned size_field);

/* Decode a 32-byte NVOS54 buffer into r's handle/cmd fields. len must be 32. */
int sniff_decode_nvos54(const unsigned char *nvos54, size_t len, sniff_record *r);

/* Fill a one-line human summary (no trailing newline). */
void sniff_format(const sniff_record *r, char *out, size_t outlen);

/* Test hook: override the real ioctl (default = dlsym RTLD_NEXT). */
void sniff_set_real_ioctl(int (*f)(int, unsigned long, void *));

#endif

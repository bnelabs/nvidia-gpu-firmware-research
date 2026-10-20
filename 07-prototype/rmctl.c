/* Offline replacement for the retired live RM client. No device or ioctl path.
 * Original client is retained in Git history at 2d66900; do not execute it.
 */
#define _POSIX_C_SOURCE 200809L
#define _XOPEN_SOURCE 700
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <limits.h>
#include "pstate_decode.h"

int main(int argc, char **argv)
{
    if (argc == 3 && !strcmp(argv[1], "--offline-pstate")) {
        char *end;
        errno = 0;
        unsigned long value = strtoul(argv[2], &end, 0);
        if (errno || !*argv[2] || *end || value > 0xffffffffUL || argv[2][0] == '-') {
            fputs("invalid u32 mask\n", stderr);
            return 1;
        }
        int ordinal = rm_pstate_ordinal((unsigned)value);
        if (ordinal < 0) printf("offline RM mask=0x%lx (undefined encoding)\n", value);
        else printf("offline RM mask=0x%lx -> P%d (not an NVML ordinal)\n", value, ordinal);
        return ordinal < 0;
    }
    if (argc == 3 && !strcmp(argv[1], "--offline-raw")) {
        struct stat st;
        char resolved[PATH_MAX];
        if (lstat(argv[2], &st) || !S_ISREG(st.st_mode) ||
            !realpath(argv[2], resolved) ||
            !strncmp(resolved, "/dev/", 5) || !strncmp(resolved, "/proc/", 6) ||
            !strncmp(resolved, "/sys/", 5)) {
            fputs("offline input must be an existing regular capture file\n", stderr);
            return 1;
        }
        FILE *f = fopen(argv[2], "rb");
        if (!f) { perror("capture file"); return 1; }
        unsigned char buf[65536];
        size_t n = fread(buf, 1, sizeof(buf), f);
        int failed = ferror(f), more = fgetc(f) != EOF;
        fclose(f);
        if (failed) return 1;
        printf("offline raw bytes: captured=%zu%s; semantics unresolved\n", n,
               more ? " TRUNCATED" : "");
        for (size_t i = 0; i < n; i++)
            printf("%02x%s", buf[i], (i + 1) % 16 ? " " : "\n");
        if (n % 16) putchar('\n');
        return 0;
    }
    fputs("Offline only. Usage: rmctl --offline-pstate MASK | --offline-raw CAPTURE\n"
          "Live RM/GSP probes are prohibited by CONSTITUTION.md.\n", stderr);
    return 64;
}

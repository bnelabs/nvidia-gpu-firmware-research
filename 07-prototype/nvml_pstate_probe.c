/* nvml_pstate_probe.c — packet B: isolated direct NVML P-state getter.
 *
 * Markers on stdout: INIT-START/INIT-END, GETTER <i>, SHUTDOWN.
 * Provenance: driver version, device name, PCI bus id, UUID printed once after init.
 * Read-only NVML API usage only (init + getters + shutdown).
 *
 * Build: gcc -O2 -Wall -o nvml_pstate_probe nvml_pstate_probe.c -ldl
 * Trace: LD_PRELOAD=../07-prototype/sniffer2.so ./nvml_pstate_probe 2> trace.log
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef int (*fn_void)(void);
typedef int (*fn_handle_idx)(unsigned, void **);
typedef int (*fn_get_pstate)(void *, unsigned *);
typedef const char *(*fn_errstr)(int);
typedef int (*fn_dev_str)(void *, char *, unsigned);

static void marker(const char *m)
{
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    printf("[marker %s t=%.3f]\n", m, ts.tv_sec + ts.tv_nsec / 1e9);
    fflush(stdout);
}

int main(void)
{
    void *h = dlopen("libnvidia-ml.so.1", RTLD_NOW);
    if (!h) { fprintf(stderr, "dlopen: %s\n", dlerror()); return 1; }

    fn_void        nvmlInit_v2        = (fn_void)dlsym(h, "nvmlInit_v2");
    fn_void        nvmlShutdown       = (fn_void)dlsym(h, "nvmlShutdown");
    fn_handle_idx  getHandleByIdx     = (fn_handle_idx)dlsym(h, "nvmlDeviceGetHandleByIndex_v2");
    fn_get_pstate  getPstate          = (fn_get_pstate)dlsym(h, "nvmlDeviceGetPerformanceState");
    fn_dev_str    getName            = (fn_dev_str)dlsym(h, "nvmlDeviceGetName");
    fn_dev_str    getUuid            = (fn_dev_str)dlsym(h, "nvmlDeviceGetUUID");
    fn_errstr      errorString        = (fn_errstr)dlsym(h, "nvmlErrorString");
    if (!nvmlInit_v2 || !getHandleByIdx || !getPstate || !errorString) {
        fprintf(stderr, "missing NVML symbols\n");
        return 1;
    }

    marker("INIT-START");
    int r = nvmlInit_v2();
    printf("init: %d (%s)\n", r, r ? errorString(r) : "ok");
    marker("INIT-END");
    if (r) return 1;

    void *dev = NULL;
    r = getHandleByIdx(0, &dev);
    printf("handle: %d (%s)\n", r, r ? errorString(r) : "ok");
    char name[96] = {0}, uuid[96] = {0};
    if (!r && getName)  getName(dev, name, sizeof(name));
    if (!r && getUuid)  getUuid(dev, uuid, sizeof(uuid));
    printf("device: %s | %s\n", name, uuid);

    for (int i = 0; i < 5; i++) {
        char m[32];
        snprintf(m, sizeof(m), "GETTER %d START", i);
        marker(m);
        unsigned ps = 0xFFFFFFFF;
        r = getPstate(dev, &ps);
        printf("getter %d: rv=%d raw_pstate=0x%x ordinal-ish=%u\n", i, r, ps, ps);
        snprintf(m, sizeof(m), "GETTER %d END", i);
        marker(m);
    }

    if (nvmlShutdown) {
        marker("SHUTDOWN-START");
        nvmlShutdown();
        marker("SHUTDOWN-END");
    }
    return 0;
}

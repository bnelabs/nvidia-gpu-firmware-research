/* CPU-only harness for the unmodified vendor source function. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t NvU32;
typedef uint16_t NvU16;
typedef uint8_t NvU8;
typedef int NvBool;
typedef unsigned NV_STATUS;
typedef struct { int unused; } OBJGPU;
typedef struct KernelBif {
    int bPreparingFunctionLevelReset, bInFunctionLevelReset;
    int (*getProperty)(struct KernelBif *, int);
} KernelBif;
#define NV_OK 0u
#define NV_ERR_GENERIC 0xffffu /* Exact nvstatuscodes.h:28. */
#define NV_ERR_NOT_SUPPORTED 0x56u /* Exact nvstatuscodes.h:115. */
#define NV_TRUE 1
#define NV_FALSE 0
#define NV_XVE_ID 0
#define PDB_PROP_KBIF_FLR_PRE_CONDITIONING_REQUIRED 1
#define NV_PRINTF(...) ((void)0)
#define DBG_BREAKPOINT() (++breakpoints)
#define IS_SILICON(p) ((void)(p), 1)
#define IS_EMULATION(p) ((void)(p), 0)
#define IS_GSP_CLIENT(p) ((void)(p), is_gsp)
#define gpuGetDomain(p) ((void)(p), 0x55u)
#define gpuGetBus(p) ((void)(p), 0xf0u)
#define gpuGetDevice(p) ((void)(p), 0x1eu)
#define FLD_TEST_DRF(d,r,f,c,v) (((v)&0xffffu)==0x10deu)
static unsigned save_status, restore_status, boot_status, pre_status;
static unsigned save_calls, reset_calls, restore_calls, wait_calls, clear_calls;
static unsigned pre_calls, drain_calls, delay_us, breakpoints, msix_restore_calls;
static int preconditioning, is_gsp, msix;
static NvU32 vendor_value;
static int synthetic_handle;
static int property(KernelBif *b,int p) {(void)b;(void)p;return preconditioning;}
static void *osPciInitHandle(NvU32 d,NvU8 b,NvU8 s,int f,NvU16 *v,NvU16 *id) {
    (void)d;(void)b;(void)s;(void)f;*v=0x10de;*id=0x2204;return &synthetic_handle;
}
static NV_STATUS kbifSavePcieConfigRegisters_HAL(OBJGPU *g,KernelBif *b) {
    (void)g;(void)b;++save_calls;return save_status;
}
static int kbifIsMSIXEnabledInHW_HAL(OBJGPU *g,KernelBif *b) {(void)g;(void)b;return msix;}
static NvU32 _kbifSaveMSIXVectorControlMasks(OBJGPU *g,KernelBif *b) {(void)g;(void)b;return 0x1234;}
static void _kbifRestoreMSIXVectorControlMasks(OBJGPU *g,KernelBif *b,NvU32 m) {
    (void)g;(void)b;assert(m==0x1234);++msix_restore_calls;
}
static NV_STATUS kbifStopSysMemRequests_HAL(OBJGPU *g,KernelBif *b,int t) {
    (void)g;(void)b;(void)t;++pre_calls;return pre_status;
}
static NV_STATUS kbifWaitForTransactionsComplete_HAL(OBJGPU *g,KernelBif *b) {
    (void)g;(void)b;++drain_calls;return pre_status;
}
static void kbifTriggerFlr_HAL(OBJGPU *g,KernelBif *b) {(void)g;(void)b;++reset_calls;}
static void osDelayUs(unsigned us) {delay_us+=us;} /* No sleep. */
static NV_STATUS kbifRestorePcieConfigRegisters_HAL(OBJGPU *g,KernelBif *b) {
    (void)g;(void)b;++restore_calls;return restore_status;
}
static NV_STATUS gpuWaitForGfwBootComplete_HAL(OBJGPU *g) {(void)g;++wait_calls;return boot_status;}
static void kbifClearDownstreamReadCounter_HAL(OBJGPU *g,KernelBif *b) {(void)g;(void)b;++clear_calls;}
static NvU32 osPciReadDword(void *h,unsigned offset) {assert(h==&synthetic_handle && offset==0);return vendor_value;}
#include "copied-flr-function.inc"
struct fixture {const char *name;unsigned save,restore,boot,pre;int cond,gsp,msix;NvU32 vendor;unsigned expected,resets,waits,clears;};
int main(void) {
    const struct fixture cases[]={
        {"synthetic_success",0,0,0,0,0,1,1,0x10de,0,1,1,1},
        {"gfw_not_ready_55",0,0,0x55,0,0,1,1,0x10de,0x55,1,1,0},
        {"save_error",7,0,0,0,0,1,0,0x10de,7,0,0,0},
        {"restore_error",0,8,0,0,0,1,0,0x10de,8,1,0,0},
        {"non_gsp_branch",0,0,0,0,0,0,0,0x10de,NV_ERR_NOT_SUPPORTED,1,0,0},
        {"late_vendor_mismatch",0,0,0,0,0,1,0,0xffff,NV_ERR_GENERIC,1,1,1},
        {"precondition_errors_continue",0,0,0,9,1,1,0,0x10de,0,1,1,1}
    };
    puts("[");
    for(unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);++i) {
        const struct fixture *c=&cases[i];
        save_status=c->save;restore_status=c->restore;boot_status=c->boot;pre_status=c->pre;
        preconditioning=c->cond;is_gsp=c->gsp;msix=c->msix;vendor_value=c->vendor;
        save_calls=reset_calls=restore_calls=wait_calls=clear_calls=pre_calls=drain_calls=delay_us=breakpoints=msix_restore_calls=0;
        OBJGPU gpu={0};KernelBif bif={0,0,property};
        unsigned status=kbifDoFunctionLevelReset_TU102(&gpu,&bif);
        assert(status==c->expected && reset_calls==c->resets && wait_calls==c->waits && clear_calls==c->clears);
        assert(!bif.bInFunctionLevelReset && !bif.bPreparingFunctionLevelReset);
        if(c->cond)assert(pre_calls==1 && drain_calls==1 && breakpoints==2);
        if(c->boot)assert(msix_restore_calls==0);
        printf("{\"case\":\"%s\",\"all_callbacks_synthetic\":true,\"status\":%u,\"reset_calls\":%u,\"boot_wait_calls\":%u,\"counter_clear_calls\":%u,\"modeled_delay_us\":%u}%s\n",c->name,status,reset_calls,wait_calls,clear_calls,delay_us,i+1<sizeof(cases)/sizeof(cases[0])?",":"");
    }
    puts("]");return 0;
}

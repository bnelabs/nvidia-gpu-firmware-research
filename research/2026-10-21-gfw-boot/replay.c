#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include "dev_gc6_island.h"
#include "dev_gc6_island_addendum.h"
typedef uint32_t NvU32;
typedef uint8_t NvU8;
typedef int NvBool;
typedef uint32_t NV_STATUS;
typedef struct { int placeholder; } OBJGPU;
typedef struct { int placeholder; } KernelGsp;
typedef KernelGsp KernelFalcon;
#define NV_TRUE 1
#define NV_FALSE 0
#define NV_OK 0u
#define NV_ERR_NOT_READY 0x55u
#define LEVEL_ERROR 0
#define GPU_TIMEOUT_FLAGS_OSTIMER 0
#define DEVICE_BASE(x) 0u /* Non-null early-map branch is excluded. */
#define MEM_RD32(p) (abort(), 0u)
#define staticCast(p,type) ((type *)(p))
#define NV_PRINTF(level,...) fprintf(stderr,__VA_ARGS__)
#define FIELD_LO(x) (0 ? x)
#define FIELD_HI(x) (1 ? x)
#define DRF_VAL(d,r,f,v) (((v) >> FIELD_LO(NV##d##r##f)) & ((1u << (FIELD_HI(NV##d##r##f)-FIELD_LO(NV##d##r##f)+1))-1u))
#define FLD_TEST_DRF(d,r,f,c,v) (DRF_VAL(d,r,f,v)==NV##d##r##f##c)
static KernelGsp synthetic_gsp;
#define GPU_GET_KERNEL_GSP(gpu) (&synthetic_gsp)
static NvU32 plm, marker, future_marker, halt_status;
static unsigned marker_reads, plm_reads, halt_calls, timeout_us;
static NvU32 synthetic_read(NvU32 address) {
 if (address==NV_PGC6_AON_SECURE_SCRATCH_GROUP_05_PRIV_LEVEL_MASK) { ++plm_reads; return plm; }
 if (address==NV_PGC6_AON_SECURE_SCRATCH_GROUP_05_0_GFW_BOOT) {
  ++marker_reads;
  return marker_reads==1 ? marker : future_marker;
 }
 abort();
}
#define GPU_REG_RD32(gpu,address) ((void)(gpu), synthetic_read(address))
static NvU32 gpuScaleTimeout(OBJGPU *gpu,NvU32 timeout) { (void)gpu; return timeout; }
static NV_STATUS kflcnWaitForHalt_HAL(OBJGPU *gpu,KernelFalcon *falcon,NvU32 timeout,int flags) {
 (void)gpu;(void)falcon;(void)flags;++halt_calls;timeout_us=timeout;return halt_status;
}
#include "copied-functions.inc"
struct fixture {const char *name;NvU32 plm,marker,future,halt,expected;unsigned reads;};
int main(void) {
 struct fixture cases[]={
  {"logged_marker_1_halt_ok",1,1,1,0,0x55,1},
  {"completed_marker_halt_ok",1,0xff,0xff,0,0,1},
  {"read_protection_not_lowered",0,0xff,0xff,0,0x55,0},
  {"completed_marker_halt_error",1,0xff,0xff,0x65,0x65,1},
  {"completion_only_on_next_read",1,1,0xff,0,0x55,1},
  {"synthetic_all_ones_halt_ok",0xffffffff,0xffffffff,0xffffffff,0,0,1}
 };
 OBJGPU gpu={0};puts("[");
 for (unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);++i) {
  struct fixture *c=&cases[i];plm=c->plm;marker=c->marker;future_marker=c->future;halt_status=c->halt;
  marker_reads=plm_reads=halt_calls=timeout_us=0;
  NV_STATUS result=gpuWaitForGfwBootComplete_TU102(&gpu);
  assert(result==c->expected && marker_reads==c->reads && halt_calls==1 && timeout_us==2050000);
  printf("{\"case\":\"%s\",\"synthetic\":true,\"status\":%u,\"marker_reads\":%u,\"protection_reads\":%u,\"halt_calls\":%u,\"modeled_timeout_us\":%u}%s\n",c->name,result,marker_reads,plm_reads,halt_calls,timeout_us,i+1<sizeof(cases)/sizeof(cases[0])?",":"");
 }
 puts("]");return 0;
}

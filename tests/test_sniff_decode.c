#include "../07-prototype/sniffer2.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
static unsigned checks;
#define CHECK(c) do { checks++; if (!(c)) { fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#c); return 1; } } while (0)
static void put32(unsigned char *p, uint32_t v)
{ for (unsigned i=0;i<4;i++) p[i]=(unsigned char)(v>>(8*i)); }
int main(void)
{
    unsigned char h[32]={0}, q[32]={0};
    static unsigned char pre[SNIF_CAP_MAX+1], post[SNIF_CAP_MAX+1];
    sniff_record *r=calloc(1,sizeof(*r));
    CHECK(r != NULL);
    put32(h,0x1234); put32(h+4,0x5678); put32(h+8,0x2080a618);
    /* Deliberately invalid historical pointer: decoder must never follow it. */
    memset(h+16,0xff,8);
    put32(h+24,sizeof(pre)); memcpy(q,h,32);
    memset(pre,0x11,sizeof(pre)); memcpy(post,pre,sizeof(pre)); post[100]=0x22;
    CHECK(!sniff_decode_nvos54(h,31,r));
    CHECK(!sniff_decode_nvos54(h,33,r));
    CHECK(!sniff_decode_nvos54(NULL,32,r));
    CHECK(!sniff_from_buffers('F',0x2b,32,h,32,q,32,pre,sizeof(pre),post,sizeof(post),0,0,r));
    CHECK(!sniff_from_buffers('F',0x2a,64,h,32,q,32,pre,sizeof(pre),post,sizeof(post),0,0,r));
    CHECK(sniff_from_buffers('F',0x2a,32,h,32,q,32,pre,sizeof(pre),post,sizeof(post),0,99,r));
    CHECK(r->hclient==0x1234 && r->hobject==0x5678 && r->cmd==0x2080a618);
    CHECK(r->recorded_params_pointer==UINT64_MAX);
    CHECK(r->captured_pre==SNIF_CAP_MAX && r->captured_post==SNIF_CAP_MAX && r->truncated);
    CHECK(r->changed && r->diff_off==100);
    CHECK(r->rm_status==0); /* success is determined by return value, not stale errno */
    FILE *f=tmpfile(); CHECK(f != NULL);
    CHECK(sniff_write_post(r,f)); CHECK(ftell(f)==SNIF_CAP_MAX); fclose(f);
    CHECK(sniff_from_buffers('F',0x2a,32,h,32,q,32,pre,0,post,sizeof(post),-1,25,r));
    CHECK(r->rm_status==-1 && r->captured_post==0 && r->syscall_errno==25);
    f=tmpfile(); CHECK(f != NULL); CHECK(!sniff_write_post(r,f)); fclose(f);
    put32(h+24,12); memcpy(q,h,32); put32(q+28,0x56);
    CHECK(sniff_from_buffers('F',0x2a,32,h,32,q,32,pre,12,pre,12,0,0,r));
    CHECK(r->rm_status==0x56 && !r->changed && !r->truncated);
    f=tmpfile(); CHECK(f != NULL); CHECK(sniff_write_post(r,f)); CHECK(ftell(f)==12); fclose(f);
    CHECK(sniff_from_buffers('F',0x2a,32,h,32,q,31,pre,12,post,12,0,0,r));
    CHECK(r->rm_status==-1 && r->captured_post==0 && r->truncated);
    CHECK(sniff_from_buffers('F',0x2a,32,h,32,q,32,NULL,12,NULL,12,0,0,r));
    CHECK(r->captured_pre==0 && r->captured_post==0 && r->truncated);
    char text[32]; sniff_format(r,text,sizeof(text)); CHECK(text[31]=='\0');
    free(r); printf("%u offline record checks passed\n",checks); return 0;
}

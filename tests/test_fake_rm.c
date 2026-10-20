#include "../07-prototype/fake_rm.h"
#include "../07-prototype/pstate_decode.h"
#include <assert.h>
#include <string.h>
int main(void)
{
    unsigned char b[16]; memset(b,0xcc,sizeof(b));
    assert(fake_rm_payload(0x2080a61d,b,11)==-1);
    for (unsigned i=0;i<sizeof(b);i++) assert(b[i]==0xcc);
    assert(fake_rm_payload(0x2080a61d,b,12)==12 && b[12]==0xcc);
    assert(fake_rm_payload(0x20802068,b,4)==4 && b[4]==80);
    unsigned value=b[0]|(unsigned)b[1]<<8|(unsigned)b[2]<<16|(unsigned)b[3]<<24;
    assert(rm_pstate_ordinal(value)==8);
    assert(fake_rm_payload(0xffffffff,b,sizeof(b))==-1);
    assert(fake_rm_payload(0x20802068,0,4)==-1);
    return 0;
}

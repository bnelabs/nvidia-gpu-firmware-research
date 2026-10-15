#include <assert.h>
#include "../07-prototype/pstate_decode.h"
int main(void)
{
    for (unsigned n = 0; n < 16; ++n)
        assert(rm_pstate_ordinal(1U << n) == (int)n);
    assert(rm_pstate_ordinal(0) == -1);
    assert(rm_pstate_ordinal(3) == -1);
    assert(rm_pstate_ordinal(0x10000) == -1);
    assert(rm_pstate_ordinal(~0U) == -1);
    return 0;
}

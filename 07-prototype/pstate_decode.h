#ifndef PSTATE_DECODE_H
#define PSTATE_DECODE_H
/* NV2080_CTRL_PERF_PSTATES_Pn = 1U << n; reject undefined/composite values. */
static inline int rm_pstate_ordinal(unsigned value)
{
    if (!value || value > 0x8000U || (value & (value - 1U)))
        return -1;
    int ordinal = 0;
    while ((value >>= 1U) != 0)
        ++ordinal;
    return ordinal;
}
#endif

/* Retired live ABI/trace probe. Deliberately has no NVML or GPU dependency. */
#include <stdio.h>
int main(void)
{
    fputs("Retired: no direct NVML ABI probing. Use retained captures or the fixed\n"
          "documented telemetry collector; see CONSTITUTION.md.\n", stderr);
    return 64;
}

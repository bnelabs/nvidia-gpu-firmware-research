/* CPU-only fixture bytes. No fd interception, hardware, syscall forwarding,
 * environment-driven behavior or claim of hardware fidelity. */
#include "fake_rm.h"
#include <string.h>
int fake_rm_payload(uint32_t command, unsigned char *out, size_t capacity)
{
    static const unsigned char pstate[] = {0, 1, 0, 0}; /* synthetic one-hot P8 */
    static const unsigned char opaque[] = {1, 254, 0, 0, 80, 165, 5, 0, 0, 0, 0, 0};
    const unsigned char *src;
    size_t size;
    if (command == 0x20802068u) { src = pstate; size = sizeof(pstate); }
    else if (command == 0x2080a61du) { src = opaque; size = sizeof(opaque); }
    else return -1;
    if (!out || capacity < size) return -1;
    memcpy(out, src, size);
    return (int)size;
}
